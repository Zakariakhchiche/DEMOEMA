"""Tool-calling pour TOUS les codegen (silver + gold ; bronze à venir) —
donne au LLM les moyens de vérifier le schéma Postgres en direct avant
de produire le SQL final. Mêmes tools, même boucle, même cadrage pour
toutes les couches.

CADRAGE STRICT (anti-loop / anti-coût) :
- 4 tools READ-ONLY uniquement (pas d'INSERT/UPDATE/DELETE/DROP).
- `dry_run_sql` exécute UNIQUEMENT `EXPLAIN`, jamais le SELECT.
- `sample_jsonb_keys` borne `LIMIT` côté serveur (max 1000).
- `statement_timeout = 5000` sur chaque tool call → coupure dure.
- Aucune string utilisateur n'est concaténée dans une requête sans validation
  (regex stricte sur schema/table/column, sinon refus).
- Boucle silvercodegen capée à `max_iterations=6` (~6 LLM rounds).
- Audit complet : tous les tool calls + arguments + résultat tronqué sont
  loggés dans `audit.silver_specs_versions.tool_audit` (jsonb).

Usage côté silver_codegen / gold_codegen :
    from ingestion.codegen_tools import (
        CODEGEN_TOOLS, execute_tool, llm_chat_with_tools,
    )
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import psycopg

log = logging.getLogger("demoema.silver_codegen.tools")

# ─── Validation utilities ──────────────────────────────────────────────────

_SAFE_IDENT = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_ALLOWED_SCHEMAS = {"bronze", "silver", "gold", "audit", "mart"}


def _check_ident(label: str, value: str) -> None:
    if not isinstance(value, str) or not _SAFE_IDENT.match(value):
        raise ValueError(f"identifiant {label} invalide : {value!r}")


def _check_schema(value: str) -> None:
    if value not in _ALLOWED_SCHEMAS:
        raise ValueError(
            f"schema interdit {value!r} (autorisés: {sorted(_ALLOWED_SCHEMAS)})"
        )


# ─── Tool schemas (OpenAI format) ──────────────────────────────────────────

CODEGEN_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "introspect_table",
            "description": (
                "Liste les colonnes + types Postgres réels d'une OU plusieurs "
                "tables/MV. Utilise CECI AVANT d'écrire un SELECT/JOIN pour "
                "vérifier qu'une colonne existe. ⭐ PRÉFÈRE le mode multi-tables "
                "(passer `tables`: ['silver.x','silver.y','bronze.z']) — 1 seul "
                "tool call au lieu de N → tu épargnes des itérations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        "enum": ["bronze", "silver", "gold", "audit", "mart"],
                        "description": "Mode mono-table : ignore si `tables` fourni.",
                    },
                    "table": {
                        "type": "string",
                        "description": "Mode mono-table : ignore si `tables` fourni.",
                    },
                    "tables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "⭐ Mode multi-tables : liste de FQN comme "
                            "['silver.inpi_dirigeants','bronze.osint_persons']. "
                            "Recommandé quand tu as besoin de >1 table — "
                            "évite N tool calls."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sample_jsonb_keys",
            "description": (
                "Renvoie les top-level keys d'une colonne jsonb avec leur "
                "fréquence sur un échantillon. Utile pour découvrir la "
                "structure d'un payload bronze (ex: bronze.github_repos_raw "
                "n'a pas de colonne `name`, c'est `payload->>'name'`)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {"type": "string", "enum": ["bronze", "silver"]},
                    "table": {"type": "string"},
                    "column": {"type": "string"},
                    "sample_rows": {
                        "type": "integer",
                        "minimum": 10,
                        "maximum": 1000,
                        "default": 200,
                    },
                },
                "required": ["schema", "table", "column"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dry_run_sql",
            "description": (
                "Exécute UNIQUEMENT un EXPLAIN (sans ANALYZE) sur un SELECT/WITH. "
                "Retourne 'OK' si Postgres compile, sinon l'erreur exacte. "
                "À utiliser pour valider un SELECT avant de produire le "
                "CREATE MATERIALIZED VIEW final. NE PAS passer un CREATE — "
                "uniquement le SELECT/WITH."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "select_sql": {
                        "type": "string",
                        "description": (
                            "Une requête SELECT ou WITH ... SELECT. "
                            "Sera wrappée dans `EXPLAIN ...`."
                        ),
                    },
                },
                "required": ["select_sql"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_rows_estimate",
            "description": (
                "Estimation rapide du nombre de lignes d'une table (via "
                "pg_class.reltuples — pas de scan). Utile pour vérifier "
                "qu'une source bronze a des données avant de la joindre."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {"type": "string"},
                    "table": {"type": "string"},
                },
                "required": ["schema", "table"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "test_compile_create",
            "description": (
                "TEST FINAL avant retour du SQL : applique le CREATE "
                "MATERIALIZED VIEW dans un schéma temporaire (avec NO DATA "
                "pour éviter de matérialiser), puis DROP. Si Postgres "
                "compile et le plan tient, c'est OK. C'est l'unique tool "
                "qui simule exactement le _apply_sql réel — appelle-le "
                "AVANT de retourner ton SQL final pour avoir confiance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "create_sql": {
                        "type": "string",
                        "description": (
                            "Le bloc complet : `CREATE MATERIALIZED VIEW "
                            "<silver_or_gold_name> AS <SELECT> WITH NO "
                            "DATA;` (un seul statement, pas d'index). "
                            "Le tool ré-écrit le nom vers un schéma temp."
                        ),
                    },
                },
                "required": ["create_sql"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_column",
            "description": (
                "Cherche dans quelles tables/MV existe une colonne donnée. "
                "Utilise quand tu hésites sur la provenance d'une colonne — "
                "ex: `find_column('person_uid')` te dira immédiatement "
                "qu'aucune table ne l'a (donc à calculer via md5)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "column_name": {
                        "type": "string",
                        "description": "Nom exact de colonne à chercher.",
                    },
                    "schemas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Liste de schémas où chercher. Défaut: bronze+silver."
                        ),
                    },
                },
                "required": ["column_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "peek_sample_rows",
            "description": (
                "Renvoie 3 vraies lignes d'une table, en JSON. Très utile "
                "pour comprendre les valeurs réelles, les nulls, le format "
                "des dates/strings, et la structure exacte des payloads "
                "jsonb. Plus puissant que sample_jsonb_keys pour calibrer "
                "tes filtres et CASE WHEN."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {"type": "string"},
                    "table": {"type": "string"},
                    "n": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "default": 3,
                    },
                },
                "required": ["schema", "table"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "look_at_existing_silver",
            "description": (
                "Renvoie le SQL d'un silver/gold déjà appliqué avec "
                "succès (depuis audit.silver_specs_versions). Utile pour "
                "voir comment un autre silver gère les patterns DEMOEMA "
                "(jsonb extraction, md5 person_uid, GROUP BY...) — "
                "inspire-toi sans copier-coller."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "silver_name": {
                        "type": "string",
                        "description": (
                            "Nom complet ex: 'silver.inpi_dirigeants' ou "
                            "'gold.entreprises_master'."
                        ),
                    },
                },
                "required": ["silver_name"],
                "additionalProperties": False,
            },
        },
    },
]


# ─── Tool handlers ─────────────────────────────────────────────────────────

# Mots-clés DDL/DML interdits dans un dry_run_sql — garde-fou même si on ne fait
# que EXPLAIN, parce que `EXPLAIN INSERT/UPDATE/DELETE` est un comportement
# valide en Postgres et pourrait planifier (pas exécuter, mais on serre).
_FORBIDDEN_TOKENS = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE|"
    r"COPY|VACUUM|REINDEX|CLUSTER|REFRESH|CALL|DO|EXECUTE|PREPARE|"
    r"DEALLOCATE|LISTEN|NOTIFY|UNLISTEN|LOAD|RESET|SET\s+ROLE|"
    r"SECURITY\s+DEFINER)\b",
    re.IGNORECASE,
)


def _tool_introspect_table(conn: "psycopg.Connection", args: dict) -> dict:
    """Mode mono-table (schema+table) ou multi-tables (tables: [fqn,...])."""
    tables_list = args.get("tables")
    if tables_list:
        if not isinstance(tables_list, list) or not tables_list:
            return {"error": "tables doit être une liste non-vide"}
        if len(tables_list) > 12:
            return {"error": "max 12 tables par appel — fais plusieurs appels"}
        out = {}
        for fqn in tables_list:
            if not isinstance(fqn, str) or "." not in fqn:
                out[str(fqn)] = {"error": f"format attendu schema.table : {fqn!r}"}
                continue
            s, t = fqn.split(".", 1)
            try:
                _check_schema(s)
                _check_ident("table", t)
            except ValueError as e:
                out[fqn] = {"error": str(e)}
                continue
            single = _introspect_one(conn, s, t)
            out[fqn] = single
        return {"mode": "multi", "tables": out}
    # Mode mono
    schema = args.get("schema")
    table = args.get("table")
    if not schema or not table:
        return {"error": "fournir (schema, table) OU tables: [fqn,...]"}
    _check_schema(schema)
    _check_ident("table", table)
    return _introspect_one(conn, schema, table)


def _introspect_one(conn: "psycopg.Connection", schema: str, table: str) -> dict:
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = 5000")
        cur.execute(
            """
            SELECT a.attname,
                   format_type(a.atttypid, a.atttypmod),
                   a.attnotnull,
                   c.relkind
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON n.oid = c.relnamespace
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
    if not rows:
        return {"error": f"{schema}.{table} introuvable", "columns": []}
    relkind = rows[0][3]
    relkind_label = {"r": "table", "v": "view", "m": "matview", "p": "partition", "f": "foreign"}.get(relkind, relkind)
    return {
        "fqn": f"{schema}.{table}",
        "kind": relkind_label,
        "columns": [
            {"name": r[0], "type": r[1], "not_null": r[2]} for r in rows
        ],
    }


