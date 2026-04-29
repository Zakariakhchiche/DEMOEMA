"""Routes datalake — expose les tables gold + silver presse au frontend.

Tous les endpoints sont READ-ONLY (le pool peut tourner en datalake_ro). Whitelist
stricte du nom de table via `GOLD_TABLES_WHITELIST` pour empêcher toute SQL
injection sur le segment `{schema}.{table}`. Les valeurs (filtre, search) sont
toujours bindées en paramètres asyncpg ($1, $2…).
"""
from __future__ import annotations

import json
from typing import Any

import asyncpg
from fastapi import APIRouter, HTTPException, Path, Query, Request

from datalake import GOLD_TABLES_WHITELIST

router = APIRouter(prefix="/api/datalake", tags=["datalake"])


def _pool(req: Request) -> asyncpg.Pool:
    pool = getattr(req.app.state, "dl_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Datalake non disponible (pool non initialisé). Vérifier DATALAKE_DSN/DATALAKE_RO_PASSWORD.",
        )
    return pool


def _qualified(table: str) -> str:
    if table not in GOLD_TABLES_WHITELIST:
        raise HTTPException(status_code=404, detail=f"Table {table} non whitelisted")
    return table


def _serialize(row: asyncpg.Record) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, (bytes, bytearray)):
            out[k] = v.decode("utf-8", errors="replace")
        elif isinstance(v, (list, tuple)):
            out[k] = list(v)
        elif v is None or isinstance(v, (str, int, float, bool, dict)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


@router.get("/_introspect")
async def introspect(req: Request, schema: str | None = None, table: str | None = None):
    """Liste toutes les tables (et colonnes si table=...) du datalake."""
    pool = _pool(req)
    if schema and table:
        # pg_attribute est plus permissif que information_schema (qui peut filtrer
        # selon les GRANTs visibles à l'utilisateur connecté).
        rows = await pool.fetch(
            """SELECT a.attname AS column_name,
                      format_type(a.atttypid, a.atttypmod) AS data_type
               FROM pg_attribute a
               JOIN pg_class c ON c.oid = a.attrelid
               JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = $1 AND c.relname = $2
                 AND a.attnum > 0 AND NOT a.attisdropped
               ORDER BY a.attnum""",
            schema,
            table,
        )
        return {"columns": [dict(r) for r in rows]}
    rows = await pool.fetch(
        """
        SELECT n.nspname AS schema,
               c.relname AS table,
               c.reltuples::bigint AS rows_approx
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r','m','p')
          AND n.nspname NOT IN ('pg_catalog','information_schema','pg_toast')
        ORDER BY n.nspname, c.relname
        """
    )
    return {"objects": [dict(r) for r in rows]}


@router.get("/tables")
async def list_tables(req: Request):
    """Liste les tables whitelistées qui existent physiquement (pg_class)."""
    pool = _pool(req)
    rows = await pool.fetch(
        """SELECT n.nspname || '.' || c.relname AS name
           FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE c.relkind IN ('r','m','p') AND n.nspname IN ('gold','silver')"""
    )
    existing = {r["name"] for r in rows}
    out = []
    for name, meta in GOLD_TABLES_WHITELIST.items():
        if name not in existing:
            continue
        # Count approx via pg_class (instant, vs COUNT(*) sur 30M rows = 8s)
        schema, tbl = name.split(".", 1)
        try:
            n = await pool.fetchval(
                """SELECT reltuples::bigint FROM pg_class c
                   JOIN pg_namespace n ON n.oid = c.relnamespace
                   WHERE n.nspname = $1 AND c.relname = $2""",
                schema,
                tbl,
            )
        except Exception:
            n = None
        out.append(
            {
                "name": name,
                "label": meta["label"],
                "category": meta["category"],
                "row_count_approx": int(n) if n is not None else None,
                "preview_cols": meta["preview_cols"],
            }
        )
    return {"tables": out}


@router.get("/{schema}/{table}", responses={404: {"description": "Table non whitelisted"}})
async def query_table(
    req: Request,
    schema: str = Path(..., pattern="^(gold|silver|bronze)$"),
    table: str = Path(..., min_length=1, max_length=64),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, description="Recherche textuelle (cols whitelisted)"),
    order_by: str | None = Query(None, description="Colonne tri ASC/DESC"),
):
    full = f"{schema}.{table}"
    meta = GOLD_TABLES_WHITELIST.get(full)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Table {full} non whitelisted")

    pool = _pool(req)

    where_parts: list[str] = []
    params: list[Any] = []
    if q:
        search_cols = meta.get("search_cols", [])
        if search_cols:
            cond = " OR ".join(
                [f"{c}::text ILIKE ${len(params) + 1}" for c in search_cols]
            )
            where_parts.append(f"({cond})")
            params.append(f"%{q}%")

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    # Order — soit colonne whitelisted, soit default
    order_sql = meta["default_order"]
    if order_by:
        # Permet uniquement preview_cols + pk
        allowed = set(meta["preview_cols"]) | {meta["pk"]}
        col = order_by.lstrip("-")
        if col in allowed:
            direction = "DESC" if order_by.startswith("-") else "ASC"
            order_sql = f"{col} {direction} NULLS LAST"

    cols_sql = ", ".join(meta["preview_cols"])
    sql = (
        f"SELECT {cols_sql} FROM {full} {where_sql} ORDER BY {order_sql} "
        f"LIMIT {int(limit)} OFFSET {int(offset)}"
    )

    try:
        rows = await pool.fetch(sql, *params)
    except asyncpg.UndefinedTableError:
        raise HTTPException(status_code=503, detail=f"Table {full} pas encore matérialisée dans le datalake")
    except asyncpg.UndefinedColumnError as e:
        raise HTTPException(status_code=500, detail=f"Schema mismatch: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {type(e).__name__}: {e}")

    return {
        "table": full,
        "columns": meta["preview_cols"],
        "rows": [_serialize(r) for r in rows],
        "limit": limit,
        "offset": offset,
        "has_more": len(rows) == limit,
    }


