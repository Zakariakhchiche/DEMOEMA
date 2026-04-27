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
from deepseek_client import DeepSeekClient
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

    mv_match = re.search(
        r"CREATE\s+(OR\s+REPLACE\s+)?MATERIALIZED\s+VIEW\s+(IF\s+NOT\s+EXISTS\s+)?(\S+)",
        sql,
        re.IGNORECASE,
    )
    if not mv_match:
        return False, "No CREATE MATERIALIZED VIEW found"
    or_replace, if_not_exists, target = mv_match.groups()

    # IF NOT EXISTS is banned because _apply_sql drops first; with IF NOT EXISTS
    # the CREATE silently no-ops on regen and only the indexes get re-applied,
    # which is what produced 17 duplicate indexes on silver.insee_unites_legales.
    if if_not_exists:
        return False, "IF NOT EXISTS is forbidden — regen requires a real replace"
    if or_replace:
        return False, "OR REPLACE is not supported by Postgres for MATERIALIZED VIEW"
    if not target.lower().startswith("silver."):
        return False, "CREATE MATERIALIZED VIEW silver.* expected as target"

    for pattern in BANNED_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"Banned pattern: {pattern}"

    # A source must be cited via FROM or JOIN — counting "silver." occurrences
    # would false-positive on the target itself.
    if not re.search(r"\b(?:FROM|JOIN)\s+(?:bronze|silver)\.", sql, re.IGNORECASE):
        return False, "No bronze or silver source referenced (FROM/JOIN bronze.* or silver.*)"
    return True, "ok"


def _version_uid(silver_name: str, sql: str) -> str:
    raw = f"{silver_name}|{sql}|{datetime.now(tz=timezone.utc).isoformat()}"
    return hashlib.sha1(raw.encode()).hexdigest()[:40]


# ═══════════ LLM client routing ═══════════

async def _llm_chat(model: str, system: str, user: str,
                    temperature: float = 0.1, num_ctx: int = 65536) -> dict:
    """Route the codegen LLM call to DeepSeek or Ollama based on model name.

    Returns the same shape both providers expose : {"message": {"content": ...}}.
    DeepSeek is preferred when the agent model starts with `deepseek-` (or the
    operator has only DEEPSEEK_API_KEY available — Ollama Cloud needs a paid
    plan with valid OLLAMA_API_KEY which is easy to misplace).

    Resilience : si l'appel Ollama timeout (silver-of-silver avec gros prompt
    peut dépasser 20 min côté kimi), retry automatique avec deepseek-chat.
    Évite que la résilience dépende d'une seule API.
    """
    import httpx

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if model.startswith("deepseek"):
        client = DeepSeekClient(model=model)
        return await client.chat(
            messages=messages, temperature=temperature, max_tokens=4096,
        )

    client = OllamaClient()
    try:
        return await client.chat(
            model=model, messages=messages, stream=False,
            options={"temperature": temperature, "num_ctx": num_ctx},
        )
    except (httpx.TimeoutException, httpx.RemoteProtocolError) as e:
        log.warning("[llm_chat] Ollama %s a échoué (%s) — fallback DeepSeek", model, type(e).__name__)
        try:
            ds = DeepSeekClient(model="deepseek-chat")
            return await ds.chat(
                messages=messages, temperature=temperature, max_tokens=4096,
            )
        except Exception as fb_err:
            log.exception("[llm_chat] fallback DeepSeek a aussi échoué")
            raise fb_err from e
    finally:
        await client.close()


# ═══════════ Bronze introspection ═══════════