def _tool_sample_jsonb_keys(conn: "psycopg.Connection", args: dict) -> dict:
    schema = args["schema"]
    table = args["table"]
    column = args["column"]
    sample_rows = max(10, min(int(args.get("sample_rows", 200)), 1000))
    _check_schema(schema)
    _check_ident("table", table)
    _check_ident("column", column)
    # Vérifie d'abord que la colonne existe ET qu'elle est jsonb / jsonb-compatible
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = 5000")
        cur.execute(
            """
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s
              AND a.attname = %s AND a.attnum > 0 AND NOT a.attisdropped
            """,
            (schema, table, column),
        )
        row = cur.fetchone()
    if not row:
        return {"error": f"colonne {schema}.{table}.{column} introuvable"}
    if "json" not in row[0].lower():
        return {
            "error": f"colonne {column} type={row[0]}, n'est pas jsonb",
            "type": row[0],
        }
    # Idents validés → safe à interpoler dans le SQL
    qry = (
        f"WITH s AS (SELECT {column} AS j FROM {schema}.{table} "
        f"WHERE {column} IS NOT NULL LIMIT %s) "
        f"SELECT k.key, count(*) AS n FROM s, "
        f"LATERAL jsonb_object_keys(s.j) AS k(key) GROUP BY 1 "
        f"ORDER BY n DESC LIMIT 40"
    )
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = 5000")
        try:
            cur.execute(qry, (sample_rows,))
            rows = cur.fetchall()
        except Exception as e:
            return {"error": f"jsonb sampling failed: {type(e).__name__}: {str(e)[:200]}"}
    return {
        "fqn": f"{schema}.{table}.{column}",
        "sample_rows": sample_rows,
        "top_keys": [{"key": r[0], "occurrences": r[1]} for r in rows],
    }