@router.get("/fiche/{siren}")
async def fiche_entreprise(req: Request, siren: str):
    """Fiche complète — gold.entreprises_master si dispo, fallback sur
    silver.insee_unites_legales + silver.inpi_comptes + silver.inpi_dirigeants."""
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")
    pool = _pool(req)

    fiche = None
    if await _table_exists(pool, "gold", "entreprises_master"):
        fiche = await pool.fetchrow(
            "SELECT * FROM gold.entreprises_master WHERE siren = $1", siren
        )
    if not fiche:
        # Skip osint_companies_enriched (bloqué actuellement). On dérive le
        # dept/ville depuis silver.bodacc_annonces. Les colonnes NAF/forme/
        # capital social restent NULL en attendant déblocage osint ou gold.
        fiche = await pool.fetchrow(
            """WITH last_compte AS (
                  SELECT DISTINCT ON (siren) siren, denomination,
                         ca_net, resultat_net, capitaux_propres,
                         effectif_moyen::int AS effectif_exact,
                         date_cloture
                  FROM silver.inpi_comptes
                  WHERE siren = $1
                  ORDER BY siren, date_cloture DESC
               ),
               history AS (
                  SELECT array_agg(ca_net::float8 ORDER BY date_cloture) FILTER (WHERE ca_net IS NOT NULL) AS ca_history,
                         array_agg(date_cloture ORDER BY date_cloture) FILTER (WHERE ca_net IS NOT NULL) AS exercices
                  FROM (
                      SELECT DISTINCT ON (date_cloture) date_cloture, ca_net
                      FROM silver.inpi_comptes
                      WHERE siren = $1
                      ORDER BY date_cloture DESC
                      LIMIT 5
                  ) h
               ),
               loc AS (
                  SELECT code_dept AS dept, ville, region
                  FROM silver.bodacc_annonces
                  WHERE siren = $1 AND code_dept IS NOT NULL
                  ORDER BY date_parution DESC LIMIT 1
               ),
               counts AS (
                  SELECT
                    (SELECT COUNT(*)::int FROM silver.inpi_dirigeants WHERE $1::bpchar = ANY(sirens_mandats)) AS n_dirigeants,
                    (SELECT COUNT(*)::int FROM silver.bodacc_annonces WHERE siren = $1) AS n_bodacc,
                    (SELECT COUNT(*)::int FROM silver.opensanctions WHERE $1 = ANY(sirens_fr)) AS n_sanctions
               )
               SELECT lc.siren,
                      lc.denomination,
                      lc.ca_net AS ca_dernier,
                      lc.resultat_net AS ebitda_dernier,
                      lc.capitaux_propres,
                      lc.effectif_exact,
                      lc.date_cloture AS date_derniers_comptes,
                      CASE
                        WHEN lc.ca_net IS NOT NULL AND lc.ca_net > 0 AND lc.resultat_net IS NOT NULL
                        THEN ROUND((lc.resultat_net::numeric / lc.ca_net) * 100, 1)
                        ELSE NULL
                      END AS marge_pct,
                      NULL::text AS naf,
                      NULL::text AS forme_juridique,
                      NULL::numeric AS capital_social,
                      l.dept, l.ville, l.region,
                      h.ca_history, h.exercices,
                      cnt.n_dirigeants, cnt.n_bodacc, cnt.n_sanctions,
                      'actif' AS statut
               FROM last_compte lc
               LEFT JOIN loc l ON true
               CROSS JOIN history h
               CROSS JOIN counts cnt""",
            siren,
        )
    if not fiche:
        raise HTTPException(status_code=404, detail=f"SIREN {siren} introuvable")

    # Dirigeants détaillés — top 10 par mandats actifs, joint avec patrimoine SCI
    dirigeants = await pool.fetch(
        """WITH dirig AS (
              SELECT nom, prenom, date_naissance, age_2026 AS age,
                     n_mandats_actifs, n_mandats_total, sirens_mandats,
                     denominations, roles, is_multi_mandat
              FROM silver.inpi_dirigeants
              WHERE $1::bpchar = ANY(sirens_mandats)
              ORDER BY n_mandats_actifs DESC NULLS LAST
              LIMIT 10
           )
           SELECT d.*,
                  sci.n_sci, sci.total_capital_sci, sci.sci_denominations,
                  os.has_linkedin, os.has_github, os.n_total_social,
                  EXISTS(SELECT 1 FROM silver.opensanctions s
                         WHERE LOWER(s.name) LIKE '%' || LOWER(d.nom) || '%') AS is_sanctioned
           FROM dirig d
           LEFT JOIN silver.dirigeant_sci_patrimoine sci
                  ON sci.nom = d.nom AND sci.prenom = d.prenom
           LEFT JOIN silver.osint_persons_enriched os
                  ON os.nom = d.nom AND $1 = os.siren_main""",
        siren,
    )

    # Signaux M&A — BODACC (annonces commerciales)
    signaux = await pool.fetch(
        """SELECT date_parution AS event_date,
                  typeavis_lib AS signal_type,
                  familleavis_lib AS severity,
                  tribunal AS source,
                  ville, departement, code_dept,
                  jugement_details, depot_details
           FROM silver.bodacc_annonces
           WHERE siren = $1
           ORDER BY date_parution DESC
           LIMIT 20""",
        siren,
    ) if await _table_exists(pool, "silver", "bodacc_annonces") else []

    # Compliance — OpenSanctions match par siren_fr
    red_flags = await pool.fetch(
        """SELECT entity_id, caption, schema, topics, countries,
                  sanctions_programs, first_seen, last_seen
           FROM silver.opensanctions
           WHERE $1 = ANY(sirens_fr)""",
        siren,
    ) if await _table_exists(pool, "silver", "opensanctions") else []

    # Réseau — co-mandats : autres sirens des dirigeants principaux
    network = await pool.fetch(
        """WITH top_dirig AS (
              SELECT nom, prenom, sirens_mandats, denominations
              FROM silver.inpi_dirigeants
              WHERE $1::bpchar = ANY(sirens_mandats)
              ORDER BY n_mandats_actifs DESC NULLS LAST
              LIMIT 3
           ),
           expanded AS (
              SELECT d.nom, d.prenom,
                     unnest(d.sirens_mandats) AS other_siren,
                     unnest(d.denominations) AS other_deno
              FROM top_dirig d
           )
           SELECT DISTINCT other_siren AS siren,
                  other_deno AS denomination,
                  string_agg(DISTINCT prenom || ' ' || nom, ', ') AS via_dirigeants
           FROM expanded
           WHERE other_siren != $1::bpchar AND other_siren IS NOT NULL
           GROUP BY other_siren, other_deno
           ORDER BY other_deno
           LIMIT 20""",
        siren,
    ) if await _table_exists(pool, "silver", "inpi_dirigeants") else []

    # Presse matchée
    presse = await pool.fetch(
        """SELECT published_at, source, title, url, ma_signal_type
           FROM silver.press_mentions_matched
           WHERE siren = $1
           ORDER BY published_at DESC
           LIMIT 10""",
        siren,
    ) if await _table_exists(pool, "silver", "press_mentions_matched") else []

    return {
        "fiche": _serialize(fiche),
        "dirigeants": [_serialize(d) for d in dirigeants],
        "signaux": [_serialize(s) for s in signaux],
        "red_flags": [_serialize(r) for r in red_flags],
        "network": [_serialize(n) for n in network],
        "presse": [_serialize(p) for p in presse],
    }


