"""Gold codegen — agent lead-data-engineer génère les TABLES Gold (vs MV silver).

Diffère de silver_codegen :
1. SPECS_DIR = gold_specs/ (pas silver_specs/)
2. Cible = gold.* (pas silver.*)
3. Sources peuvent être silver.* OR gold.* (gold-of-gold autorisé)
4. Pattern par défaut : CREATE TABLE + procedure refresh_<name>() avec UPSERT
   (au lieu de CREATE MATERIALIZED VIEW DROP+RECREATE comme silver)
5. Améliorations gold-specific lues depuis spec : check_constraints,
   composite_indexes, partitioning, lineage_field
6. Le LLM est instruit de générer ces améliorations dans le SQL final

Réutilise silver_codegen pour :
- Le LLM client (_llm_chat)
- Le bronze schema introspect (introspect_schema)
- L'audit log (_log_version)
- La validation patterns banned (BANNED_PATTERNS)

Architecture refresh :
- Au boot : bootstrap_missing_golds() crée les tables manquantes
- Cron quotidien : refresh_gold_<name>() exécute UPSERT depuis silvers
- Idempotent : ON CONFLICT (key) DO UPDATE SET ..., derniere_maj = now()
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
import yaml

from config import settings
from ingestion.silver_codegen import (
    BANNED_PATTERNS,
    _llm_chat,
    _log_version,
    introspect_schema,
)
from loader import get_agent

log = logging.getLogger("demoema.gold_codegen")

GOLD_SPECS_DIR = Path(__file__).parent / "gold_specs"
GOLD_TRANSFORMS_DIR = Path(__file__).parent / "gold_transforms"
GOLD_TRANSFORMS_DIR.mkdir(exist_ok=True)

# Postgres advisory lock id distinct du silver (0x51EA77B05) et bronze (0xB202E80057BAB)
_GOLD_BOOTSTRAP_LOCK_ID = 0x60BD7700057BAB  # "GOLD7BO5BAB" mnemonic


# ═══════════ Validation gold-specific ═══════════

def _validate_gold_sql(sql: str) -> tuple[bool, str]:
    """Validate SQL gold : doit créer TABLE OR MATERIALIZED VIEW gold.*

    Pattern accepté :
    - CREATE TABLE gold.X (...) [+ INSERT ... ON CONFLICT ...] (recommandé pour
      les gold tables physiques avec UPSERT incremental)
    - CREATE MATERIALIZED VIEW gold.X AS ... (fallback si LLM ne sait pas faire
      table physique)
    """
    if not sql or len(sql) < 50:
        return False, "SQL too short or empty"

    # Match CREATE TABLE gold.X OR CREATE MATERIALIZED VIEW gold.X
    target_match = re.search(
        r"CREATE\s+(?:TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?|MATERIALIZED\s+VIEW\s+)(?P<target>\S+)",
        sql, re.IGNORECASE,
    )
    if not target_match:
        return False, "No CREATE TABLE/MATERIALIZED VIEW found"
    target = target_match.group("target")

    if not target.lower().startswith("gold."):
        return False, f"Target must start with 'gold.' — got '{target}'"

    # Banned patterns (réutilisé de silver_codegen)
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"Banned pattern: {pattern}"

    # Doit citer au moins une source silver.* OR gold.* (gold-of-gold ok)
    if not re.search(r"\b(?:FROM|JOIN)\s+(?:silver|gold)\.", sql, re.IGNORECASE):
        return False, "No silver/gold source referenced (FROM/JOIN required)"

    return True, "ok"


def _version_uid(gold_name: str, sql: str) -> str:
    raw = f"{gold_name}|{sql}|{datetime.now(tz=timezone.utc).isoformat()}"
    return hashlib.sha1(raw.encode()).hexdigest()[:40]


# ═══════════ Spec loading ═══════════

def load_gold_spec(gold_name: str) -> dict | None:
    """Charge spec YAML par gold_name (avec ou sans préfixe gold.)."""
    name = gold_name.replace("gold.", "")
    path = GOLD_SPECS_DIR / f"{name}.yaml"
    if not path.exists():
        log.warning("gold spec not found: %s", path)
        return None
    with path.open(encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    if not spec.get("silver_name", "").startswith("gold."):
        spec["silver_name"] = f"gold.{spec.get('silver_name', name)}"
    return spec


def list_gold_specs() -> list[str]:
    """Liste les gold_specs/*.yaml (skip _ prefix)."""
    return sorted(
        f"gold.{p.stem}"
        for p in GOLD_SPECS_DIR.glob("*.yaml")
        if not p.stem.startswith("_")
    )


# ═══════════ Prompt builder gold ═══════════

def _build_gold_prompt(spec: dict, source_schemas: dict, feedback: str | None = None) -> str:
    gold_name = spec["silver_name"]  # ex: gold.entreprises_master
    goal = spec.get("goal", "")
    source_tables = spec.get("source_tables", [])
    grain = spec.get("grain", "")
    business_logic = spec.get("business_logic", "")
    transformations = spec.get("transformations", "")
    key_columns = spec.get("key_columns", [])
    indexes = spec.get("indexes", [])
    physical = spec.get("physical", True)
    check_constraints = spec.get("check_constraints", [])
    composite_indexes = spec.get("composite_indexes", [])
    partitioning = spec.get("partitioning")
    lineage_field = spec.get("lineage_field", "sources_de_verite")

    schema_block = "\n".join([
        f"### `{tbl}` ({len(cols)} cols)\n" + "\n".join(
            f"- `{c['column']}` : {c['type']}" for c in cols[:30]
        )
        for tbl, cols in source_schemas.items()
    ])

    fb_block = ""
    if feedback:
        fb_block = f"\n## ITÉRATION PRÉCÉDENTE — ERREUR À CORRIGER\n{feedback}\nCorrige.\n"

    # Gold-specific instructions
    pattern_instruction = ""
    if physical:
        pattern_instruction = f"""
## PATTERN ATTENDU : TABLE PHYSIQUE (pas Materialized View)

```sql
-- 1. CREATE TABLE (idempotent IF NOT EXISTS — la table existe déjà après 1er bootstrap)
CREATE TABLE IF NOT EXISTS {gold_name} (
  -- colonnes ici avec types stricts
  -- ajouter CHECK constraints (voir liste ci-dessous)
);

-- 2. CREATE INDEXes (idempotent IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_... ON {gold_name} (...);

-- 3. UPSERT depuis silvers (= refresh de la table)
WITH new_data AS (
  SELECT ... FROM silver.X JOIN silver.Y ...
)
INSERT INTO {gold_name} (col1, col2, ..., derniere_maj)
SELECT col1, col2, ..., now() FROM new_data
ON CONFLICT (key) DO UPDATE SET
  col1 = EXCLUDED.col1,
  col2 = EXCLUDED.col2,
  derniere_maj = now();
```

Le bootstrap exécutera CREATE TABLE + CREATE INDEX + INSERT initial.
Le refresh quotidien ré-exécutera juste l'INSERT/UPSERT (idempotent).
"""
    else:
        pattern_instruction = f"""
## PATTERN ATTENDU : MATERIALIZED VIEW (refresh full)

```sql
CREATE MATERIALIZED VIEW {gold_name} AS
WITH ... AS (...)
SELECT ...
FROM ...;
CREATE INDEX ON {gold_name} (...);
```
"""

    constraints_block = ""
    if check_constraints:
        cc_lines = "\n".join(f"- `{c}`" for c in check_constraints)
        constraints_block = f"\n## CHECK CONSTRAINTS REQUIRED\n{cc_lines}\n"

    composite_idx_block = ""
    if composite_indexes:
        ci_lines = "\n".join(
            f"- `{i.get('cols')}`" + (f" WHERE {i.get('where')}" if i.get('where') else "") +
            f" — purpose: {i.get('purpose','')}"
            for i in composite_indexes
        )
        composite_idx_block = f"\n## COMPOSITE INDEXES REQUIRED\n{ci_lines}\n"

    partitioning_block = ""
    if partitioning:
        partitioning_block = f"\n## PARTITIONING\n{yaml.safe_dump(partitioning)}\n"

    lineage_block = f"\n## LINEAGE FIELD\n- {lineage_field} JSONB : tracker quel silver alimente quel champ.\n"

    return f"""Tu es lead-data-engineer DEMOEMA. Génère le SQL Postgres pour la GOLD TABLE.
{fb_block}
## TARGET
- Nom : `{gold_name}`
- Grain : {grain}
- Sources : {', '.join(source_tables)}
- Goal métier : {goal}

## LOGIQUE MÉTIER
{business_logic}

## TRANSFORMATIONS DEMANDÉES
{transformations}

## KEY COLUMNS
{', '.join(key_columns)}

## SCHÉMAS SOURCES
{schema_block}

{pattern_instruction}
{constraints_block}
{composite_idx_block}
{partitioning_block}
{lineage_block}

## RÈGLES NON NÉGOCIABLES
1. Cible = `gold.{gold_name.replace('gold.','')}` UNIQUEMENT
2. CREATE TABLE IF NOT EXISTS (table physique idempotente) OU MATERIALIZED VIEW
3. INTERDIT : DROP/DELETE/TRUNCATE sur silver.* ou bronze.*
4. CHECK constraints OBLIGATOIRES (voir section dédiée)
5. Composite indexes obligatoires (voir section dédiée)
6. UPSERT pattern : ON CONFLICT (key) DO UPDATE
7. Champ `derniere_maj TIMESTAMPTZ DEFAULT now()` obligatoire
8. Champ `{lineage_field} JSONB` obligatoire (lineage tracking)
9. Pas de LIMIT (full refresh)
10. Cast explicite pour les colonnes JSONB → typées

## SORTIE ATTENDUE
**UNIQUEMENT du SQL Postgres** entre balises ```sql ... ```. Aucun texte avant ou après.
"""


def _extract_sql(response_text: str) -> str | None:
    m = re.search(r"```sql\s*\n(.*?)\n```", response_text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    stripped = response_text.strip()
    if stripped.upper().startswith(("CREATE ", "WITH ", "--", "/*")):
        return stripped
    return None


# ═══════════ Apply gold SQL ═══════════

def _apply_gold_sql(gold_name: str, sql: str, version_uid: str, physical: bool) -> dict:
    """Execute le SQL gold.

    Pour table physique : exécute le bloc complet (CREATE TABLE IF NOT EXISTS
    + INDEXes + INSERT/UPSERT) en transaction.

    Pour MV : DROP CASCADE + CREATE MV (comme silver) — moins recommandé
    car indexes lourds détruits à chaque refresh.
    """
    if not settings.database_url:
        return {"applied": False, "error": "no database_url"}

    qualified = gold_name if "." in gold_name else f"gold.{gold_name}"
    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 0")
                cur.execute("CREATE SCHEMA IF NOT EXISTS gold")
                # MV → DROP+CREATE (comme silver_codegen)
                if not physical:
                    cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {qualified} CASCADE")
                # Pour table physique : on exécute DIRECTEMENT le SQL généré
                # qui contient déjà CREATE TABLE IF NOT EXISTS + ON CONFLICT.
                # Pas de DROP — la table reste, juste UPSERT.
                cur.execute(sql)
                # Audit UPDATE dans la même tx
                cur.execute(
                    "UPDATE audit.silver_specs_versions "
                    "SET applied = true, applied_at = now() WHERE version_uid = %s",
                    (version_uid,),
                )
            conn.commit()
        log.info("[gold_codegen] applied %s (version %s, physical=%s)",
                 gold_name, version_uid[:12], physical)
        return {"applied": True}
    except Exception as e:
        log.exception("[gold_codegen] apply failed for %s", gold_name)
        return {"applied": False, "error": f"{type(e).__name__}: {e}"}


# ═══════════ Main pipeline ═══════════

async def generate_gold_sql(
    gold_name: str,
    feedback: str | None = None,
    apply_immediately: bool = False,
) -> dict:
    """Pipeline génération SQL gold via LLM."""
    spec = load_gold_spec(gold_name)
    if not spec:
        return {"error": f"Spec not found for {gold_name}"}

    if not settings.database_url:
        return {"error": "no database_url"}

    # Introspect schemas des sources (silver.* ou gold.*)
    source_tables = spec.get("source_tables", [])
    with psycopg.connect(settings.database_url) as conn:
        source_schemas = introspect_schema(conn, source_tables)
    missing = [t for t, cols in source_schemas.items() if not cols]
    if missing:
        return {"error": f"source tables missing: {missing}"}

    agent = get_agent("lead-data-engineer")
    if not agent:
        return {"error": "agent lead-data-engineer not loaded"}

    prompt = _build_gold_prompt(spec, source_schemas, feedback=feedback)

    # Tool-calling path (CODEGEN_USE_TOOLS=1) — mêmes garanties que silver
    import os as _os
    use_tools = _os.environ.get("CODEGEN_USE_TOOLS", "").lower() in ("1", "true", "yes")
    tool_audit: list = []
    response = None
    if use_tools and agent.model.startswith("deepseek") and settings.database_url:
        from ingestion.codegen_tools import llm_chat_with_tools
        from deepseek_client import DeepSeekClient
        ds_client = DeepSeekClient(model=agent.model, timeout=settings.deepseek_timeout_s)
        tools_system = (
            agent.system_prompt
            + "\n\nTu disposes de tools READ-ONLY pour vérifier le schéma "
              "Postgres en direct AVANT de produire ton SQL final. Privilégie "
              "`introspect_table`, `find_column`, `peek_sample_rows`, "
              "`look_at_existing_silver`, et VALIDE TON RÉSULTAT via "
              "`test_compile_create` avant de retourner le SQL final entre "
              "balises ```sql ... ```."
        )
        try:
            with psycopg.connect(settings.database_url) as tools_conn:
                response = await llm_chat_with_tools(
                    deepseek_client=ds_client,
                    system=tools_system,
                    user=prompt,
                    conn=tools_conn,
                    max_iterations=6,
                    temperature=agent.temperature,
                    max_tokens=settings.deepseek_max_tokens,
                )
            tool_audit = response.get("tool_audit", [])
            if response.get("error"):
                log.warning(
                    "[gold_codegen] tool-calling pour %s : %s — fallback no-tools",
                    gold_name, response["error"],
                )
                response = None
        except Exception as e:
            log.warning("[gold_codegen] tool-calling exception : %s — fallback no-tools", e)
            response = None
        if response is not None:
            log.info(
                "[gold_codegen] tool-calling pour %s : %d itérations, %d tool calls",
                gold_name, response.get("iterations", 0), len(tool_audit),
            )

    if response is None:
        response = await _llm_chat(
            model=agent.model,
            system=agent.system_prompt,
            user=prompt,
            temperature=agent.temperature,
            num_ctx=agent.num_ctx,
        )

    content = response.get("message", {}).get("content", "") if isinstance(response, dict) else ""
    sql = _extract_sql(content)
    if not sql:
        return {"error": "no SQL extractable", "raw": content[:500]}

    ok, msg = _validate_gold_sql(sql)
    version_uid = _version_uid(gold_name, sql)

    # Persist
    target_path = GOLD_TRANSFORMS_DIR / f"{gold_name.replace('gold.', '')}.sql"
    target_path.write_text(sql, encoding="utf-8")

    # Audit
    _tool_iters = response.get("iterations") if isinstance(response, dict) else None
    _log_version(
        gold_name, spec, sql, ok, msg, version_uid, agent.model, feedback,
        tool_audit=tool_audit if use_tools else None,
        tool_iterations=_tool_iters if use_tools else None,
    )

    result = {
        "gold_name": gold_name,
        "sql": sql,
        "version_uid": version_uid,
        "valid": ok,
        "validation_msg": msg,
        "path": str(target_path),
        "applied": False,
    }

    physical = spec.get("physical", True)
    if ok and apply_immediately:
        applied = _apply_gold_sql(gold_name, sql, version_uid, physical)
        result["applied"] = applied["applied"]
        result.update({f"apply_{k}": v for k, v in applied.items() if k != "applied"})

    return result


# ═══════════ Bootstrap parallèle ═══════════

def _gold_state(conn) -> dict[str, int | None]:
    """Pour chaque table/MV gold, count rows estimé (reltuples)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT n.nspname || '.' || c.relname AS qname,
                   c.reltuples::bigint
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'gold' AND c.relkind IN ('r', 'm')
        """)
        return {row[0]: row[1] for row in cur.fetchall()}


def _topo_levels_gold() -> list[list[str]]:
    """Kahn topo : level 0 = gold sourcing only silvers, level 1+ = gold-of-gold."""
    deps: dict[str, set[str]] = {}
    for p in GOLD_SPECS_DIR.glob("*.yaml"):
        if p.stem.startswith("_"):
            continue
        try:
            spec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        name = spec.get("silver_name") or f"gold.{p.stem}"
        if not name.startswith("gold."):
            name = f"gold.{name}"
        srcs = spec.get("source_tables") or []
        # Dépendances = sources gold.* uniquement (silver.* sont déjà résolus)
        deps[name] = {s for s in srcs if isinstance(s, str) and s.startswith("gold.")}

    levels: list[list[str]] = []
    seen: set[str] = set()
    pending = dict(deps)
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


async def _build_one_gold(gold_name: str, existing: dict, force_empty: bool,
                           sem: asyncio.Semaphore) -> dict:
    """Coroutine codegen d'un gold avec semaphore."""
    rows = existing.get(gold_name)
    needs_build = (rows is None) or (force_empty and rows == 0)
    if not needs_build:
        return {"gold_name": gold_name, "action": "skip", "rows": rows}

    reason = "missing" if rows is None else "empty"
    async with sem:
        log.info("[gold_bootstrap] building %s (%s)", gold_name, reason)
        try:
            r = await generate_gold_sql(gold_name, apply_immediately=True)
            return {
                "gold_name": gold_name,
                "action": "build",
                "reason": reason,
                "valid": r.get("valid"),
                "applied": r.get("applied"),
                "validation_msg": r.get("validation_msg"),
                "error": r.get("error") or r.get("apply_error"),
            }
        except Exception as e:
            log.exception("[gold_bootstrap] failed %s", gold_name)
            return {"gold_name": gold_name, "action": "build", "reason": reason,
                    "applied": False, "error": str(e)}


async def bootstrap_missing_golds(force_empty: bool = True) -> dict:
    """Itère gold_specs/*.yaml et build les tables manquantes/vides en parallèle.

    Pattern identique à silver_codegen.bootstrap_missing_silvers :
    - Topo levels (gold-of-gold doit attendre ses deps gold)
    - asyncio.gather + Semaphore(silver_codegen_parallelism, default 4) par level
    - Advisory lock distinct (_GOLD_BOOTSTRAP_LOCK_ID)
    """
    if not settings.database_url:
        return {"error": "no database_url"}

    lock_conn = psycopg.connect(settings.database_url, autocommit=True)
    try:
        with lock_conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (_GOLD_BOOTSTRAP_LOCK_ID,))
            got_lock = cur.fetchone()[0]
        if not got_lock:
            log.info("[gold_bootstrap] another worker holds the lock — skipping")
            return {"built": 0, "failed": 0, "skipped": 0,
                    "skipped_due_to_lock": True, "details": []}

        # Ensure gold schema exists
        with psycopg.connect(settings.database_url, autocommit=True) as cn:
            with cn.cursor() as c:
                c.execute("CREATE SCHEMA IF NOT EXISTS gold")

        levels = _topo_levels_gold()
        results: list[dict] = []

        with psycopg.connect(settings.database_url) as conn:
            existing = _gold_state(conn)

        parallelism = max(1, int(getattr(settings, "silver_codegen_parallelism", 4)))
        sem = asyncio.Semaphore(parallelism)
        log.info("[gold_bootstrap] %d levels, parallelism=%d (specs=%d)",
                 len(levels), parallelism, sum(len(lv) for lv in levels))

        for level_idx, level in enumerate(levels):
            log.info("[gold_bootstrap] level %d/%d : %d specs %s",
                     level_idx + 1, len(levels), len(level), level)
            level_results = await asyncio.gather(*[
                _build_one_gold(name, existing, force_empty, sem)
                for name in level
            ])
            results.extend(level_results)

            # Refresh existing après chaque level
            with psycopg.connect(settings.database_url) as conn:
                existing = _gold_state(conn)

        built = sum(1 for r in results if r["action"] == "build" and r.get("applied"))
        failed = sum(1 for r in results if r["action"] == "build" and not r.get("applied"))
        skipped = sum(1 for r in results if r["action"] == "skip")
        log.info("[gold_bootstrap] %d built / %d failed / %d skipped (parallelism=%d)",
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
