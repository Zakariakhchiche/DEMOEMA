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
from fastapi import APIRouter, HTTPException, Query, Request

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
async def introspect(req: Request):
    """Liste toutes les tables gold + silver présentes (schema, name, count approx).
    Utile pour aligner la whitelist avec la réalité du datalake déployé."""
    pool = _pool(req)
    rows = await pool.fetch(
        """
        SELECT n.nspname AS schema,
               c.relname AS table,
               c.reltuples::bigint AS rows_approx
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r','m','p')
          AND n.nspname IN ('gold','silver','bronze')
        ORDER BY n.nspname, c.relname
        """
    )
    return {"objects": [dict(r) for r in rows]}


@router.get("/tables")
async def list_tables(req: Request):
    """Liste les tables gold + silver presse + counts (head only). Query info_schema
    pour vérifier que la table existe physiquement avant de la renvoyer — évite
    de proposer des tables qui ne sont pas encore matérialisées."""
    pool = _pool(req)
    rows = await pool.fetch(
        """
        SELECT table_schema || '.' || table_name AS name
        FROM information_schema.tables
        WHERE table_schema IN ('gold', 'silver')
        """
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


@router.get("/{schema}/{table}")
async def query_table(
    req: Request,
    schema: str,
    table: str,
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


@router.get("/entreprise/{siren}")
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
        # Fallback silver — JOIN unites_legales + dernier exercice INPI
        fiche = await pool.fetchrow(
            """SELECT u.*,
                      c.chiffre_affaires AS ca_dernier,
                      c.resultat_net AS ebitda_dernier,
                      c.exercice AS date_derniers_comptes,
                      c.effectif_moyen AS effectif_exact
               FROM silver.insee_unites_legales u
               LEFT JOIN LATERAL (
                 SELECT chiffre_affaires, resultat_net, effectif_moyen, exercice
                 FROM silver.inpi_comptes WHERE siren = u.siren
                 ORDER BY exercice DESC LIMIT 1
               ) c ON true
               WHERE u.siren = $1""",
            siren,
        )
    if not fiche:
        raise HTTPException(status_code=404, detail=f"SIREN {siren} introuvable")

    if await _table_exists(pool, "gold", "dirigeants_master"):
        dirigeants = await pool.fetch(
            """SELECT person_id, nom, prenom, qualite, age, n_mandats, score_decideur
               FROM gold.dirigeants_master
               WHERE siren_companies @> ARRAY[$1]::text[] OR siren = $1
               ORDER BY score_decideur DESC NULLS LAST
               LIMIT 5""",
            siren,
        )
    elif await _table_exists(pool, "silver", "inpi_dirigeants"):
        dirigeants = await pool.fetch(
            """SELECT nom, prenom, qualite, date_naissance, nationalite
               FROM silver.inpi_dirigeants
               WHERE siren = $1
               ORDER BY date_naissance NULLS LAST
               LIMIT 10""",
            siren,
        )
    else:
        dirigeants = []

    signaux = []
    if await _table_exists(pool, "silver", "bodacc_annonces"):
        signaux = await pool.fetch(
            """SELECT dateparution AS event_date, type_annonce AS signal_type,
                      tribunal AS source, denomination
               FROM silver.bodacc_annonces
               WHERE siren = $1
               ORDER BY dateparution DESC
               LIMIT 10""",
            siren,
        )

    presse = await pool.fetch(
        """SELECT published_at, source, title, url, ma_signal_type
           FROM silver.press_mentions_matched
           WHERE siren = $1
           ORDER BY published_at DESC
           LIMIT 5""",
        siren,
    ) if await _table_exists(pool, "silver", "press_mentions_matched") else []

    return {
        "fiche": _serialize(fiche),
        "dirigeants": [_serialize(d) for d in dirigeants],
        "signaux": [_serialize(s) for s in signaux],
        "presse": [_serialize(p) for p in presse],
    }


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
    """Fallback : JOIN silver.insee_unites_legales (29M) + silver.inpi_comptes (6M)
    pour synthétiser une vue cible M&A en attendant que gold.entreprises_master
    soit produit. Score M&A approx = 50 + (CA / 200K€), capé à 95."""
    where: list[str] = ["u.etat_administratif = 'A'"]
    params: list[Any] = []
    if q:
        if q.isdigit() and len(q) == 9:
            params.append(q)
            where.append(f"u.siren = ${len(params)}")
        else:
            params.append(f"%{q}%")
            where.append(f"u.denomination ILIKE ${len(params)}")
    if dept:
        # dépt encodé sur les 2-3 premiers chars du code commune INSEE — on fait
        # un best-effort via insee_etablissements (siège). Coûteux donc on
        # squeeze sauf si dept fourni.
        params.append(dept + "%")
        where.append(
            f"u.siren IN (SELECT DISTINCT siren FROM silver.insee_etablissements "
            f"WHERE etablissement_siege = true AND code_commune ILIKE ${len(params)} LIMIT 5000)"
        )
    if naf:
        params.append(f"{naf}%")
        where.append(f"u.naf ILIKE ${len(params)}")
    if min_score is not None:
        # On ne peut pas filtrer sur le score calculé sans subquery — on filtre
        # sur le CA approximativement.
        approx_ca = max(0, (min_score - 50) * 200_000)
        params.append(approx_ca)
        where.append(f"COALESCE(c.chiffre_affaires, 0) >= ${len(params)}")

    order_sql = {
        "score_ma": "COALESCE(c.chiffre_affaires, 0) DESC NULLS LAST",
        "ca_dernier": "c.chiffre_affaires DESC NULLS LAST",
        "date_creation": "u.date_creation DESC NULLS LAST",
    }[sort]

    sql = f"""
        SELECT u.siren,
               u.denomination,
               u.naf,
               u.naf,
               '' AS naf_libelle,
               u.tranche_effectif_unite_legale AS effectif_tranche,
               u.date_creation,
               u.etat_administratif,
               c.chiffre_affaires AS ca_dernier,
               c.resultat_net AS ebitda_dernier,
               c.exercice AS date_derniers_comptes,
               c.effectif_moyen AS effectif_exact,
               LEAST(95, 50 + (COALESCE(c.chiffre_affaires, 0) / 200000)::int) AS score_ma,
               (COALESCE(c.chiffre_affaires, 0) >= 14000000) AS is_pro_ma,
               false AS is_asset_rich,
               false AS has_compliance_red_flag,
               false AS is_listed,
               'actif' AS statut
        FROM silver.insee_unites_legales u
        LEFT JOIN LATERAL (
            SELECT chiffre_affaires, resultat_net, effectif_moyen, exercice
            FROM silver.inpi_comptes
            WHERE siren = u.siren
            ORDER BY exercice DESC
            LIMIT 1
        ) c ON true
        WHERE {' AND '.join(where)}
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
            """SELECT 1 FROM information_schema.tables
               WHERE table_schema = $1 AND table_name = $2""",
            schema,
            table,
        )
    )