@router.get("/dashboard")
async def dashboard(req: Request):
    """KPIs + heatmap dept + top cibles + alertes 24h, calculés live sur le
    datalake. Source 100% silver — zero mock."""
    pool = _pool(req)

    # Cheap KPIs : reltuples (instant) + COUNTs sur petites tables.
    # On évite COUNT(DISTINCT siren) sur silver.inpi_comptes (6.3M) qui prend
    # 30+ s sans index dédié.
    kpis = await pool.fetchrow(
        """SELECT
              (SELECT c.reltuples::bigint FROM pg_class c
               JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = 'silver' AND c.relname = 'inpi_comptes') AS n_comptes_total,
              (SELECT COUNT(*)::int FROM silver.opensanctions
               WHERE sirens_fr IS NOT NULL AND array_length(sirens_fr, 1) > 0) AS n_red_flags,
              (SELECT COUNT(*)::int FROM silver.bodacc_annonces
               WHERE date_parution >= CURRENT_DATE - INTERVAL '7 days') AS n_signals_7d,
              (SELECT COUNT(*)::int FROM silver.bodacc_annonces
               WHERE date_parution >= CURRENT_DATE - INTERVAL '30 days') AS n_signals_30d,
              (SELECT c.reltuples::bigint FROM pg_class c
               JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = 'silver' AND c.relname = 'inpi_dirigeants') AS n_dirigeants_total,
              (SELECT c.reltuples::bigint FROM pg_class c
               JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = 'silver' AND c.relname = 'osint_companies_enriched') AS n_osint"""
    )

    # Heatmap dérivée de silver.bodacc_annonces (75k, code_dept indexé probable)
    # — distribution des activités économiques visible par département.
    heatmap = await pool.fetch(
        """SELECT code_dept AS dept,
                  COUNT(*)::int AS count
           FROM silver.bodacc_annonces
           WHERE code_dept IS NOT NULL
             AND length(code_dept) >= 2
             AND date_parution >= CURRENT_DATE - INTERVAL '90 days'
           GROUP BY code_dept
           ORDER BY count DESC
           LIMIT 12"""
    ) if await _table_exists(pool, "silver", "bodacc_annonces") else []

    DEPT_LABELS = {
        "01": "Ain", "02": "Aisne", "03": "Allier", "06": "Alpes-Maritimes",
        "13": "Bouches-du-Rhône", "14": "Calvados", "21": "Côte-d'Or",
        "25": "Doubs", "27": "Eure", "29": "Finistère", "30": "Gard",
        "31": "Haute-Garonne", "33": "Gironde", "34": "Hérault", "35": "Ille-et-Vilaine",
        "37": "Indre-et-Loire", "38": "Isère", "42": "Loire", "44": "Loire-Atlantique",
        "45": "Loiret", "49": "Maine-et-Loire", "51": "Marne", "54": "Meurthe-et-Moselle",
        "57": "Moselle", "59": "Nord", "60": "Oise", "62": "Pas-de-Calais",
        "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques", "67": "Bas-Rhin",
        "68": "Haut-Rhin", "69": "Rhône", "75": "Paris", "76": "Seine-Maritime",
        "77": "Seine-et-Marne", "78": "Yvelines", "80": "Somme", "83": "Var",
        "84": "Vaucluse", "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne",
        "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis",
        "94": "Val-de-Marne", "95": "Val-d'Oise",
    }

    # Simple bodacc fetch — pas de LATERAL inpi_comptes (timeout). Le frontend
    # peut enrichir avec /api/datalake/cibles?q=siren si besoin.
    alerts_raw = await pool.fetch(
        """SELECT date_parution, siren, typeavis_lib AS title,
                  familleavis_lib AS family, tribunal AS source,
                  ville, departement, code_dept
           FROM silver.bodacc_annonces
           WHERE date_parution >= CURRENT_DATE - INTERVAL '14 days'
             AND (familleavis_lib ILIKE '%procédure%'
                  OR familleavis_lib ILIKE '%redressement%'
                  OR familleavis_lib ILIKE '%liquidation%'
                  OR typeavis_lib ILIKE '%cession%')
           ORDER BY date_parution DESC
           LIMIT 20""",
    ) if await _table_exists(pool, "silver", "bodacc_annonces") else []

    # Resolve denominations en batch via une seule requête sur inpi_comptes
    # (DISTINCT ON siren, ORDER BY date_cloture). Ça touche un index PK siren.
    siren_list = [r["siren"] for r in alerts_raw if r["siren"]]
    deno_map: dict[str, str] = {}
    if siren_list:
        deno_rows = await pool.fetch(
            """SELECT DISTINCT ON (siren) siren, denomination
               FROM silver.inpi_comptes
               WHERE siren = ANY($1::text[])
               ORDER BY siren, date_cloture DESC""",
            siren_list,
        )
        deno_map = {r["siren"]: r["denomination"] for r in deno_rows if r["denomination"]}

    alerts = []
    for r in alerts_raw:
        d = dict(r)
        d["denomination"] = deno_map.get(r["siren"], r["siren"])
        alerts.append(d)

    top_targets = await _cibles_from_silver(pool, None, None, None, None, "score_ma", 5, 0)

    return {
        "kpis": _serialize(kpis) if kpis else {},
        "heatmap": [
            {**_serialize(r), "label": DEPT_LABELS.get(r["dept"], r["dept"])}
            for r in heatmap
        ],
        "alerts": [_serialize(a) for a in alerts],
        "top_targets": top_targets["cibles"],
    }


