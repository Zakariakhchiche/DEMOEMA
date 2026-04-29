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

import asyncio
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
    # Court-circuit : si AUCUNE clé LLM, inutile de tenter quoi que ce soit
    # — ça consomme 0 budget mais loggue clairement pour le maintainer.
    if not settings.ollama_api_key and not settings.deepseek_api_key:
        log.error("[llm_chat] aucune clé LLM disponible (Ollama + DeepSeek vides) — skip")
        raise RuntimeError("no LLM provider configured — set OLLAMA_API_KEY or DEEPSEEK_API_KEY")

    if model.startswith("deepseek"):
        client = DeepSeekClient(model=model, timeout=settings.deepseek_timeout_s)
        return await client.chat(
            messages=messages, temperature=temperature,
            max_tokens=settings.deepseek_max_tokens,
        )

    client = OllamaClient()
    try:
        return await client.chat(
            model=model, messages=messages, stream=False,
            options={"temperature": temperature, "num_ctx": num_ctx},
        )
    except (
        httpx.TimeoutException,
        httpx.RemoteProtocolError,
        httpx.ConnectError,
        httpx.HTTPStatusError,  # 5xx Ollama (vu en prod : 504 Gateway Timeout)
    ) as e:
        # Fallback DeepSeek avec timeout DISTINCT (180s vs Ollama 1200s) :
        # un DeepSeek qui ramerait au delà de 3 min = vraie panne, pas hang
        # raisonnable — on échoue vite plutôt que d'enchaîner 2 timeouts longs.
        if not settings.deepseek_api_key:
            log.warning("[llm_chat] Ollama failed (%s) — pas de fallback DeepSeek (clé absente)",
                        type(e).__name__)
            raise
        log.warning("[llm_chat] Ollama %s failed (%s) — fallback DeepSeek (timeout %ds)",
                    model, type(e).__name__, settings.deepseek_timeout_s)
        try:
            ds = DeepSeekClient(model="deepseek-chat", timeout=settings.deepseek_timeout_s)
            return await ds.chat(
                messages=messages, temperature=temperature,
                max_tokens=settings.deepseek_max_tokens,
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
    max_retries: int = 2,
) -> dict:
    """Generate silver SQL via LLM with retry-on-apply-failure.

    Returns dict with keys:
    - sql: generated SQL (or None on failure)
    - valid: bool
    - msg: validation msg
    - version_uid: audit reference
    - applied: bool (True if apply_immediately + valid + successful apply)
    - retries: nombre de retries effectués

    Retry strategy : si _apply_sql échoue avec UndefinedColumn / SyntaxError /
    DataError côté Postgres, on relance generate_silver_sql avec un feedback qui
    contient l'erreur exacte. Le LLM corrige son SQL au tour suivant.
    Bornage à max_retries pour ne pas boucler indéfiniment + cap budget LLM.
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
        "retries": 0,
    }

    if ok and apply_immediately:
        applied = _apply_sql(silver_name, sql, version_uid)
        result["applied"] = applied["applied"]
        result.update({f"apply_{k}": v for k, v in applied.items() if k != "applied"})

        # Retry-with-feedback : si apply a échoué avec une erreur SQL
        # corrigeable (column inexistant, syntax error, etc.), on regénère le
        # SQL avec l'erreur exacte en feedback. Le LLM produit alors une
        # version corrigée qui ne fait plus la même bévue.
        apply_err = applied.get("error", "") if not applied["applied"] else ""
        retry_indicators = (
            "UndefinedColumn", "SyntaxError", "DataError",
            "DatatypeMismatch", "InvalidTextRepresentation",
            "UndefinedTable", "DuplicateColumn", "WrongObjectType",
        )
        should_retry = (
            not applied["applied"]
            and any(ind in apply_err for ind in retry_indicators)
            and max_retries > 0
        )
        if should_retry:
            log.warning(
                "[silver_codegen] %s : apply failed (%s) — retry %d/%d avec feedback LLM",
                silver_name, apply_err[:120],
                (max_retries if feedback is None else max_retries - 1) - max_retries + 1,
                max_retries,
            )
            new_feedback = (
                (feedback + "\n\n---\n" if feedback else "")
                + f"Le SQL généré au tour précédent a échoué à l'apply Postgres avec :\n"
                  f"```\n{apply_err[:800]}\n```\n"
                  f"Corrige le SQL en évitant cette erreur. Vérifie EXACTEMENT le nom"
                  f" des colonnes dans les SCHÉMAS BRONZE DISPONIBLES — n'invente aucune"
                  f" colonne. Pour les indexes multi-colonnes, syntaxe correcte :"
                  f" `CREATE INDEX ON t (col1, col2)` (UNE seule paire de parenthèses)."
            )
            retry = await generate_silver_sql(
                silver_name=silver_name,
                feedback=new_feedback,
                apply_immediately=True,
                max_retries=max_retries - 1,
            )
            retry["retries"] = result["retries"] + 1 + retry.get("retries", 0)
            return retry

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


def _list_downstream_silvers(conn, qualified: str) -> list[str]:
    """Liste les MV silver.* qui dépendent de `qualified` via pg_depend.

    Pré-check INFORMATIF avant DROP CASCADE — pour logger ce qu'on s'apprête
    à dropper. Ne BLOQUE jamais (le DROP atomique reste la seule option pour
    éviter les indexes dupliqués). Mais l'opérateur sait quoi rebuild ensuite.
    """
    schema, table = qualified.split(".", 1)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT n2.nspname || '.' || c2.relname AS downstream
                FROM pg_depend d
                JOIN pg_rewrite r ON d.objid = r.oid
                JOIN pg_class c2 ON r.ev_class = c2.oid
                JOIN pg_namespace n2 ON n2.oid = c2.relnamespace
                JOIN pg_class c1 ON d.refobjid = c1.oid
                JOIN pg_namespace n1 ON n1.oid = c1.relnamespace
                WHERE n1.nspname = %s AND c1.relname = %s
                  AND c2.relkind = 'm'
                  AND (n2.nspname, c2.relname) != (%s, %s)
                """,
                (schema, table, schema, table),
            )
            return [r[0] for r in cur.fetchall()]
    except Exception:
        return []


