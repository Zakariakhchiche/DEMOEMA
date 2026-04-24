"""Silver codegen pipeline — agent lead-data-engineer génère le SQL MATERIALIZED VIEW
à partir d'un spec YAML de silver transformation.

Flow :
1. Lire silver_specs/{silver_name}.yaml
2. Introspect schema bronze (source tables + columns via information_schema)
3. Préparer prompt (spec + schémas + règles silver + éventuel feedback d'erreur précédente)
4. Appeler Ollama Cloud (agent lead-data-engineer)
5. Extraire SQL (fences ```sql ... ```)
6. Valider : parse basique + check dangereux (DROP TABLE bronze, DELETE, etc.)
7. Écrire dans silver_transforms/{silver_name}.sql
8. Log dans audit.silver_specs_versions
9. Optionnel : apply (CREATE MATERIALIZED VIEW IF NOT EXISTS + CREATE INDEX)

⚠️ SQL généré jamais exécuté sans validation :
- Seuls CREATE MATERIALIZED VIEW + CREATE INDEX + REFRESH + SELECT autorisés
- Aucune DROP/DELETE/TRUNCATE sur bronze.*
- Aucun fichier en dehors de silver_transforms/*.sql
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
import yaml

from config import settings
from loader import get_agent
from ollama_client import OllamaClient

log = logging.getLogger("demoema.silver_codegen")

SILVER_SPECS_DIR = Path(__file__).parent / "silver_specs"
SILVER_TRANSFORMS_DIR = Path(__file__).parent / "silver_transforms"
SILVER_TRANSFORMS_DIR.mkdir(exist_ok=True)


# ═══════════ Validation : banned patterns ═══════════

BANNED_PATTERNS = [
    r"\bDROP\s+TABLE\s+bronze\.",
    r"\bDELETE\s+FROM\s+bronze\.",
    r"\bTRUNCATE\s+bronze\.",
    r"\bALTER\s+TABLE\s+bronze\.",
    r"\bDROP\s+SCHEMA\s+bronze",
    r"\bDROP\s+DATABASE\b",
    r"\bGRANT\s+",
    r"\bREVOKE\s+",
    r"\\\\copy\s+",
    r"\bCOPY\s+.*\bFROM\s+PROGRAM\b",
    r"\bCREATE\s+EXTENSION\b",
    r"\bCREATE\s+FUNCTION\b.*LANGUAGE\s+plpython",
]


def _validate_sql(sql: str) -> tuple[bool, str]:
    """Check SQL for dangerous patterns + basic structure."""
    if not sql or len(sql) < 50:
        return False, "SQL too short or empty"
    if not re.search(r"CREATE\s+(OR\s+REPLACE\s+)?MATERIALIZED\s+VIEW\s+(IF\s+NOT\s+EXISTS\s+)?silver\.", sql, re.IGNORECASE):
        return False, "No CREATE MATERIALIZED VIEW silver.* found"
    upper = sql.upper()
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"Banned pattern: {pattern}"
    # Must reference at least one bronze table
    if "BRONZE." not in upper:
        return False, "No bronze source referenced"
    return True, "ok"


def _version_uid(silver_name: str, sql: str) -> str:
    raw = f"{silver_name}|{sql}|{datetime.now(tz=timezone.utc).isoformat()}"
    return hashlib.sha1(raw.encode()).hexdigest()[:40]


# ═══════════ Bronze introspection ═══════════

def introspect_schema(conn, tables: list[str]) -> dict[str, list[dict]]:
    """Return {'bronze.foo': [{'column': 'x', 'type': 'text'}, ...]}."""
    result: dict[str, list[dict]] = {}
    with conn.cursor() as cur:
        for full_name in tables:
            if "." in full_name:
                schema, table = full_name.split(".", 1)
            else:
                schema, table = "bronze", full_name
            cur.execute(
                """
                SELECT column_name, data_type, udt_name, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema, table),
            )
            rows = cur.fetchall()
            result[f"{schema}.{table}"] = [
                {"column": r[0], "type": r[1], "udt": r[2], "len": r[3]}
                for r in rows
            ]
    return result


def _format_schema_for_prompt(schemas: dict[str, list[dict]]) -> str:
    lines = []
    for tbl, cols in schemas.items():
        lines.append(f"### `{tbl}` ({len(cols)} cols)")
        for c in cols[:60]:   # cap at 60 cols per table to keep prompt sane
            type_repr = c["type"]
            if c.get("len"):
                type_repr += f"({c['len']})"
            lines.append(f"- `{c['column']}` : {type_repr}")
        if len(cols) > 60:
            lines.append(f"- ...({len(cols) - 60} more cols truncated)")
        lines.append("")
    return "\n".join(lines)