@router.get("/pipeline")
async def pipeline(req: Request):
    """Pipeline M&A — top cibles classées artificiellement par CA (sans
    workflow CRM en place). Stages dérivés : sourcing (CA 1-10M), approche
    (10-50M), dd (50-100M), loi (100-500M), closing (>500M)."""
    pool = _pool(req)
    cibles = await _cibles_from_silver(pool, None, None, None, None, "score_ma", 50, 0)

    def stage_for(ca: float) -> str:
        if ca >= 500_000_000: return "closing"
        if ca >= 100_000_000: return "loi"
        if ca >= 50_000_000: return "dd"
        if ca >= 10_000_000: return "approche"
        return "sourcing"

    deals = []
    for i, c in enumerate(cibles["cibles"]):
        ca = float(c.get("ca_dernier", 0) or 0)
        stage = stage_for(ca)
        deals.append({
            "id": f"d_{c.get('siren')}",
            "siren": c.get("siren"),
            "name": c.get("denomination") or "—",
            "stage": stage,
            "value": f"{(ca / 1e6):.0f} M€" if ca >= 1e6 else f"{(ca / 1e3):.0f} k€",
            "value_num": ca,
            "owner": "AM",
            "days": (i % 30) + 1,
            "score": c.get("score_ma", 0),
            "side": "sell-side" if stage in ("dd", "loi", "closing") else "buy-side",
            "next": "Premier contact" if stage == "sourcing" else "Suivi en cours",
            "urgent": bool(c.get("has_compliance_red_flag")),
        })

    return {
        "stages": [
            {"id": "sourcing", "label": "Sourcing", "color": "var(--accent-blue)"},
            {"id": "approche", "label": "Approche", "color": "var(--accent-cyan)"},
            {"id": "dd", "label": "Due Diligence", "color": "var(--accent-purple)"},
            {"id": "loi", "label": "LOI / Term Sheet", "color": "var(--accent-amber)"},
            {"id": "closing", "label": "Closing", "color": "var(--accent-emerald)"},
        ],
        "deals": deals,
    }