def _apply_sql(silver_name: str, sql: str, version_uid: str) -> dict:
    """Execute the generated SQL atomically.

    Drops the existing MV (CASCADE — also drops its indexes) inside the same
    transaction as the new CREATE, so a re-applied silver fully replaces its
    predecessor and never accumulates duplicate indexes. Postgres has no
    CREATE OR REPLACE MATERIALIZED VIEW, so DROP+CREATE is the only path.

    Pré-check informatif `pg_depend` : log les silvers downstream qui seront
    drop-cascadés par cette opération. Permet à l'opérateur de savoir quoi
    rebuild ensuite (via le bootstrap one-shot ou le maintainer).
    """
    if not settings.database_url:
        return {"applied": False, "error": "no database_url"}
    qualified = silver_name if "." in silver_name else f"silver.{silver_name}"
    downstream: list[str] = []
    try:
        with psycopg.connect(settings.database_url) as conn:
            downstream = _list_downstream_silvers(conn, qualified)
            if downstream:
                log.warning(
                    "[silver_codegen] %s : DROP CASCADE va aussi dropper %d downstream MV : %s — "
                    "ils devront être rebuild (next bootstrap tick + maintainer s'en chargera)",
                    qualified, len(downstream), downstream,
                )
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 0")
                cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {qualified} CASCADE")
                cur.execute(sql)
                # Audit UPDATE dans la MÊME transaction — ferme la fenêtre où
                # la MV était créée mais audit non mis à jour (bug SE-2).
                cur.execute(
                    "UPDATE audit.silver_specs_versions "
                    "SET applied = true, applied_at = now() WHERE version_uid = %s",
                    (version_uid,),
                )
            conn.commit()
        log.info("[silver_codegen] applied %s (version %s, downstream=%d)",
                 silver_name, version_uid[:12], len(downstream))
        return {"applied": True, "downstream_dropped": downstream}
    except Exception as e:
        log.exception("[silver_codegen] apply failed for %s", silver_name)
        return {"applied": False, "error": f"{type(e).__name__}: {e}",
                "downstream_dropped": downstream}


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