# ═══════════ Prompt builder ═══════════

def _build_prompt(spec: dict, schemas: dict, feedback: str | None = None) -> str:
    silver_name = spec["silver_name"]
    goal = spec.get("goal") or spec.get("description", "")
    source_tables = spec.get("source_tables", [])
    grain = spec.get("grain", "1 row per natural key")
    business_logic = spec.get("business_logic", "")
    key_columns = spec.get("key_columns", [])
    transformations = spec.get("transformations", "")
    indexes = spec.get("indexes", [])
    sla_minutes = spec.get("sla_minutes", 1440)

    fb_block = ""
    if feedback:
        fb_block = f"""
## ITÉRATION PRÉCÉDENTE — ERREUR À CORRIGER
{feedback}
Corrige ce problème dans cette nouvelle version.
"""

    idx_block = ""
    if indexes:
        _idx_lines = []
        for idx in indexes:
            # Detect GIN indexes (array columns, jsonb, tsvector, trigram)
            # and produce correct Postgres syntax: CREATE INDEX ON t USING gin (col)
            idx_lower = idx.lower()
            if "using gin" in idx_lower or idx.endswith(" USING gin"):
                col = idx.replace("USING gin", "").replace("using gin", "").strip().strip("()")
                _idx_lines.append(f"- `CREATE INDEX ON {silver_name} USING gin ({col})`")
            elif "where" in idx_lower:
                # Partial index: "col WHERE cond" -> CREATE INDEX ON t (col) WHERE cond
                parts = re.split(r"\s+WHERE\s+", idx, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) == 2:
                    col, cond = parts[0].strip(), parts[1].strip()
                    _idx_lines.append(f"- `CREATE INDEX ON {silver_name} ({col}) WHERE {cond}`")
                else:
                    _idx_lines.append(f"- `CREATE INDEX ON {silver_name} ({idx})`")
            else:
                _idx_lines.append(f"- `CREATE INDEX ON {silver_name} ({idx})`")
        idx_block = "\n## INDEXES À CRÉER (respecte EXACTEMENT cette syntaxe Postgres)\n" + "\n".join(_idx_lines)

    schema_block = _format_schema_for_prompt(schemas)

    return f"""Tu es lead-data-engineer DEMOEMA. Ta mission : GÉNÉRER le SQL Postgres d'une MATERIALIZED VIEW pour la couche silver.
{fb_block}
## TARGET
- Nom : `{silver_name}`
- Grain : {grain}
- Sources : {', '.join(source_tables)}
- SLA refresh : {sla_minutes} min
- Goal métier : {goal}

## LOGIQUE MÉTIER ATTENDUE
{business_logic}

## TRANSFORMATIONS DEMANDÉES
{transformations}

## KEY COLUMNS (doivent figurer en SELECT)
{', '.join(key_columns) if key_columns else 'à déduire'}

## SCHÉMAS BRONZE DISPONIBLES
{schema_block}
{idx_block}

## RÈGLES NON NÉGOCIABLES
1. **Un seul `CREATE MATERIALIZED VIEW IF NOT EXISTS {silver_name} AS ...`** suivi des CREATE INDEX
2. **INTERDIT** : DROP/DELETE/TRUNCATE/ALTER sur bronze.*, COPY FROM PROGRAM, CREATE EXTENSION, plpython
3. **Autorisé** : SELECT, JOIN, CASE, aggregat, CTE, jsonb_*, to_date, coalesce, nullif, array_agg
4. **Qualifie** toutes les tables par leur schema : `bronze.xxx`, jamais sans préfixe
5. **CAST** explicite pour les colonnes non typées (ex: `(payload->>'date')::date`)
6. **Dedup** : utilise GROUP BY ou DISTINCT ON si le grain l'exige
7. **Gère les NULLS** : NULLIF('') pour les strings vides, COALESCE quand applicable
8. **Commentaire** : `-- Generated by silver_codegen for {silver_name}` en tête
9. **Indexes** à la fin, un par ligne
10. **Pas de LIMIT** (on veut tout le silver, pas un échantillon)

## SORTIE ATTENDUE
**UNIQUEMENT du SQL Postgres** entre balises ```sql ... ```. **Aucun texte avant ou après**. Pas d'explication, pas de markdown intermédiaire, juste le SQL complet prêt à être exécuté.
"""