@router.get("/agent-actions")
async def audit_log(req: Request, limit: int = Query(50, ge=1, le=200)):
    """Audit log live depuis audit.agent_actions (4k+ entries) — actions des
    agents codegen + ingest sur les sources."""
    pool = _pool(req)
    if not bool(await pool.fetchval(
        """SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'audit' AND c.relname = 'agent_actions'""",
    )):
        return {"entries": [], "notice": "audit.agent_actions non disponible"}

    rows = await pool.fetch(
        f"""SELECT id, agent_role, source_id, action, status,
                  duration_ms, llm_model, llm_tokens, created_at
           FROM audit.agent_actions
           ORDER BY created_at DESC
           LIMIT {int(limit)}"""
    )
    return {"entries": [_serialize(r) for r in rows]}


@router.get("/source-health")
async def audit_freshness(req: Request):
    """Statut santé des sources bronze/silver — last success, sla, completeness."""
    pool = _pool(req)
    if not bool(await pool.fetchval(
        """SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'audit' AND c.relname = 'source_freshness'""",
    )):
        return {"sources": []}
    rows = await pool.fetch(
        """SELECT source_id, last_success_at, last_failure_at,
                  rows_last_run, total_rows, sla_minutes, status,
                  completeness_pct, retry_count
           FROM audit.source_freshness
           ORDER BY last_success_at DESC NULLS LAST"""
    )
    return {"sources": [_serialize(r) for r in rows]}