def _bronze_sources_all_empty(source_tables: list[str]) -> list[str]:
    """Retourne la liste des sources bronze.* à 0 lignes parmi celles fournies.

    Renvoie une liste VIDE soit si aucun bronze source n'est listé (le silver
    ne dépend que d'autres silvers), soit si au moins UN bronze source a des
    rows. Renvoie la liste des bronze vides UNIQUEMENT quand TOUS les bronzes
    listés sont à 0 — signal pour skip safe le silver bootstrap.

    Lit `c.reltuples` (rapide, pas de scan). reltuples=-1 (jamais analyzé)
    est traité comme "inconnu, pas vide" → no-skip safe.
    """
    if not settings.database_url:
        return []
    bronze_tables = [t for t in source_tables if t.startswith("bronze.")]
    if not bronze_tables:
        return []
    empty: list[str] = []
    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        for full_name in bronze_tables:
            schema, table = full_name.split(".", 1)
            cur.execute(
                """
                SELECT c.reltuples::bigint
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s AND c.relname = %s AND c.relkind IN ('r','m')
                """,
                (schema, table),
            )
            row = cur.fetchone()
            if row is None:
                # table absente = pire que vide, mais le LLM va échouer cleanly
                # via "bronze tables missing" check de generate_silver_sql.
                continue
            rt = row[0]
            if rt == 0:
                empty.append(full_name)
    # Retourne la liste vide si au moins une source a des rows OU est inconnue
    return empty if len(empty) == len(bronze_tables) else []