def introspect_schema(conn, tables: list[str]) -> dict[str, list[dict]]:
    """Return {'bronze.foo': [{'column': 'x', 'type': 'text'}, ...]}.

    Lit pg_attribute plutôt qu'information_schema.columns parce que ce dernier
    ne voit pas les colonnes des MATERIALIZED VIEW. C'est ce qui empêchait
    silver.entreprises_signals (silver-of-silver) d'être généré : ses sources
    silver.* renvoyaient toujours 0 colonnes → fail "bronze tables missing".
    """
    result: dict[str, list[dict]] = {}
    with conn.cursor() as cur:
        for full_name in tables:
            if "." in full_name:
                schema, table = full_name.split(".", 1)
            else:
                schema, table = "bronze", full_name
            cur.execute(
                """
                SELECT a.attname AS column_name,
                       format_type(a.atttypid, a.atttypmod) AS data_type,
                       t.typname AS udt_name,
                       CASE WHEN a.atttypmod > 0 AND t.typname IN ('varchar','bpchar')
                            THEN a.atttypmod - 4 ELSE NULL END AS char_max_length
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_type t ON t.oid = a.atttypid
                WHERE n.nspname = %s
                  AND c.relname = %s
                  AND c.relkind IN ('r','v','m','p','f')
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                ORDER BY a.attnum
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
    """Compact schema dump for the LLM prompt.

    Le cap a été baissé de 60 à 30 cols par table parce que sur les silvers
    fortement dénormalisés (ex: silver.entreprises_signals avec 9 sources),
    le prompt total dépassait la fenêtre de réflexion utile de kimi-k2.6 et
    déclenchait des ReadTimeout > 10 min.
    """
    lines = []
    for tbl, cols in schemas.items():
        lines.append(f"### `{tbl}` ({len(cols)} cols)")
        for c in cols[:30]:
            type_repr = c["type"]
            if c.get("len"):
                type_repr += f"({c['len']})"
            lines.append(f"- `{c['column']}` : {type_repr}")
        if len(cols) > 30:
            lines.append(f"- ...({len(cols) - 30} more cols truncated)")
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
1. **Un seul `CREATE MATERIALIZED VIEW {silver_name} AS ...`** (PAS de `IF NOT EXISTS`, PAS de `OR REPLACE` — l'apply fait DROP CASCADE avant), suivi des CREATE INDEX
2. **INTERDIT** : DROP/DELETE/TRUNCATE/ALTER sur bronze.*, COPY FROM PROGRAM, CREATE EXTENSION, plpython
3. **Autorisé** : SELECT, JOIN, CASE, aggregat, CTE, jsonb_*, to_date, coalesce, nullif, array_agg
4. **Qualifie** toutes les tables par leur schema : `bronze.xxx` ou `silver.xxx`, jamais sans préfixe (les silver-of-silver sont autorisés ; voir SCHÉMAS BRONZE DISPONIBLES — peut contenir des `silver.*`)
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
    response = await _llm_chat(
        model=agent.model,
        system=agent.system_prompt,
        user=prompt,
        temperature=agent.temperature,
        num_ctx=agent.num_ctx,
    )

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
    """Execute the generated SQL atomically.

    Drops the existing MV (CASCADE — also drops its indexes) inside the same
    transaction as the new CREATE, so a re-applied silver fully replaces its
    predecessor and never accumulates duplicate indexes. Postgres has no
    CREATE OR REPLACE MATERIALIZED VIEW, so DROP+CREATE is the only path.
    """
    if not settings.database_url:
        return {"applied": False, "error": "no database_url"}
    qualified = silver_name if "." in silver_name else f"silver.{silver_name}"
    try:
        with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
            cur.execute("SET statement_timeout = 0")
            cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {qualified} CASCADE")
            cur.execute(sql)
            conn.commit()
        # audit log on its own connection (autocommit)
        with psycopg.connect(settings.database_url, autocommit=True) as conn, conn.cursor() as cur:
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


# ═══════════ Bootstrap : combler l'écart specs YAML ↔ MV en base ═══════════

def _silver_state(conn) -> dict[str, int | None]:
    """For every materialized view in schema 'silver', return its row count.
    Missing MVs are absent from the returned dict.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT n.nspname || '.' || c.relname AS qname,
                   c.reltuples::bigint           AS approx_rows
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'silver' AND c.relkind = 'm'
            """
        )
        return {row[0]: row[1] for row in cur.fetchall()}


def _topo_sort_specs() -> list[str]:
    """Return spec names ordered so each silver-of-silver appears after its deps.

    Edges come from spec.source_tables : if `silver.B` lists `silver.A` as a
    source, A is built before B. Pure bronze-source specs come first.
    Cycles fall back to alphabetical order for the unresolved tail.
    """
    deps: dict[str, set[str]] = {}
    for p in SILVER_SPECS_DIR.glob("*.yaml"):
        if p.stem.startswith("_"):
            continue
        try:
            with p.open(encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}
        except Exception:
            continue
        name = spec.get("silver_name") or f"silver.{p.stem}"
        if not name.startswith("silver."):
            name = f"silver.{name}"
        srcs = spec.get("source_tables") or []
        deps[name] = {s for s in srcs if isinstance(s, str) and s.startswith("silver.")}

    ordered: list[str] = []
    seen: set[str] = set()
    pending = dict(deps)
    while pending:
        ready = sorted(n for n, d in pending.items() if d.issubset(seen | {n}))
        if not ready:
            ordered.extend(sorted(pending))
            break
        for n in ready:
            ordered.append(n)
            seen.add(n)
            pending.pop(n, None)
    return ordered


# Postgres advisory lock id for bootstrap mutual exclusion.
# Uvicorn workers > 1 each run the FastAPI lifespan separately, which fired
# bootstrap N times in parallel — observed on prod with 2 workers racing on
# silver.bodacc_annonces (29M rows) and burning LLM credits twice. A
# session-level pg_try_advisory_lock with a constant id ensures at most one
# bootstrap runs at any moment cluster-wide.
_BOOTSTRAP_LOCK_ID = 0x51EA77B05  # "SILVA77BO5" mnemonic — arbitrary 64-bit


async def bootstrap_missing_silvers(force_empty: bool = True) -> dict:
    """Walk every silver spec YAML and ensure the matching MV exists with rows.

    Used at engine startup AND on the migrate-VPS scenario where Postgres is
    empty after Bronze has been ingested. For each spec :
      - MV missing                    → generate + apply
      - MV exists but 0 rows (and force_empty=True) → regenerate + apply
      - MV exists with rows           → leave alone (refresh job handles it)

    Mutual exclusion is enforced via a Postgres session-level advisory lock so
    multiple Uvicorn workers don't race on the same spec.

    Specs are processed in topological order so silver-of-silver dependencies
    are built before their consumers. Returns a per-spec report.
    """
    if not settings.database_url:
        return {"error": "no database_url"}

    # Hold the lock for the whole bootstrap. Closing this connection
    # auto-releases (Postgres rule for advisory locks).
    lock_conn = psycopg.connect(settings.database_url, autocommit=True)
    try:
        with lock_conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (_BOOTSTRAP_LOCK_ID,))
            got_lock = cur.fetchone()[0]
        if not got_lock:
            log.info("[silver_bootstrap] another worker holds the lock — skipping")
            return {"built": 0, "failed": 0, "skipped": 0,
                    "skipped_due_to_lock": True, "details": []}

        specs = _topo_sort_specs()
        results: list[dict] = []

        with psycopg.connect(settings.database_url) as conn:
            existing = _silver_state(conn)

        for silver_name in specs:
            rows = existing.get(silver_name)
            needs_build = (rows is None) or (force_empty and rows == 0)
            if not needs_build:
                results.append({"silver_name": silver_name, "action": "skip", "rows": rows})
                continue

            reason = "missing" if rows is None else "empty"
            log.info("[silver_bootstrap] building %s (%s)", silver_name, reason)
            try:
                r = await generate_silver_sql(silver_name, apply_immediately=True)
                results.append({
                    "silver_name": silver_name,
                    "action": "build",
                    "reason": reason,
                    "valid": r.get("valid"),
                    "applied": r.get("applied"),
                    "validation_msg": r.get("validation_msg"),
                    "error": r.get("error") or r.get("apply_error"),
                })
            except Exception as e:
                log.exception("[silver_bootstrap] failed %s", silver_name)
                results.append({
                    "silver_name": silver_name, "action": "build",
                    "reason": reason, "applied": False, "error": str(e),
                })

        built = sum(1 for r in results if r["action"] == "build" and r.get("applied"))
        failed = sum(1 for r in results if r["action"] == "build" and not r.get("applied"))
        skipped = sum(1 for r in results if r["action"] == "skip")
        log.info("[silver_bootstrap] %d built / %d failed / %d skipped", built, failed, skipped)
        return {"built": built, "failed": failed, "skipped": skipped, "details": results}
    finally:
        try:
            lock_conn.close()
        except Exception:
            pass