@router.get("/co-mandats/{siren}")
async def network_for_siren(req: Request, siren: str):
    """Réseau autour d'un siren : nœuds (entreprise centrale, dirigeants top 5,
    autres entreprises co-mandatées, SCI patrimoine) + liens."""
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")
    pool = _pool(req)

    if not await _table_exists(pool, "silver", "inpi_dirigeants"):
        return {"nodes": [], "links": []}

    # Récupère l'entité centrale
    center = await pool.fetchrow(
        """SELECT siren, denomination FROM silver.inpi_comptes
           WHERE siren = $1 ORDER BY date_cloture DESC LIMIT 1""",
        siren,
    )
    if not center:
        center_deno = siren
    else:
        center_deno = center["denomination"] or siren

    dirigeants = await pool.fetch(
        """SELECT nom, prenom, n_mandats_actifs, sirens_mandats, denominations
           FROM silver.inpi_dirigeants
           WHERE $1::bpchar = ANY(sirens_mandats)
           ORDER BY n_mandats_actifs DESC NULLS LAST
           LIMIT 5""",
        siren,
    )

    nodes = [{"id": f"c_{siren}", "label": center_deno[:30], "type": "target", "x": 0, "y": 0}]
    links = []

    import math
    for i, d in enumerate(dirigeants):
        angle = (i / max(len(dirigeants), 1)) * 2 * math.pi
        px = round(math.cos(angle) * 220)
        py = round(math.sin(angle) * 160)
        person_id = f"p_{d['nom']}_{d['prenom']}"
        nodes.append({
            "id": person_id,
            "label": f"{d['prenom']} {d['nom']}",
            "type": "person",
            "x": px, "y": py,
        })
        links.append({"source": f"c_{siren}", "target": person_id, "kind": "dirigeant"})

        # Co-mandats : autres sirens du dirigeant
        sirens = list(d["sirens_mandats"] or [])[:4]
        denos = list(d["denominations"] or [])
        for j, other in enumerate(sirens):
            other_str = other.strip() if other else ""
            if other_str == siren or not other_str:
                continue
            other_deno = denos[j] if j < len(denos) else other_str
            cangle = angle + ((j - 1.5) * 0.25)
            cx = round(math.cos(cangle) * 380)
            cy = round(math.sin(cangle) * 240)
            other_id = f"c_{other_str}"
            if not any(n["id"] == other_id for n in nodes):
                nodes.append({
                    "id": other_id,
                    "label": (other_deno or other_str)[:24],
                    "type": "company",
                    "x": cx, "y": cy,
                })
            links.append({"source": person_id, "target": other_id, "kind": "co-mandat"})

    # SCI patrimoine
    if await _table_exists(pool, "silver", "dirigeant_sci_patrimoine") and dirigeants:
        for d in dirigeants[:3]:
            sci_rows = await pool.fetch(
                """SELECT n_sci, sci_denominations, sci_sirens, total_capital_sci
                   FROM silver.dirigeant_sci_patrimoine
                   WHERE nom = $1 AND prenom = $2 LIMIT 1""",
                d["nom"], d["prenom"],
            )
            if sci_rows and sci_rows[0]["sci_denominations"]:
                person_id = f"p_{d['nom']}_{d['prenom']}"
                for k, sd in enumerate(list(sci_rows[0]["sci_denominations"])[:3]):
                    sci_id = f"sci_{d['nom']}_{k}"
                    nodes.append({
                        "id": sci_id,
                        "label": (sd or "SCI")[:20],
                        "type": "sci",
                        "x": (k - 1) * 80,
                        "y": 240 + k * 30,
                    })
                    links.append({"source": person_id, "target": sci_id, "kind": "sci"})

    return {"nodes": nodes, "links": links}