def _load_silver_deps() -> dict[str, set[str]]:
    """Return {silver_name: {silver.dep1, silver.dep2}} from every spec.

    Bronze sources are filtered out — only `silver.*` deps create edges in the
    DAG (a silver depending on bronze.* has no in-DAG predecessor).
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
    return deps


def _topo_sort_specs() -> list[str]:
    """Return spec names in a flat topological order (legacy / tests).

    Edges come from spec.source_tables : if `silver.B` lists `silver.A` as a
    source, A is built before B. Pure bronze-source specs come first.
    Cycles fall back to alphabetical order for the unresolved tail.
    """
    return [name for level in _topo_levels_specs() for name in level]


def _topo_levels_specs() -> list[list[str]]:
    """Return spec names grouped by topological level (Kahn-style).

    Level 0 = silvers with no silver.* deps (pure bronze sources) — buildable
    immediately in parallel.
    Level k = silvers whose silver.* deps are all in levels < k.

    Within a level, all silvers are independent — codegen + apply can run
    fully in parallel without race or correctness risk. Levels themselves are
    sequential : level k must finish before level k+1 starts (a silver-of-
    silver needs its deps' MVs to exist before introspect_schema sees their
    columns).

    Cycles : the unresolved tail is dropped into a final level alphabetically
    sorted (matches `_topo_sort_specs` legacy behavior — tests assert this).
    """
    pending = _load_silver_deps()
    levels: list[list[str]] = []
    seen: set[str] = set()
    while pending:
        ready = sorted(n for n, d in pending.items() if d.issubset(seen | {n}))
        if not ready:
            levels.append(sorted(pending))
            break
        levels.append(ready)
        for n in ready:
            seen.add(n)
            pending.pop(n, None)
    return levels


# Postgres advisory lock id for bootstrap mutual exclusion.
# Uvicorn workers > 1 each run the FastAPI lifespan separately, which fired
# bootstrap N times in parallel — observed on prod with 2 workers racing on
# silver.bodacc_annonces (29M rows) and burning LLM credits twice. A
# session-level pg_try_advisory_lock with a constant id ensures at most one
# bootstrap runs at any moment cluster-wide.
_BOOTSTRAP_LOCK_ID = 0x51EA77B05  # "SILVA77BO5" mnemonic — arbitrary 64-bit


async def _build_one_silver(silver_name: str, existing: dict[str, int | None],
                             force_empty: bool, sem: asyncio.Semaphore) -> dict:
    """Build (or skip) a single silver under semaphore — coroutine for gather().

    Encapsule le decision-tree par silver (skip vs build) + le pré-check
    bronze-empty pour qu'on puisse le scheduler en parallèle dans `gather`.
    """
    rows = existing.get(silver_name)
    needs_build = (rows is None) or (force_empty and rows == 0)
    if not needs_build:
        return {"silver_name": silver_name, "action": "skip", "rows": rows}

    reason = "missing" if rows is None else "empty"
    # Pré-check sources vides : si TOUTES les bronze.* du spec sont à
    # 0 lignes, le LLM gaspillerait son budget pour générer un silver
    # qui restera à 0. On warn et skip — le bootstrap re-tentera au
    # tick maintainer suivant quand bronze ingest aura tourné.
    spec = load_silver_spec(silver_name)
    if spec:
        empty_bronze = _bronze_sources_all_empty(spec.get("source_tables", []))
        if empty_bronze:
            log.warning(
                "[silver_bootstrap] skip %s — all bronze sources empty (%s)",
                silver_name, empty_bronze,
            )
            return {
                "silver_name": silver_name, "action": "skip",
                "reason": "bronze_empty", "empty_sources": empty_bronze,
            }

    # Le sémaphore limite le parallélisme effectif (LLM rate limits + DB load).
    # On l'acquiert APRÈS les pré-checks pour ne pas bloquer un slot pendant
    # qu'on lit YAML / pg_class.
    async with sem:
        log.info("[silver_bootstrap] building %s (%s)", silver_name, reason)
        try:
            r = await generate_silver_sql(silver_name, apply_immediately=True)
            return {
                "silver_name": silver_name,
                "action": "build",
                "reason": reason,
                "valid": r.get("valid"),
                "applied": r.get("applied"),
                "validation_msg": r.get("validation_msg"),
                "error": r.get("error") or r.get("apply_error"),
            }
        except Exception as e:
            log.exception("[silver_bootstrap] failed %s", silver_name)
            return {
                "silver_name": silver_name, "action": "build",
                "reason": reason, "applied": False, "error": str(e),
            }


async def bootstrap_missing_silvers(force_empty: bool = True) -> dict:
    """Walk every silver spec YAML and ensure the matching MV exists with rows.

    Used at engine startup AND on the migrate-VPS scenario where Postgres is
    empty after Bronze has been ingested. For each spec :
      - MV missing                    → generate + apply
      - MV exists but 0 rows (and force_empty=True) → regenerate + apply
      - MV exists with rows           → leave alone (refresh job handles it)

    Mutual exclusion (vs autres workers Uvicorn) : Postgres session-level
    advisory lock — un seul worker du cluster boostrap à la fois.

    Parallélisme INTRA-bootstrap : les specs sont groupées par niveau topo
    via `_topo_levels_specs()`. Au sein d'un niveau (silvers indépendants),
    on lance `silver_codegen_parallelism` codegen+apply en parallèle via
    `asyncio.gather` + `Semaphore`. On attend la fin du niveau avant de
    passer au suivant — un silver-of-silver a besoin que ses deps existent
    pour que `introspect_schema` voie leurs colonnes.

    Returns a per-spec report.
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

        levels = _topo_levels_specs()
        results: list[dict] = []

        with psycopg.connect(settings.database_url) as conn:
            existing = _silver_state(conn)

        parallelism = max(1, int(settings.silver_codegen_parallelism))
        sem = asyncio.Semaphore(parallelism)
        log.info("[silver_bootstrap] %d levels, parallelism=%d (specs=%d)",
                 len(levels), parallelism,
                 sum(len(lv) for lv in levels))

        for level_idx, level in enumerate(levels):
            log.info("[silver_bootstrap] level %d/%d : %d specs %s",
                     level_idx + 1, len(levels), len(level), level)
            level_results = await asyncio.gather(*[
                _build_one_silver(name, existing, force_empty, sem)
                for name in level
            ])
            results.extend(level_results)

            # Mettre à jour `existing` après chaque niveau pour que les
            # silvers buildés deviennent visibles aux niveaux suivants
            # (sinon un level k+1 dépendant pourrait croire que sa source
            # est encore "missing" et la regénérer à tort).
            with psycopg.connect(settings.database_url) as conn:
                existing = _silver_state(conn)

        built = sum(1 for r in results if r["action"] == "build" and r.get("applied"))
        failed = sum(1 for r in results if r["action"] == "build" and not r.get("applied"))
        skipped = sum(1 for r in results if r["action"] == "skip")
        log.info("[silver_bootstrap] %d built / %d failed / %d skipped (parallelism=%d)",
                 built, failed, skipped, parallelism)
        return {
            "built": built, "failed": failed, "skipped": skipped,
            "parallelism": parallelism, "levels": len(levels),
            "details": results,
        }
    finally:
        try:
            lock_conn.close()
        except Exception:
            pass