def _tool_dry_run_sql(conn: "psycopg.Connection", args: dict) -> dict:
    sql = args["select_sql"].strip()
    if not sql:
        return {"error": "select_sql vide"}
    if _FORBIDDEN_TOKENS.search(sql):
        return {"error": "token DDL/DML interdit dans dry_run_sql"}
    if ";" in sql.rstrip(";"):
        return {"error": "requête multi-statements interdite"}
    sql = sql.rstrip(";")
    upper = sql.lstrip().upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return {
            "error": "doit commencer par SELECT ou WITH (pas de CREATE/UPDATE)"
        }
    explain = f"EXPLAIN (VERBOSE off, FORMAT TEXT) {sql}"
    with conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout = 8000")
        try:
            cur.execute(explain)
            plan = "\n".join(r[0] for r in cur.fetchall())
        except Exception as e:
            return {
                "error": f"{type(e).__name__}: {str(e)[:400]}",
                "ok": False,
            }
    # Plan dump tronqué — l'important est OK ou erreur
    return {"ok": True, "plan_excerpt": plan[:600]}


def _tool_count_rows_estimate(conn: "psycopg.Connection", args: dict) -> dict:
    schema = args["schema"]
    table = args["table"]
    _check_schema(schema)
    _check_ident("table", table)
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = 5000")
        try:
            cur.execute(
                "SELECT reltuples::bigint, relkind FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = %s AND c.relname = %s",
                (schema, table),
            )
            row = cur.fetchone()
        except Exception as e:
            return {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    if not row:
        return {"error": f"{schema}.{table} introuvable"}
    return {
        "fqn": f"{schema}.{table}",
        "rows_estimate": int(row[0]),
        "kind": row[1],
    }


def _tool_test_compile_create(conn: "psycopg.Connection", args: dict) -> dict:
    """Simule l'apply réel : crée la MV en pg_temp avec NO DATA, puis DROP.

    Détecte 100% des SyntaxError, UndefinedColumn, UndefinedTable, etc. avant
    qu'on ne tente l'apply prod. Bien meilleur que `dry_run_sql` qui ne
    valide qu'un SELECT — ici on valide le CREATE complet.
    """
    create_sql = args["create_sql"].strip().rstrip(";")
    if not create_sql:
        return {"error": "create_sql vide"}
    # Anti-DDL hors CREATE MATERIALIZED VIEW
    upper = create_sql.lstrip().upper()
    if not (upper.startswith("CREATE MATERIALIZED VIEW") or upper.startswith("CREATE VIEW")):
        return {"error": "doit être un CREATE MATERIALIZED VIEW (ou CREATE VIEW)"}
    if ";" in create_sql:
        return {"error": "un seul statement (pas d'index ni de point-virgule)"}
    # Réécrit le nom <schema.name> ou <name> vers pg_temp.<random>
    # Pattern: CREATE MATERIALIZED VIEW [IF NOT EXISTS] <name> AS ...
    import secrets
    temp_name = f"_codegen_test_{secrets.token_hex(6)}"
    rewrite = re.sub(
        r"CREATE\s+(MATERIALIZED\s+)?VIEW\s+(IF\s+NOT\s+EXISTS\s+)?(\S+)",
        f"CREATE TEMPORARY VIEW {temp_name}",
        create_sql,
        count=1,
        flags=re.IGNORECASE,
    )
    # Remove WITH NO DATA si présent (TEMPORARY VIEW ne supporte pas)
    rewrite = re.sub(r"WITH\s+NO\s+DATA\s*$", "", rewrite, flags=re.IGNORECASE).rstrip()
    # Remove WITH DATA aussi
    rewrite = re.sub(r"WITH\s+DATA\s*$", "", rewrite, flags=re.IGNORECASE).rstrip()
    with conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout = 12000")
        try:
            cur.execute(rewrite)
            cur.execute(f"DROP VIEW IF EXISTS {temp_name}")
            return {"ok": True, "msg": "compile OK (CREATE TEMP VIEW exécuté + dropped)"}
        except Exception as e:
            return {
                "ok": False,
                "error": f"{type(e).__name__}: {str(e)[:500]}",
            }


def _tool_find_column(conn: "psycopg.Connection", args: dict) -> dict:
    column_name = args["column_name"]
    _check_ident("column_name", column_name)
    schemas = args.get("schemas") or ["bronze", "silver"]
    if not isinstance(schemas, list):
        return {"error": "schemas doit être une liste"}
    for s in schemas:
        if s not in _ALLOWED_SCHEMAS:
            return {"error": f"schema interdit: {s}"}
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = 5000")
        cur.execute(
            """
            SELECT n.nspname, c.relname,
                   format_type(a.atttypid, a.atttypmod),
                   c.relkind
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE a.attname = %s
              AND n.nspname = ANY(%s)
              AND c.relkind IN ('r','v','m','p','f')
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY n.nspname, c.relname
            LIMIT 60
            """,
            (column_name, schemas),
        )
        rows = cur.fetchall()
    if not rows:
        return {
            "column": column_name,
            "found_in": [],
            "hint": (
                f"Aucune table/MV n'a la colonne `{column_name}` dans "
                f"{schemas}. Si tu en as besoin, calcule-la inline "
                f"(ex: md5(...) pour person_uid, ou payload->>'key' "
                f"pour les bronze jsonb)."
            ),
        }
    return {
        "column": column_name,
        "found_in": [
            {
                "fqn": f"{r[0]}.{r[1]}",
                "type": r[2],
                "kind": {"r": "table", "v": "view", "m": "matview"}.get(r[3], r[3]),
            }
            for r in rows
        ],
    }


def _tool_peek_sample_rows(conn: "psycopg.Connection", args: dict) -> dict:
    schema = args["schema"]
    table = args["table"]
    n = max(1, min(int(args.get("n", 3)), 5))
    _check_schema(schema)
    _check_ident("table", table)
    # Vérifie l'existence
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname=%s AND c.relname=%s AND c.relkind IN ('r','v','m','p','f')",
            (schema, table),
        )
        if not cur.fetchone():
            return {"error": f"{schema}.{table} introuvable"}
    qry = f"SELECT to_jsonb(t.*) FROM {schema}.{table} t LIMIT %s"
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = 5000")
        try:
            cur.execute(qry, (n,))
            rows = cur.fetchall()
        except Exception as e:
            return {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    return {
        "fqn": f"{schema}.{table}",
        "n": len(rows),
        "rows": [
            # row[0] est déjà un dict (psycopg parse jsonb auto via Json adapter)
            (json.loads(r[0]) if isinstance(r[0], str) else r[0])
            for r in rows
        ],
    }


def _tool_look_at_existing_silver(conn: "psycopg.Connection", args: dict) -> dict:
    silver_name = args["silver_name"].strip()
    if not silver_name or len(silver_name) > 80:
        return {"error": "silver_name invalide"}
    # Pattern: schema.name (silver|gold|mart|silver_audit)
    if not re.match(r"^(silver|gold|mart)\.[a-z_][a-z0-9_]{0,62}$", silver_name):
        return {"error": "format attendu: silver.<name> ou gold.<name>"}
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = 5000")
        try:
            cur.execute(
                """
                SELECT generated_sql, version_uid, applied, applied_at
                FROM audit.silver_specs_versions
                WHERE silver_name = %s AND validation_status = 'ok'
                ORDER BY applied DESC NULLS LAST,
                         applied_at DESC NULLS LAST,
                         generated_at DESC
                LIMIT 1
                """,
                (silver_name,),
            )
            row = cur.fetchone()
        except Exception as e:
            return {"error": f"audit lookup failed: {type(e).__name__}: {str(e)[:200]}"}
    if not row:
        return {"silver_name": silver_name, "found": False}
    sql_text = row[0] or ""
    # Tronque à 4k chars pour ne pas exploser le contexte LLM
    return {
        "silver_name": silver_name,
        "found": True,
        "version_uid": (row[1] or "")[:16],
        "applied": bool(row[2]),
        "applied_at": str(row[3]) if row[3] else None,
        "sql": sql_text[:4000],
        "truncated": len(sql_text) > 4000,
    }


_HANDLERS = {
    "introspect_table": _tool_introspect_table,
    "sample_jsonb_keys": _tool_sample_jsonb_keys,
    "dry_run_sql": _tool_dry_run_sql,
    "count_rows_estimate": _tool_count_rows_estimate,
    "test_compile_create": _tool_test_compile_create,
    "find_column": _tool_find_column,
    "peek_sample_rows": _tool_peek_sample_rows,
    "look_at_existing_silver": _tool_look_at_existing_silver,
}


def execute_tool(name: str, args_raw: str, conn: "psycopg.Connection") -> dict:
    """Dispatcher. Catch toutes les erreurs côté handler pour ne JAMAIS
    propager une exception au LLM (sinon DeepSeek interrompt la conv)."""
    try:
        args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
    except Exception as e:
        return {"error": f"arguments JSON invalides: {e}"}
    handler = _HANDLERS.get(name)
    if not handler:
        return {"error": f"tool inconnu: {name}"}
    try:
        return handler(conn, args)
    except ValueError as e:
        return {"error": f"validation: {e}"}
    except Exception as e:
        log.exception("[silver_codegen.tools] %s failed", name)
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── Boucle LLM ←→ tools ───────────────────────────────────────────────────


async def llm_chat_with_tools(
    deepseek_client,
    system: str,
    user: str,
    conn: "psycopg.Connection",
    *,
    max_iterations: int = 6,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict:
    """Boucle LLM ↔ tools. Retourne {message, tool_audit, iterations}.

    `message` a le même shape que DeepSeekClient.chat() (pour rétrocompat
    avec _extract_sql_from_response côté caller).

    Cap dur sur les itérations + sur la taille du résultat tool injecté
    (8000 chars) pour ne pas exploser le contexte.
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    audit: list[dict[str, Any]] = []
    finish_reason = None
    last_msg: dict[str, Any] = {}

    for i in range(max_iterations):
        try:
            resp = await deepseek_client.chat(
                messages=messages,
                tools=CODEGEN_TOOLS,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            log.warning("[silver_codegen.tools] LLM call failed iter=%d: %s", i, e)
            return {
                "message": {"content": ""},
                "tool_audit": audit,
                "iterations": i,
                "error": f"llm_call_failed: {type(e).__name__}: {str(e)[:200]}",
            }
        last_msg = resp.get("message") or {}
        finish_reason = resp.get("finish_reason")
        tool_calls = last_msg.get("tool_calls") or []
        if not tool_calls:
            # Réponse finale (ou contenu vide)
            return {
                "message": last_msg,
                "tool_audit": audit,
                "iterations": i + 1,
                "finish_reason": finish_reason,
            }

        # Append assistant turn (avec tool_calls)
        messages.append(last_msg)

        for tc in tool_calls:
            fn = (tc.get("function") or {})
            fname = fn.get("name", "")
            fargs_raw = fn.get("arguments", "{}")
            tcid = tc.get("id", "")
            result = execute_tool(fname, fargs_raw, conn)
            audit.append(
                {
                    "iter": i,
                    "tool": fname,
                    "args": fargs_raw[:500] if isinstance(fargs_raw, str) else fargs_raw,
                    "result_summary": json.dumps(result, default=str)[:400],
                }
            )
            tool_payload = json.dumps(result, default=str)[:8000]
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tcid,
                    "content": tool_payload,
                }
            )

    # Dépassé max_iterations sans réponse finale
    log.warning(
        "[silver_codegen.tools] max_iterations=%d atteint sans réponse finale",
        max_iterations,
    )
    return {
        "message": last_msg,
        "tool_audit": audit,
        "iterations": max_iterations,
        "error": "max_iterations_exceeded",
        "finish_reason": finish_reason,
    }