def _extract_sql_from_response(response_text: str) -> str | None:
    m = re.search(r"```sql\s*\n(.*?)\n```", response_text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    stripped = response_text.strip()
    if stripped.upper().startswith(("CREATE ", "--", "/*", "WITH ")):
        return stripped
    return None


# ═══════════ Main pipeline ═══════════

def load_silver_spec(silver_name: str) -> dict | None:
    path = SILVER_SPECS_DIR / f"{silver_name.replace('silver.', '')}.yaml"
    if not path.exists():
        log.warning("spec not found: %s", path)
        return None
    with path.open(encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    # Normalize silver_name (auto-prefix silver.)
    if not spec.get("silver_name", "").startswith("silver."):
        spec["silver_name"] = f"silver.{spec.get('silver_name', silver_name.replace('silver.', ''))}"
    return spec


async def generate_silver_sql(
    silver_name: str,
    feedback: str | None = None,
    apply_immediately: bool = False,
) -> dict:
    """Generate silver SQL via LLM. Returns dict with keys:
    - sql: generated SQL (or None on failure)
    - valid: bool
    - msg: validation msg
    - version_uid: audit reference
    - applied: bool (True if apply_immediately + valid + successful apply)
    """
    spec = load_silver_spec(silver_name)
    if not spec:
        return {"error": f"Spec not found for {silver_name}"}

    # Introspect bronze schemas
    if not settings.database_url:
        return {"error": "no database_url"}
    with psycopg.connect(settings.database_url) as conn:
        schemas = introspect_schema(conn, spec.get("source_tables", []))
    missing = [t for t, cols in schemas.items() if not cols]
    if missing:
        return {"error": f"bronze tables missing: {missing}"}

    # LLM call
    agent = get_agent("lead-data-engineer")
    if not agent:
        return {"error": "agent lead-data-engineer not loaded"}

    prompt = _build_prompt(spec, schemas, feedback=feedback)
    client = OllamaClient()
    try:
        response = await client.chat(
            model=agent.model,
            messages=[
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": prompt},
            ],
            options=agent.to_ollama_options(),
            stream=False,
        )
    finally:
        await client.close()

    content = response.get("message", {}).get("content", "") if isinstance(response, dict) else ""
    sql = _extract_sql_from_response(content)
    if not sql:
        return {"error": "no SQL extractable from LLM response", "raw": content[:500]}

    # Validate
    ok, msg = _validate_sql(sql)
    version_uid = _version_uid(silver_name, sql)

    # Persist to disk always (even invalid, for debugging)
    target_path = SILVER_TRANSFORMS_DIR / f"{silver_name.replace('silver.', '')}.sql"
    target_path.write_text(sql, encoding="utf-8")

    # Log in audit
    _log_version(silver_name, spec, sql, ok, msg, version_uid, agent.model, feedback)

    result = {
        "silver_name": silver_name,
        "sql": sql,
        "version_uid": version_uid,
        "valid": ok,
        "validation_msg": msg,
        "path": str(target_path),
        "applied": False,
    }

    if ok and apply_immediately:
        applied = _apply_sql(silver_name, sql, version_uid)
        result["applied"] = applied["applied"]
        result.update({f"apply_{k}": v for k, v in applied.items() if k != "applied"})

    return result


def _log_version(
    silver_name: str,
    spec: dict,
    sql: str,
    ok: bool,
    msg: str,
    version_uid: str,
    llm_model: str,
    feedback: str | None,
):
    if not settings.database_url:
        return
    try:
        with psycopg.connect(settings.database_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit.silver_specs_versions
                  (version_uid, silver_name, spec_yaml, generated_sql, generator,
                   llm_model, llm_feedback, validation_status, validation_msg)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (version_uid) DO NOTHING
                """,
                (
                    version_uid, silver_name,
                    yaml.safe_dump(spec, allow_unicode=True, sort_keys=False),
                    sql, "codegen_llm", llm_model, feedback,
                    "ok" if ok else "invalid", msg,
                ),
            )
    except Exception as e:
        log.warning("audit log failed: %s", e)


def _apply_sql(silver_name: str, sql: str, version_uid: str) -> dict:
    """Execute the generated SQL. Returns apply stats."""
    if not settings.database_url:
        return {"applied": False, "error": "no database_url"}
    try:
        with psycopg.connect(settings.database_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("SET statement_timeout = 0")
            cur.execute(sql)
            # mark version applied
            cur.execute(
                "UPDATE audit.silver_specs_versions SET applied = true, applied_at = now() WHERE version_uid = %s",
                (version_uid,),
            )
        log.info("[silver_codegen] applied %s (version %s)", silver_name, version_uid[:12])
        return {"applied": True}
    except Exception as e:
        log.exception("[silver_codegen] apply failed for %s", silver_name)
        return {"applied": False, "error": f"{type(e).__name__}: {e}"}


def list_silver_specs() -> list[str]:
    """Return list of available silver names (from YAML files)."""
    return sorted(
        f"silver.{p.stem}"
        for p in SILVER_SPECS_DIR.glob("*.yaml")
        if not p.stem.startswith("_")
    )