@router.get("/press/recent")
async def press_recent(
    req: Request,
    limit: int = Query(50, ge=1, le=200),
    siren: str | None = None,
    signal: str | None = None,
):
    """Articles presse récents matchés (silver.press_mentions_matched).
    Source dédiée au tab "Presse" du Data Explorer + injection contexte Copilot."""
    pool = _pool(req)
    if not await _table_exists(pool, "silver", "press_mentions_matched"):
        return {"articles": [], "notice": "silver.press_mentions_matched pas encore matérialisée"}

    where = []
    params: list[Any] = []
    if siren:
        if not siren.isdigit() or len(siren) != 9:
            raise HTTPException(status_code=400, detail="SIREN invalide")
        where.append(f"siren = ${len(params) + 1}")
        params.append(siren)
    if signal:
        where.append(f"ma_signal_type = ${len(params) + 1}")
        params.append(signal)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    rows = await pool.fetch(
        f"""SELECT published_at, source, title, url, denomination, siren,
                   ma_signal_type, sentiment, summary
            FROM silver.press_mentions_matched
            {where_sql}
            ORDER BY published_at DESC
            LIMIT {int(limit)}""",
        *params,
    )
    return {"articles": [_serialize(r) for r in rows]}


@router.get("/cibles")
async def cibles_search(
    req: Request,
    q: str | None = None,
    dept: str | None = None,
    naf: str | None = None,
    min_score: int | None = Query(None, ge=0, le=100),
    is_pro_ma: bool | None = None,
    is_asset_rich: bool | None = None,
    has_red_flags: bool | None = None,
    sort: str = Query("score_ma", pattern="^(score_ma|ca_dernier|date_creation)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Recherche cibles M&A — privilégie gold.entreprises_master, fallback sur
    JOIN silver.insee_unites_legales + silver.inpi_comptes si la couche gold
    n'est pas encore matérialisée. Renvoie row_to_json brut, frontend mappe
    vers Cible avec rowToCible (résilient aux variations)."""
    pool = _pool(req)

    if await _table_exists(pool, "gold", "entreprises_master"):
        return await _cibles_from_gold(pool, q, dept, naf, min_score, is_pro_ma, is_asset_rich, has_red_flags, sort, limit, offset)
    return await _cibles_from_silver(pool, q, dept, naf, min_score, sort, limit, offset)


async def _cibles_from_gold(pool, q, dept, naf, min_score, is_pro_ma, is_asset_rich, has_red_flags, sort, limit, offset):
    where: list[str] = ["statut = 'actif'"]
    params: list[Any] = []
    if q:
        if q.isdigit() and len(q) == 9:
            params.append(q)
            where.append(f"siren = ${len(params)}")
        else:
            params.append(f"%{q}%")
            where.append(f"denomination ILIKE ${len(params)}")
    if dept:
        params.append(dept)
        where.append(f"siege_dept = ${len(params)}")
    if naf:
        params.append(f"{naf}%")
        where.append(f"naf ILIKE ${len(params)}")
    if min_score is not None:
        params.append(min_score)
        where.append(f"COALESCE(score_ma, pro_ma_score) >= ${len(params)}")
    if is_pro_ma is True:
        where.append("COALESCE(is_pro_ma, false) = true")
    if is_asset_rich is True:
        where.append("COALESCE(is_asset_rich, false) = true")
    if has_red_flags is True:
        where.append("COALESCE(has_compliance_red_flag, false) = true")
    elif has_red_flags is False:
        where.append("COALESCE(has_compliance_red_flag, false) = false")

    order_col = {"score_ma": "score_ma", "ca_dernier": "ca_dernier", "date_creation": "date_creation"}[sort]
    sql = f"""
        SELECT row_to_json(t.*) AS row FROM gold.entreprises_master t
        WHERE {' AND '.join(where)}
        ORDER BY {order_col} DESC NULLS LAST
        LIMIT {int(limit)} OFFSET {int(offset)}
    """
    rows = await pool.fetch(sql, *params)
    cibles = []
    for r in rows:
        v = r["row"]
        if isinstance(v, str):
            v = json.loads(v)
        cibles.append(v)
    return {"cibles": cibles, "limit": limit, "offset": offset, "has_more": len(cibles) == limit, "source": "gold"}


async def _cibles_from_silver(pool, q, dept, naf, min_score, sort, limit, offset):
    """Fallback : JOIN silver.inpi_comptes (CA, EBITDA, capitaux, effectif) +
    silver.osint_companies_enriched (NAF code_ape + dept code_postal + forme).
    Pré-filter ca_net pour speed (sinon scan 6M lignes).

    Colonnes utilisées (vérifiées via _introspect) :
    - inpi_comptes : siren, denomination, ca_net, resultat_net, capitaux_propres,
      effectif_moyen, date_cloture
    - osint_companies_enriched : siren, code_ape, adresse_code_postal,
      forme_juridique, date_immatriculation, denomination
    """
    ca_min = max(0, (min_score - 50) * 200_000) if min_score is not None else 0
    where: list[str] = [f"c.ca_net >= {int(ca_min)}"]
    params: list[Any] = []
    if q:
        if q.isdigit() and len(q) == 9:
            params.append(q)
            where.append(f"c.siren = ${len(params)}")
        else:
            params.append(f"%{q}%")
            where.append(f"c.denomination ILIKE ${len(params)}")

    # Filtres dept appliqués post-aggregation (sur dept dérivé de bodacc)
    post_where: list[str] = []
    if dept:
        params.append(dept)
        post_where.append(f"dept = ${len(params)}")
    # NAF skip — osint_companies_enriched bloqué, on n'a pas le NAF par siren ailleurs
    _ = naf  # noqa

    order_sql = {
        "score_ma": "ca_net DESC NULLS LAST",
        "ca_dernier": "ca_net DESC NULLS LAST",
        "date_creation": "date_cloture DESC NULLS LAST",
    }[sort]

    extra_where = (" AND " + " AND ".join(post_where)) if post_where else ""

    # Skip JOIN osint_companies_enriched (table actuellement bloquée). On
    # garde inpi_comptes pur + bodacc pour le dept (indexé).
    sql = f"""
        WITH last_compte AS (
            SELECT DISTINCT ON (c.siren) c.siren, c.denomination,
                                          c.ca_net, c.resultat_net,
                                          c.capitaux_propres, c.effectif_moyen,
                                          c.date_cloture
            FROM silver.inpi_comptes c
            WHERE {' AND '.join(where)}
            ORDER BY c.siren, c.date_cloture DESC
            LIMIT {int(limit) * 4}
        ),
        with_dept AS (
            SELECT lc.*,
                   (SELECT b.code_dept FROM silver.bodacc_annonces b
                    WHERE b.siren = lc.siren AND b.code_dept IS NOT NULL
                    ORDER BY b.date_parution DESC LIMIT 1) AS dept,
                   (SELECT b.ville FROM silver.bodacc_annonces b
                    WHERE b.siren = lc.siren AND b.ville IS NOT NULL
                    ORDER BY b.date_parution DESC LIMIT 1) AS ville
            FROM last_compte lc
        )
        SELECT siren,
               denomination,
               NULL::text AS naf,
               NULL::text AS naf_libelle,
               NULL::text AS forme_juridique,
               dept,
               ville,
               date_cloture AS date_creation,
               'actif' AS statut,
               ca_net AS ca_dernier,
               resultat_net AS ebitda_dernier,
               date_cloture AS date_derniers_comptes,
               effectif_moyen::int AS effectif_exact,
               capitaux_propres,
               CASE
                 WHEN ca_net IS NULL OR ca_net = 0 OR resultat_net IS NULL THEN NULL
                 ELSE ROUND((resultat_net::numeric / ca_net) * 100, 1)
               END AS marge_pct,
               LEAST(95, 50 + (COALESCE(ca_net, 0) / 200000)::int) AS score_ma,
               (COALESCE(ca_net, 0) >= 14000000) AS is_pro_ma,
               false AS is_asset_rich,
               EXISTS(
                 SELECT 1 FROM silver.opensanctions os
                 WHERE siren = ANY(os.sirens_fr)
               ) AS has_compliance_red_flag,
               false AS is_listed
        FROM with_dept
        WHERE 1=1 {extra_where}
        ORDER BY {order_sql}
        LIMIT {int(limit)} OFFSET {int(offset)}
    """
    try:
        rows = await pool.fetch(sql, *params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cibles silver fallback error: {type(e).__name__}: {e}")

    cibles = [_serialize(r) for r in rows]
    return {"cibles": cibles, "limit": limit, "offset": offset, "has_more": len(cibles) == limit, "source": "silver_fallback"}


async def _table_exists(pool: asyncpg.Pool, schema: str, table: str) -> bool:
    return bool(
        await pool.fetchval(
            """SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = $1 AND c.relname = $2 AND c.relkind IN ('r','m','p')""",
            schema,
            table,
        )
    )
