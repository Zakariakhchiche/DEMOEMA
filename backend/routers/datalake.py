"""Routes datalake — expose les tables gold + silver presse au frontend.

Tous les endpoints sont READ-ONLY (le pool peut tourner en datalake_ro). Whitelist
stricte du nom de table via `GOLD_TABLES_WHITELIST` pour empêcher toute SQL
injection sur le segment `{schema}.{table}`. Les valeurs (filtre, search) sont
toujours bindées en paramètres asyncpg ($1, $2…).
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import asyncpg
from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

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


async def _safe(coro, timeout_s: float = 4.0, default=None):
    """Helper module-level : exécute une coroutine avec timeout, retourne default
    si échec/timeout. Pour endpoints lents où une table peut être bloquante."""
    import asyncio as _asyncio
    try:
        return await _asyncio.wait_for(coro, timeout=timeout_s)
    except (_asyncio.TimeoutError, Exception) as e:
        print(f"[_safe] {type(e).__name__}: {str(e)[:100]}")
        return default


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
               -- Bug Y rapport QA : reltuples = -1 quand pas encore ANALYZE.
               -- On exposait des -1 trompeurs dans l'Explorer. Désormais on
               -- normalise à 0 (tableau vide ou pas analysé) — l'opérateur
               -- doit lancer ANALYZE pour avoir le count statistique.
               GREATEST(0, c.reltuples::bigint) AS rows_approx
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
        # Count approx via pg_class (instant, vs COUNT(*) sur 30M rows = 8s).
        # Audit QA 2026-05-01 : pg_class.reltuples = -1 quand jamais ANALYZE
        # (ex hatvp_lobbying). On normalise à 0 — Explorer exposait du -1 trompeur.
        schema, tbl = name.split(".", 1)
        try:
            n = await pool.fetchval(
                """SELECT GREATEST(0, reltuples::bigint) FROM pg_class c
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


# Bug v6/1.4 — fiche/{siren} p95 = 5s (multiple JOINs gold + silver fallback +
# Google News RSS + opensanctions). Cache in-memory LRU TTL=5min couvre les
# accès répétés (l'UI rappelle /fiche à chaque tab switch — gain massif).
# Pas de Redis : 1 seul process backend, mémoire suffit. Single-flight via
# asyncio.Lock pour éviter la stampede sur cache miss simultanés.
import time as _time

_FICHE_CACHE: dict[str, tuple[float, dict]] = {}
_FICHE_LOCKS: dict[str, asyncio.Lock] = {}
_FICHE_TTL_S = 300.0  # 5 min — fiches changent rarement (refresh quotidien gold)
_FICHE_MAX_ENTRIES = 500  # garde-fou mémoire (~10 KB/entrée → ~5 MB max)


def _fiche_cache_get(siren: str) -> dict | None:
    item = _FICHE_CACHE.get(siren)
    if not item:
        return None
    ts, payload = item
    if _time.time() - ts > _FICHE_TTL_S:
        _FICHE_CACHE.pop(siren, None)
        return None
    return payload


def _fiche_cache_set(siren: str, payload: dict) -> None:
    if len(_FICHE_CACHE) >= _FICHE_MAX_ENTRIES:
        # Évince l'entrée la plus ancienne (FIFO simple, suffisant pour ce volume)
        oldest = min(_FICHE_CACHE.items(), key=lambda kv: kv[1][0])[0]
        _FICHE_CACHE.pop(oldest, None)
    _FICHE_CACHE[siren] = (_time.time(), payload)


# Cache générique pour /cibles, /graph et /scoring (bug v6/1.4 perf p95>3s).
# Clé = string custom, valeur = (timestamp, payload). TTL 60s pour /cibles
# (filtres dynamiques, on ne veut pas servir une liste périmée trop longtemps),
# 300s pour /graph (couplé à un siren, change rarement).
_GENERIC_CACHE: dict[str, tuple[float, Any]] = {}


def _gen_cache_get(key: str, ttl_s: float) -> Any | None:
    item = _GENERIC_CACHE.get(key)
    if not item:
        return None
    ts, payload = item
    if _time.time() - ts > ttl_s:
        _GENERIC_CACHE.pop(key, None)
        return None
    return payload


def _gen_cache_set(key: str, payload: Any) -> None:
    if len(_GENERIC_CACHE) >= 1000:
        oldest = min(_GENERIC_CACHE.items(), key=lambda kv: kv[1][0])[0]
        _GENERIC_CACHE.pop(oldest, None)
    _GENERIC_CACHE[key] = (_time.time(), payload)


@router.get("/fiche/{siren}")
async def fiche_entreprise(req: Request, siren: str):
    """Fiche complète — gold.entreprises_master si dispo, fallback sur
    silver.insee_unites_legales + silver.inpi_comptes + silver.inpi_dirigeants.

    Cache LRU TTL 5 min sur (siren) — bug v6/1.4 perf.
    """
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")

    cached = _fiche_cache_get(siren)
    if cached is not None:
        return cached

    # Single-flight : si 2 requêtes pour le même siren arrivent en parallèle
    # sur cache miss, on n'exécute qu'une seule fois la fiche full.
    lock = _FICHE_LOCKS.setdefault(siren, asyncio.Lock())
    async with lock:
        cached = _fiche_cache_get(siren)
        if cached is not None:
            return cached
        result = await _fiche_entreprise_uncached(req, siren)
        _fiche_cache_set(siren, result)
    return result


async def _fiche_entreprise_uncached(req: Request, siren: str):
    pool = _pool(req)

    fiche = None
    gouv = None
    if await _table_exists(pool, "gold", "entreprises_master"):
        fiche_row = await pool.fetchrow(
            "SELECT * FROM gold.entreprises_master WHERE siren = $1", siren
        )
        if fiche_row:
            # Schema gold v3 PRO : ca_latest / effectif_moyen_latest / resultat_net_latest /
            # insee_tranche_effectifs etc. Le frontend lit les noms LEGACY (ca_dernier,
            # effectif_exact, ebitda_dernier, tranche_effectifs, n_bodacc). Sans alias,
            # les cards CA/EBITDA/Effectif s'affichent vides sur les sirens en gold.
            # Voir _cibles_from_gold qui fait la même chose en sortie.
            fiche = dict(fiche_row)
            fiche.setdefault("ca_dernier", fiche.get("ca_latest"))
            fiche.setdefault("ebitda_dernier", fiche.get("resultat_net_latest"))
            fiche.setdefault("resultat_net", fiche.get("resultat_net_latest"))
            fiche.setdefault("effectif_exact", fiche.get("effectif_moyen_latest") or fiche.get("effectif_salarie"))
            fiche.setdefault("effectif_moyen", fiche.get("effectif_moyen_latest"))
            fiche.setdefault("capitaux_propres", fiche.get("capitaux_propres_latest"))
            fiche.setdefault("tranche_effectifs", fiche.get("insee_tranche_effectifs"))
            fiche.setdefault("forme_juridique", fiche.get("insee_categorie_juridique"))
            fiche.setdefault("naf", fiche.get("code_ape"))
            fiche.setdefault("dept", fiche.get("adresse_dept"))
            fiche.setdefault("ville", fiche.get("adresse_commune"))
            fiche.setdefault("date_creation", fiche.get("date_immatriculation"))
            fiche.setdefault("annee_creation", (
                int(str(fiche["date_immatriculation"])[:4])
                if fiche.get("date_immatriculation")
                else None
            ))
            fiche.setdefault("statut", "actif" if fiche.get("insee_etat_administratif") != "F" else "cesse")
            fiche.setdefault("etat_administratif", fiche.get("insee_etat_administratif"))
            # marge_pct calculé pour cohérence avec le silver path
            ca_v = fiche.get("ca_latest")
            rn_v = fiche.get("resultat_net_latest")
            if ca_v and rn_v is not None:
                try:
                    fiche["marge_pct"] = round((float(rn_v) / float(ca_v)) * 100, 1)
                except (TypeError, ZeroDivisionError):
                    fiche["marge_pct"] = None

            # CA history (5 derniers exercices) — manque dans gold, requis par le
            # graphe d'évolution finance côté frontend.
            ca_hist = await _safe(pool.fetch(
                """SELECT date_cloture, ca_net::float8 AS ca
                   FROM (SELECT DISTINCT ON (date_cloture) date_cloture, ca_net
                         FROM silver.inpi_comptes
                         WHERE siren = $1 ORDER BY date_cloture DESC LIMIT 5) h
                   WHERE ca_net IS NOT NULL ORDER BY date_cloture""",
                siren,
            ), default=[])
            fiche["ca_history"] = [r["ca"] for r in (ca_hist or [])]
            fiche["exercices"] = [r["date_cloture"].isoformat() for r in (ca_hist or [])]

            # Counts agrégés (n_dirigeants/n_bodacc/n_sanctions) — gold a
            # n_bodacc_annonces_24m mais pas le total ni les dirigeants/sanctions.
            # Sans ces 3 compteurs, les cards "DIRIGEANTS / BODACC / RED FLAGS"
            # de l'overview affichent 0 alors que les tabs pleins. Cf. DUFOUR.
            # Bug v5/3.7 — fiches grands groupes (Renault, EDF, L'Oréal…)
            # affichaient 1/11 champs car les holdings cotées ne déposent pas
            # leur bilan à l'INPI (URD AMF à la place). Pour les champs simples
            # qui peuvent venir de l'API gouv recherche-entreprises (NAF lib,
            # tranche effectifs, ville détaillée), on enrichit le gold path
            # quand ils sont NULL en complément.
            needs_gouv_enrich = (
                not fiche.get("insee_tranche_effectifs")
                or not fiche.get("adresse_commune")
                or not fiche.get("nom_commercial")
            )
            if needs_gouv_enrich:
                try:
                    import httpx as _httpx_g
                    async with _httpx_g.AsyncClient(timeout=4.0) as client_g:
                        resp_g = await client_g.get(
                            f"https://recherche-entreprises.api.gouv.fr/search?q={siren}&per_page=1"
                        )
                        if resp_g.status_code == 200:
                            data_g = resp_g.json()
                            if data_g.get("results"):
                                r_g = data_g["results"][0]
                                siege_g = r_g.get("siege") or {}
                                # setdefault n'écrase pas une clé existant à NULL : on doit
                                # faire un OR explicit pour les champs gold pré-existants.
                                def _fill(key, val):
                                    if val and not fiche.get(key):
                                        fiche[key] = val
                                _fill("naf_libelle", siege_g.get("libelle_activite_principale") or r_g.get("libelle_activite_principale"))
                                _fill("tranche_effectifs", r_g.get("tranche_effectif_salarie") or siege_g.get("tranche_effectif_salarie"))
                                _fill("nom_commercial", r_g.get("nom_complet"))
                                _fill("ville", siege_g.get("libelle_commune"))
                                _fill("adresse", siege_g.get("adresse"))
                                _fill("n_etablissements", r_g.get("nombre_etablissements"))
                                _fill("n_etablissements_ouverts", r_g.get("nombre_etablissements_ouverts"))
                except Exception as _e:
                    print(f"[fiche gold] gouv enrich failed: {type(_e).__name__}")

            fiche["n_dirigeants"] = await _safe(pool.fetchval(
                "SELECT COUNT(*)::int FROM silver.inpi_dirigeants WHERE $1::char(9) = ANY(sirens_mandats)",
                siren,
            ), default=0) or fiche.get("n_dirigeants") or 0
            fiche["n_bodacc"] = await _safe(pool.fetchval(
                "SELECT COUNT(*)::int FROM silver.bodacc_annonces WHERE siren = $1",
                siren,
            ), default=0) or 0
            fiche["n_sanctions"] = await _safe(pool.fetchval(
                "SELECT COUNT(*)::int FROM silver.opensanctions WHERE $1 = ANY(sirens_fr)",
                siren,
            ), default=0) or 0
    if not fiche:
        # Multi-query approach : chaque source séparée avec timeout court.
        # Si une table est lente/locked, on remplit avec NULL au lieu de tout
        # bloquer. Plus robuste qu'un mega-CTE.
        # Note: _safe est défini au module-level (ligne 37). Pas de re-def
        # locale (sinon UnboundLocalError quand `fiche` truthy => Python
        # marque _safe comme local mais la def dans le if n'est jamais
        # exécutée, et hatvp ligne 865 plante).

        # 1. INPI comptes — agrégats sur tous les exercices pour ne pas perdre
        # les valeurs présentes dans des exercices antérieurs (effectif/capital
        # parfois null sur le dernier mais présents sur N-1 ou N-2).
        compte = await pool.fetchrow(
            """WITH all_comptes AS (
                  SELECT denomination, ca_net, resultat_net,
                         capital_social, capitaux_propres,
                         effectif_moyen::int AS effectif_exact,
                         date_cloture, total_actif, emprunts_dettes
                  FROM silver.inpi_comptes
                  WHERE siren = $1
                  ORDER BY date_cloture DESC
               ),
               latest AS (SELECT * FROM all_comptes LIMIT 1),
               latest_non_null AS (
                  SELECT
                    (SELECT capital_social FROM all_comptes WHERE capital_social IS NOT NULL LIMIT 1) AS capital_social,
                    (SELECT capitaux_propres FROM all_comptes WHERE capitaux_propres IS NOT NULL LIMIT 1) AS capitaux_propres,
                    (SELECT effectif_exact FROM all_comptes WHERE effectif_exact IS NOT NULL LIMIT 1) AS effectif_exact,
                    (SELECT total_actif FROM all_comptes WHERE total_actif IS NOT NULL LIMIT 1) AS total_actif,
                    (SELECT emprunts_dettes FROM all_comptes WHERE emprunts_dettes IS NOT NULL LIMIT 1) AS emprunts_dettes
               )
               SELECT $1 AS siren,
                      latest.denomination, latest.ca_net, latest.resultat_net,
                      COALESCE(latest.capital_social, latest_non_null.capital_social) AS capital_social,
                      COALESCE(latest.capitaux_propres, latest_non_null.capitaux_propres) AS capitaux_propres,
                      COALESCE(latest.effectif_exact, latest_non_null.effectif_exact) AS effectif_exact,
                      COALESCE(latest.total_actif, latest_non_null.total_actif) AS total_actif,
                      COALESCE(latest.emprunts_dettes, latest_non_null.emprunts_dettes) AS emprunts_dettes,
                      latest.date_cloture
               FROM latest, latest_non_null""",
            siren,
        )
        # Bug v5/3.7 — siren absent de silver.inpi_comptes (typique des
        # holdings cotés ou TPE non-soumises à dépôt) renvoyait 404. Au lieu
        # de bloquer, on fabrique un compte "vide" et on enrichit côté gouv
        # API + INSEE plus bas. Le frontend gère gracefully ca_net=NULL.
        if not compte:
            compte = {
                "siren": siren,
                "denomination": None, "ca_net": None, "resultat_net": None,
                "capital_social": None, "capitaux_propres": None,
                "effectif_exact": None, "total_actif": None,
                "emprunts_dettes": None, "date_cloture": None,
            }

        # 2. CA history (5 derniers exercices)
        history = await _safe(pool.fetch(
            """SELECT date_cloture, ca_net::float8 AS ca
               FROM (SELECT DISTINCT ON (date_cloture) date_cloture, ca_net
                     FROM silver.inpi_comptes
                     WHERE siren = $1 ORDER BY date_cloture DESC LIMIT 5) h
               WHERE ca_net IS NOT NULL ORDER BY date_cloture""",
            siren,
        ), default=[])

        # 3. Localisation bodacc (rapide, indexé siren)
        loc = await _safe(pool.fetchrow(
            """SELECT code_dept AS dept, ville, region
               FROM silver.bodacc_annonces
               WHERE siren = $1 AND code_dept IS NOT NULL
               ORDER BY date_parution DESC LIMIT 1""",
            siren,
        ))

        # 4. OSINT enrichment (NAF, forme, capital, domain, linkedin)
        osint = await _safe(pool.fetchrow(
            """SELECT code_ape AS naf, forme_juridique,
                      montant_capital AS capital_social,
                      adresse_code_postal,
                      EXTRACT(YEAR FROM date_immatriculation)::int AS annee_creation,
                      primary_domain, has_linkedin_page, has_github_org,
                      linkedin_employees, digital_presence_score, tech_stack
               FROM silver.osint_companies_enriched WHERE siren = $1""",
            siren,
        ), timeout_s=6.0)

        # 5. INSEE unites_legales (sigle, secteur)
        insee = await _safe(pool.fetchrow(
            """SELECT denomination_unite, sigle, code_ape, categorie_juridique,
                      categorie_entreprise, tranche_effectifs, date_creation,
                      date_derniere_maj, etat_administratif
               FROM silver.insee_unites_legales WHERE siren = $1""",
            siren,
        ))

        # 6. Counts agrégés (séparés pour timeout indépendant)
        n_dirigeants = await _safe(pool.fetchval(
            "SELECT COUNT(*)::int FROM silver.inpi_dirigeants WHERE $1::char(9) = ANY(sirens_mandats)",
            siren,
        ), default=0)
        n_bodacc = await _safe(pool.fetchval(
            "SELECT COUNT(*)::int FROM silver.bodacc_annonces WHERE siren = $1",
            siren,
        ), default=0)
        n_sanctions = await _safe(pool.fetchval(
            "SELECT COUNT(*)::int FROM silver.opensanctions WHERE $1 = ANY(sirens_fr)",
            siren,
        ), default=0)

        # Agrégation finale
        ca_history = [r["ca"] for r in (history or [])]
        exercices = [r["date_cloture"].isoformat() for r in (history or [])]

        ca_net = float(compte["ca_net"]) if compte["ca_net"] is not None else None
        resultat = float(compte["resultat_net"]) if compte["resultat_net"] is not None else None
        marge_pct = round((resultat / ca_net) * 100, 1) if ca_net and ca_net > 0 and resultat is not None else None

        # 7. Fallback live API gouv pour siren ghost-row (NAF, dept, ville,
        # forme, etc. quand silver est vide). API gratuite, < 200ms.
        if not osint and (not insee or not insee["code_ape"]):
            import httpx as _httpx
            try:
                async with _httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(
                        f"https://recherche-entreprises.api.gouv.fr/search?q={siren}&per_page=1"
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("results"):
                            r = data["results"][0]
                            siege = r.get("siege") or {}
                            mp = r.get("matching_etablissements") or []
                            adresse = siege.get("adresse")
                            commune = siege.get("libelle_commune") or siege.get("commune") or ""
                            # NAF / catégorie : depuis siège (struct API gouv FR)
                            gouv = {
                                "naf": siege.get("activite_principale") or r.get("activite_principale"),
                                "naf_libelle": siege.get("libelle_activite_principale") or r.get("libelle_activite_principale"),
                                "forme_juridique": r.get("nature_juridique") or r.get("nature_juridique_libelle"),
                                "categorie_entreprise": r.get("categorie_entreprise"),
                                "date_creation": r.get("date_creation") or siege.get("date_creation"),
                                "denomination": r.get("nom_complet") or r.get("nom_raison_sociale"),
                                "sigle": r.get("sigle"),
                                "tranche_effectifs": r.get("tranche_effectif_salarie") or siege.get("tranche_effectif_salarie"),
                                "ville": commune,
                                "code_postal": siege.get("code_postal"),
                                "dept": siege.get("departement") or (siege.get("code_postal") or "")[:2],
                                "region": siege.get("libelle_region") or siege.get("region"),
                                "etat_administratif": r.get("etat_administratif"),
                                "adresse": adresse,
                                "n_etablissements": r.get("nombre_etablissements"),
                                "n_etablissements_ouverts": r.get("nombre_etablissements_ouverts"),
                                "date_fermeture": siege.get("date_fermeture"),
                                "dirigeants": r.get("dirigeants") or [],
                                "matching_etablissements": [
                                    {"siret": e.get("siret"), "ville": e.get("libelle_commune"), "code_postal": e.get("code_postal")}
                                    for e in mp[:5]
                                ],
                            }
            except Exception as e:
                print(f"[fiche] gouv API fallback failed: {type(e).__name__}: {str(e)[:80]}")

        fiche = {
            "siren": compte["siren"],
            "denomination": compte["denomination"] or (insee["denomination_unite"] if insee else None) or (gouv["denomination"] if gouv else None),
            "sigle": (insee["sigle"] if insee else None) or (gouv["sigle"] if gouv else None),
            "ca_dernier": compte["ca_net"],
            "ebitda_dernier": compte["resultat_net"],
            "capitaux_propres": compte["capitaux_propres"],
            "effectif_exact": compte["effectif_exact"],
            "tranche_effectifs": (insee["tranche_effectifs"] if insee else None) or (gouv["tranche_effectifs"] if gouv else None),
            "date_derniers_comptes": compte["date_cloture"].isoformat() if compte["date_cloture"] else None,
            "marge_pct": marge_pct,
            "naf": (osint["naf"] if osint else None) or (insee["code_ape"] if insee else None) or (gouv["naf"] if gouv else None),
            "naf_libelle": (gouv["naf_libelle"] if gouv else None),
            "forme_juridique": (osint["forme_juridique"] if osint else None) or (insee["categorie_juridique"] if insee else None) or (gouv["forme_juridique"] if gouv else None),
            # Capital social : INPI comptes (toutes années) > osint
            "capital_social": compte["capital_social"] or (osint["capital_social"] if osint else None),
            "total_actif": compte["total_actif"],
            "emprunts_dettes": compte["emprunts_dettes"],
            "adresse_code_postal": (osint["adresse_code_postal"] if osint else None) or (gouv["code_postal"] if gouv else None),
            "annee_creation": (osint["annee_creation"] if osint and osint["annee_creation"] else None) or (
                int(str(insee["date_creation"])[:4]) if insee and insee["date_creation"] else (
                    int(str(gouv["date_creation"])[:4]) if gouv and gouv["date_creation"] else None
                )
            ),
            # Bug v5/3.14 — ancienneté manquait sur le silver path. Calculé
            # symétriquement au gold path pour cohérence des fiches.
            "age_entreprise": (
                lambda y: (2026 - y) if y else None
            )(
                (osint["annee_creation"] if osint and osint["annee_creation"] else None)
                or (int(str(insee["date_creation"])[:4]) if insee and insee["date_creation"] else None)
                or (int(str(gouv["date_creation"])[:4]) if gouv and gouv["date_creation"] else None)
            ),
            "primary_domain": osint["primary_domain"] if osint else None,
            "has_linkedin_page": osint["has_linkedin_page"] if osint else None,
            "has_github_org": osint["has_github_org"] if osint else None,
            "linkedin_employees": osint["linkedin_employees"] if osint else None,
            "digital_presence_score": osint["digital_presence_score"] if osint else None,
            "categorie_entreprise": (insee["categorie_entreprise"] if insee else None) or (gouv["categorie_entreprise"] if gouv else None),
            "dept": (osint["adresse_code_postal"][:2] if osint and osint["adresse_code_postal"] else None) or (loc["dept"] if loc else None) or (gouv["dept"] if gouv else None),
            "ville": (loc["ville"] if loc else None) or (gouv["ville"] if gouv else None),
            "region": (loc["region"] if loc else None) or (gouv["region"] if gouv else None),
            "etat_administratif": gouv["etat_administratif"] if gouv else (insee["etat_administratif"] if insee else None),
            "adresse": gouv["adresse"] if gouv else None,
            "n_etablissements": gouv["n_etablissements"] if gouv else None,
            "n_etablissements_ouverts": gouv["n_etablissements_ouverts"] if gouv else None,
            "date_fermeture": gouv["date_fermeture"] if gouv else None,
            "ca_history": ca_history,
            "exercices": exercices,
            "n_dirigeants": n_dirigeants or 0,
            "n_bodacc": n_bodacc or 0,
            "n_sanctions": n_sanctions or 0,
            "statut": (
                "cesse" if (gouv and gouv.get("date_fermeture")) or (gouv and gouv.get("etat_administratif") == "C")
                else "actif"
            ),
        }
    # Si fiche est un dict (multi-query path) on skip le check ci-dessous.
    if not fiche:
        raise HTTPException(status_code=404, detail=f"SIREN {siren} introuvable")
    # Bug v5/3.7 — guard final : si tous les fallbacks (silver + gouv) ont
    # échoué, denomination reste NULL → fiche inutilisable. On ne renvoie
    # pas une fiche vide qui simulerait un succès, on renvoie 404.
    if isinstance(fiche, dict) and not fiche.get("denomination"):
        raise HTTPException(status_code=404, detail=f"SIREN {siren} introuvable (silver + gouv vides)")

    # Dirigeants détaillés — top 10 par mandats actifs, joint avec patrimoine SCI.
    # On essaie d'abord en silver (8M dirigeants), fallback sur l'API gouv si vide.
    dirigeants_silver = await pool.fetch(
        """WITH dirig_raw AS (
              -- Identité = (nom, prenom, date_naissance). Si silver a plusieurs
              -- rows pour la même personne (ex : 1 par siren_main), on garde la
              -- row avec le plus grand n_mandats_actifs.
              SELECT DISTINCT ON (
                       UPPER(unaccent(nom)),
                       UPPER(unaccent(prenom)),
                       COALESCE(date_naissance, '')
                     )
                     nom, prenom, date_naissance, age_2026 AS age,
                     n_mandats_actifs, n_mandats_total,
                     sirens_mandats, denominations, formes_juridiques,
                     roles, is_multi_mandat,
                     first_mandat_date, last_mandat_date
              FROM silver.inpi_dirigeants
              WHERE $1::char(9) = ANY(sirens_mandats)
              ORDER BY UPPER(unaccent(nom)),
                       UPPER(unaccent(prenom)),
                       COALESCE(date_naissance, ''),
                       n_mandats_actifs DESC NULLS LAST
           ),
           dirig AS (
              SELECT * FROM dirig_raw
              ORDER BY n_mandats_actifs DESC NULLS LAST
              LIMIT 10
           ),
           -- Aggrège SCI patrimoine par (nom, prenom) — la table a plusieurs rows
           -- par dirigeant (1 row par siren_main probable), il faut consolider
           -- pour éviter les duplicate dirigeants côté API.
           sci_agg AS (
              SELECT nom, prenom, date_naissance,
                     SUM(n_sci) AS n_sci,
                     SUM(total_capital_sci) AS total_capital_sci,
                     ARRAY(SELECT DISTINCT unnest(array_agg(sci_denominations))) AS sci_denominations,
                     ARRAY(SELECT DISTINCT unnest(array_agg(sci_sirens))) AS sci_sirens,
                     ARRAY(SELECT DISTINCT unnest(array_agg(sci_code_postaux))) AS sci_code_postaux,
                     MIN(first_sci_date) AS first_sci_date
              FROM silver.dirigeant_sci_patrimoine
              WHERE (nom, prenom) IN (SELECT nom, prenom FROM dirig)
              GROUP BY nom, prenom, date_naissance
           ),
           -- Valeur réelle du patrimoine SCI : agrégation des derniers comptes
           -- INPI (total_actif = bilan, immo_corporelles = biens immo, capitaux_propres
           -- = situation nette). C'est cette VALEUR qui est intéressante pour
           -- estimer la richesse réelle du dirigeant, pas le capital social statutaire.
           sci_patrimoine_value AS (
              SELECT sa.nom, sa.prenom, sa.date_naissance,
                     SUM(c.total_actif) AS sci_total_actif,
                     SUM(c.immo_corporelles) AS sci_immo_corporelles,
                     SUM(c.capitaux_propres) AS sci_capitaux_propres,
                     SUM(c.ca_net) AS sci_ca_net,
                     COUNT(DISTINCT c.siren) AS sci_n_with_comptes
              FROM sci_agg sa
              CROSS JOIN LATERAL unnest(sa.sci_sirens) AS s(siren)
              -- Dernier exercice par siren SCI uniquement (DISTINCT ON)
              JOIN LATERAL (
                  SELECT total_actif, immo_corporelles, capitaux_propres, ca_net, siren
                  FROM silver.inpi_comptes ic
                  WHERE ic.siren = s.siren
                  ORDER BY ic.date_cloture DESC NULLS LAST
                  LIMIT 1
              ) c ON true
              GROUP BY sa.nom, sa.prenom, sa.date_naissance
           ),
           -- Sanctions matching strict : nom + prenom dans le caption opensanctions
           sanc_agg AS (
              SELECT d.nom, d.prenom,
                     bool_or(true) AS is_sanctioned,
                     array_agg(DISTINCT s.entity_id) FILTER (WHERE s.entity_id IS NOT NULL) AS sanction_ids,
                     array_agg(DISTINCT s.caption) FILTER (WHERE s.caption IS NOT NULL) AS sanction_captions,
                     ARRAY(SELECT DISTINCT unnest(array_agg(s.topics))) AS sanction_topics,
                     ARRAY(SELECT DISTINCT unnest(array_agg(s.countries))) AS sanction_countries,
                     ARRAY(SELECT DISTINCT unnest(array_agg(s.sanctions_programs))) AS sanction_programs
              FROM dirig d
              JOIN silver.opensanctions s
                ON s.schema = 'Person'
               AND LOWER(s.name) ILIKE '%' || LOWER(d.prenom) || '%'
               AND LOWER(s.name) ILIKE '%' || LOWER(d.nom) || '%'
               AND LENGTH(d.prenom) > 2 AND LENGTH(d.nom) > 2
              GROUP BY d.nom, d.prenom
           )
           SELECT d.*,
                  -- Patrimoine SCI consolidé
                  sci.n_sci,
                  sci.total_capital_sci,
                  sci.sci_denominations,
                  sci.sci_sirens,
                  sci.sci_code_postaux,
                  sci.first_sci_date,
                  -- Valeur réelle du patrimoine SCI (bilan agrégé dernier exercice)
                  spv.sci_total_actif,
                  spv.sci_immo_corporelles,
                  spv.sci_capitaux_propres,
                  spv.sci_ca_net,
                  spv.sci_n_with_comptes,
                  -- OSINT : présence sociale + entreprise principale (JOIN sur prenoms[])
                  os.person_uid,
                  os.has_linkedin, os.has_github, os.has_any_social,
                  os.n_linkedin, os.n_github, os.n_twitter,
                  os.n_other_sites, os.n_total_social,
                  os.denomination_main_company AS osint_main_deno,
                  os.forme_juridique_main AS osint_main_forme,
                  os.capital_main AS osint_main_capital,
                  os.date_immat_main AS osint_main_immat,
                  os.n_mandats_inpi AS osint_n_mandats,
                  os.last_scanned_at AS osint_scanned_at,
                  -- Compliance : sanction détail
                  COALESCE(sa.is_sanctioned, false) AS is_sanctioned,
                  sa.sanction_ids,
                  sa.sanction_captions,
                  sa.sanction_topics,
                  sa.sanction_countries,
                  sa.sanction_programs,
                  -- Pro M&A heuristique : multi-mandats + holdings + age 50+
                  (d.n_mandats_actifs >= 5
                   AND COALESCE(sci.n_sci, 0) >= 1
                   AND COALESCE(d.age, 0) >= 50) AS is_pro_ma,
                  (COALESCE(d.age, 0) >= 60) AS is_senior,
                  (COALESCE(sci.total_capital_sci, 0) >= 500000) AS is_asset_rich
           FROM dirig d
           LEFT JOIN sci_agg sci
                  ON UPPER(unaccent(sci.nom)) = UPPER(unaccent(d.nom))
                 AND UPPER(unaccent(sci.prenom)) = UPPER(unaccent(d.prenom))
                 AND COALESCE(sci.date_naissance, '') = COALESCE(d.date_naissance, '')
           LEFT JOIN sci_patrimoine_value spv
                  ON UPPER(unaccent(spv.nom)) = UPPER(unaccent(d.nom))
                 AND UPPER(unaccent(spv.prenom)) = UPPER(unaccent(d.prenom))
                 AND COALESCE(spv.date_naissance, '') = COALESCE(d.date_naissance, '')
           LEFT JOIN sanc_agg sa
                  ON UPPER(unaccent(sa.nom)) = UPPER(unaccent(d.nom))
                 AND UPPER(unaccent(sa.prenom)) = UPPER(unaccent(d.prenom))
           LEFT JOIN LATERAL (
                  -- LIMIT 1 pour ne pas multiplier les rows quand
                  -- silver.osint_persons_enriched a plusieurs entries pour la
                  -- même personne (ex : 1 par representant_id distinct).
                  SELECT person_uid, has_linkedin, has_github, has_any_social,
                         n_linkedin, n_github, n_twitter, n_other_sites,
                         n_total_social, denomination_main_company,
                         forme_juridique_main, capital_main, date_immat_main,
                         n_mandats_inpi, last_scanned_at
                  FROM silver.osint_persons_enriched os2
                  WHERE UPPER(unaccent(os2.nom)) = UPPER(unaccent(d.nom))
                    AND EXISTS (
                          SELECT 1 FROM unnest(os2.prenoms) p
                          WHERE UPPER(unaccent(p)) = UPPER(unaccent(d.prenom))
                    )
                    AND COALESCE(os2.date_naissance, '') = COALESCE(d.date_naissance, '')
                  ORDER BY n_total_social DESC NULLS LAST
                  LIMIT 1
           ) os ON true
           ORDER BY d.n_mandats_actifs DESC NULLS LAST""",
        siren,
    )

    # Fallback : si silver vide, dérive depuis le gouv API (déjà fetché).
    # Gestion des 2 types de dirigeants :
    #   - personne physique : nom + prenoms + annee_de_naissance + qualite
    #   - personne morale   : siren + denomination + qualite
    if not dirigeants_silver and gouv and gouv.get("dirigeants"):
        def _map_dirig(d: dict) -> dict:
            type_d = d.get("type_dirigeant") or ("personne physique" if d.get("nom") or d.get("prenoms") else "personne morale")
            is_phys = type_d == "personne physique"
            if is_phys:
                nom = (d.get("nom") or "").strip()
                prenom = (d.get("prenoms") or "").strip()
                annee = d.get("annee_de_naissance") or d.get("date_de_naissance")
                age = (2026 - int(annee)) if annee and str(annee).isdigit() else None
                date_n = d.get("date_de_naissance") or (str(annee) if annee else None)
            else:
                # personne morale : utiliser denomination comme "nom"
                nom = (d.get("denomination") or d.get("nom") or "").strip()
                prenom = ""
                age = None
                date_n = None
            return {
                "nom": nom,
                "prenom": prenom,
                "date_naissance": date_n,
                "age": age,
                "qualite": d.get("qualite") or "",
                "type_dirigeant": type_d,
                "siren_dirigeant": d.get("siren") if not is_phys else None,
                "n_mandats_actifs": 1,
                "n_mandats_total": 1,
                "sirens_mandats": [siren],
                "denominations": [fiche["denomination"]],
                "roles": [d.get("qualite", "")] if d.get("qualite") else [],
                "is_multi_mandat": False,
                "n_sci": None,
                "total_capital_sci": None,
                "sci_denominations": None,
                "has_linkedin": None,
                "has_github": None,
                "n_total_social": None,
                "is_sanctioned": False,
            }
        dirigeants = [_map_dirig(d) for d in gouv["dirigeants"][:10]]
    else:
        dirigeants = dirigeants_silver

    # Override compteurs si fallback fourni des données.
    # Évite l'incohérence "tab Dirigeants 3 / cellule DIRIGEANTS 0" en bas de fiche.
    if isinstance(fiche, dict):
        if dirigeants and (fiche.get("n_dirigeants") or 0) < len(dirigeants):
            fiche["n_dirigeants"] = len(dirigeants)

    # Signaux M&A — BODACC (annonces commerciales). Silver d'abord, fallback
    # API gov BODACC live si vide.
    signaux: list = []
    if await _table_exists(pool, "silver", "bodacc_annonces"):
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
        )

    if not signaux:
        # Fallback live BODACC datadila API. Si succès, on récupère aussi le
        # COUNT total via nhits (pas juste les 20 affichés) pour que le
        # compteur n_bodacc soit fidèle.
        try:
            import httpx as _httpx2
            async with _httpx2.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"https://bodacc-datadila.opendatasoft.com/api/records/1.0/search/"
                    f"?dataset=annonces-commerciales&q={siren}&rows=20&sort=-dateparution"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    signaux = [
                        {
                            "event_date": r.get("fields", {}).get("dateparution"),
                            "signal_type": r.get("fields", {}).get("typeavis_lib") or r.get("fields", {}).get("typeavis"),
                            "severity": r.get("fields", {}).get("familleavis_lib") or r.get("fields", {}).get("familleavis"),
                            "source": r.get("fields", {}).get("tribunal"),
                            "ville": r.get("fields", {}).get("ville"),
                            "departement": r.get("fields", {}).get("departement_nom_officiel"),
                            "code_dept": r.get("fields", {}).get("departement_code"),
                            "_live": True,
                        }
                        for r in (data.get("records") or [])
                    ]
                    # Update n_bodacc avec le total réel (nhits) du dataset
                    if isinstance(fiche, dict):
                        fiche["n_bodacc"] = data.get("nhits", len(signaux))
        except Exception as e:
            print(f"[fiche] BODACC live API failed: {type(e).__name__}: {str(e)[:80]}")

    # Compliance — UNIQUEMENT via silver.sanctions (table unifiée AMF + OpenSanctions
    # + ICIJ + DGCCRF + CNIL). Le backend ne touche PAS bronze.
    deno_for_match = (fiche.get("denomination") if isinstance(fiche, dict) else None) or ""

    red_flags: list = []
    if deno_for_match and await _table_exists(pool, "silver", "sanctions"):
        red_flags_rows = await _safe(pool.fetch(
            """SELECT sanction_uid AS entity_id,
                      entreprise AS caption,
                      type_decision AS schema,
                      topics,
                      countries,
                      ARRAY[type_decision, motif]::text[] AS sanctions_programs,
                      date_decision AS first_seen,
                      date_decision AS last_seen,
                      source AS _source,
                      CASE WHEN siren = $2 THEN 'siren_match' ELSE 'name_match' END AS _match_type,
                      severity,
                      montant_amende,
                      jurisdiction
               FROM silver.sanctions
               WHERE siren = $2 OR entity_lower ILIKE $1
               ORDER BY
                 CASE severity
                   WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                   WHEN 'medium'   THEN 3 WHEN 'low'  THEN 4
                 END,
                 date_decision DESC NULLS LAST
               LIMIT 50""",
            deno_for_match.lower(), siren,
        ), default=[])
        red_flags = [dict(r) for r in red_flags_rows]

    # Statut radiation : red flag immédiat si etat_administratif = C ou date_fermeture
    try:
        is_cesse = isinstance(fiche, dict) and (
            fiche.get("statut") in ("cesse", "cessée", "C", "RADIE")
            or fiche.get("etat_administratif") == "C"
            or bool(fiche.get("date_fermeture"))
        )
        if is_cesse:
            date_cessation = (fiche or {}).get("date_fermeture") or (fiche or {}).get("date_cessation") or "—"
            red_flags.insert(0, {
                "entity_id": f"status-{siren}",
                "caption": f"Société CESSÉE le {date_cessation}",
                "schema": "STATUS_RADIATION",
                "_source": "INSEE",
                "_match_type": "siren_match",
                "severity": "critical",
                "first_seen": str(date_cessation),
                "last_seen": str(date_cessation),
                "topics": ["cessation"],
                "countries": ["FR"],
                "sanctions_programs": ["RADIATION"],
            })
    except Exception as e:
        print(f"[red_flags] status enrichment skipped: {e}")

    # Procédures collectives via signaux BODACC déjà fetchés
    try:
        for s in signaux:
            d = dict(s) if not isinstance(s, dict) else s
            famille = (d.get("familleavis_lib") or d.get("famille") or "").lower()
            type_av = (d.get("typeavis_lib") or d.get("typeavis") or "").lower()
            if "procédure" in famille or "procedure collective" in famille or "redressement" in famille or "liquidation" in type_av or "radiation" in type_av:
                red_flags.append({
                    "entity_id": f"bodacc-{d.get('annonce_id', d.get('id', siren))}",
                    "caption": f"Signal BODACC : {d.get('typeavis_lib') or d.get('familleavis_lib') or 'BODACC'}",
                    "schema": "BODACC_PROCEDURE",
                    "_source": "BODACC",
                    "_match_type": "siren_match",
                    "severity": "high",
                    "first_seen": str(d.get("date_parution") or "—"),
                    "last_seen": str(d.get("date_parution") or "—"),
                    "topics": ["procedure_collective"],
                    "countries": ["FR"],
                    "sanctions_programs": [d.get("typeavis_lib") or "Procédure collective"],
                })
    except Exception as e:
        print(f"[red_flags] BODACC procedures enrichment skipped: {e}")

    # Réseau — co-mandats : silver.inpi_dirigeants (top 3 dirigeants → autres
    # sirens). Fallback : dirigeants gouv API qui ont un siren (personnes morales).
    network: list = []
    if await _table_exists(pool, "silver", "inpi_dirigeants"):
        network = await pool.fetch(
            """WITH top_dirig AS (
                  SELECT nom, prenom, sirens_mandats, denominations
                  FROM silver.inpi_dirigeants
                  WHERE $1::char(9) = ANY(sirens_mandats)
                  ORDER BY n_mandats_actifs DESC NULLS LAST
                  LIMIT 3
               ),
               expanded AS (
                  SELECT d.nom, d.prenom,
                         unnest(d.sirens_mandats) AS other_siren,
                         unnest(d.denominations) AS other_deno
                  FROM top_dirig d
               )
               -- Bug v5/3.13 — SIREN apparaissait 2-3× quand silver avait
               -- plusieurs orthographes pour la même entité (ex 441639465).
               -- GROUP BY siren only + max(denomination) consolide.
               SELECT other_siren AS siren,
                      max(other_deno) AS denomination,
                      string_agg(DISTINCT prenom || ' ' || nom, ', ') AS via_dirigeants
               FROM expanded
               WHERE other_siren != $1::char(9) AND other_siren IS NOT NULL
               GROUP BY other_siren
               ORDER BY max(other_deno)
               LIMIT 20""",
            siren,
        )

    if not network and gouv:
        # Fallback : personnes morales dans dirigeants gouv API ARE co-mandats.
        moral_dirigs = [d for d in gouv.get("dirigeants", []) if d.get("siren") and d.get("denomination")]
        network = [
            {
                "siren": d["siren"],
                "denomination": d.get("denomination"),
                "via_dirigeants": d.get("qualite") or "Personne morale liée",
            }
            for d in moral_dirigs[:20]
        ]

    # Presse — skip silver.press_mentions_matched (vide), fallback Google News RSS
    presse: list = []
    if isinstance(fiche, dict) and fiche.get("denomination"):
        try:
            import httpx as _httpx3
            from defusedxml import ElementTree as _ET
            import urllib.parse as _urlparse
            q_press = _urlparse.quote(fiche["denomination"])
            async with _httpx3.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                resp = await client.get(
                    f"https://news.google.com/rss/search?q={q_press}&hl=fr-FR&gl=FR&ceid=FR:fr"
                )
                if resp.status_code == 200:
                    root = _ET.fromstring(resp.content)
                    items = root.findall(".//item")
                    for item in items[:10]:
                        title_el = item.find("title")
                        link_el = item.find("link")
                        date_el = item.find("pubDate")
                        source_el = item.find("source")
                        presse.append({
                            "title": (title_el.text or "")[:200] if title_el is not None else "",
                            "url": link_el.text if link_el is not None else None,
                            "published_at": date_el.text if date_el is not None else None,
                            "source": source_el.text if source_el is not None else "Google News",
                            "ma_signal_type": None,
                        })
        except Exception as e:
            print(f"[fiche] Google News RSS failed: {type(e).__name__}: {str(e)[:80]}")

    # Presse négative — enrichissement red flags après que `presse` soit construite
    try:
        NEG_KEYWORDS = (
            "fraude", "scandale", "condamné", "condamnée", "épingl",
            "tromp", "contrefa", "blanch", "corruption", "amende",
            "sanction", "perquisition", "garde à vue", "abus de bien",
            "redressement fiscal", "défaut", "défaillance",
        )
        for p in presse:
            d = dict(p) if not isinstance(p, dict) else p
            t = (d.get("title") or "").lower()
            if any(kw in t for kw in NEG_KEYWORDS):
                red_flags.append({
                    "entity_id": f"press-{abs(hash(d.get('title','') or ''))% 10**9}",
                    "caption": f"Presse négative : {d.get('title', '')[:120]}",
                    "schema": "PRESS_NEGATIVE",
                    "_source": d.get("source") or "Presse",
                    "_match_type": "name_match",
                    "severity": "medium",
                    "first_seen": str(d.get("published_at") or "—"),
                    "last_seen": str(d.get("published_at") or "—"),
                    "topics": ["presse_negative"],
                    "countries": ["FR"],
                    "sanctions_programs": ["PRESSE"],
                    "url": d.get("url"),
                })
    except Exception as e:
        print(f"[red_flags] press enrichment skipped: {e}")

    # HATVP — registre des représentants d'intérêts (lobbying). Source silver
    # uniquement (backend interdiction de toucher bronze).
    hatvp = await _safe(pool.fetchrow(
        """SELECT representant_id, denomination, secteur_activite,
                  date_inscription, adresse_ville, nb_deputes,
                  chiffre_affaires_lobbying, has_active_lobbying
           FROM silver.hatvp_lobbying
           WHERE siren = $1::char(9) LIMIT 1""",
        siren,
    )) if await _table_exists(pool, "silver", "hatvp_lobbying") else None

    # Synchronise les compteurs avec les données réellement fetched (silver + fallbacks)
    if isinstance(fiche, dict):
        if signaux and (fiche.get("n_bodacc") or 0) < len(signaux):
            fiche["n_bodacc"] = len(signaux)
        if red_flags:
            fiche["n_sanctions"] = len(red_flags)
        fiche["n_presse"] = len(presse)
        fiche["n_network"] = len(network)
        # HATVP lobbying — signal de transparence
        if hatvp:
            fiche["hatvp"] = {
                "representant_id": hatvp.get("representant_id"),
                "secteur_activite": hatvp.get("secteur_activite"),
                "date_inscription": (
                    hatvp["date_inscription"].isoformat() if hatvp.get("date_inscription") else None
                ),
                "adresse_ville": hatvp.get("adresse_ville"),
                "nb_deputes": hatvp.get("nb_deputes"),
                "chiffre_affaires_lobbying": (
                    float(hatvp["chiffre_affaires_lobbying"]) if hatvp.get("chiffre_affaires_lobbying") else None
                ),
            }
            fiche["is_lobbying_registered"] = True
        else:
            fiche["is_lobbying_registered"] = False

    return {
        "fiche": _serialize(fiche) if hasattr(fiche, "items") and not isinstance(fiche, dict) else fiche,
        "dirigeants": [_serialize(d) for d in dirigeants],
        "signaux": [_serialize(s) for s in signaux],
        "red_flags": [_serialize(r) for r in red_flags],
        "network": [_serialize(n) for n in network],
        "presse": [_serialize(p) for p in presse],
    }


async def _dirigeant_full(
    req: Request, nom: str, prenom: str, date_naissance: str | None = None
):
    """Drill-down : retourne TOUTES les infos disponibles pour un dirigeant
    identifié par le triplet (nom, prenom, date_naissance).
    Sources silver agrégées :
      - inpi_dirigeants : carrière (mandats actifs / total / formes / roles)
      - dirigeant_sci_patrimoine : patrimoine SCI complet (denominations / sirens
        / code postaux / capital cumulé)
      - osint_persons_enriched : présence sociale (LinkedIn, GitHub, Twitter)
        + entreprise principale
      - opensanctions : matchs personne (topics / programs / countries)
      - dvf_transactions : transactions immobilières des SCI du dirigeant
    """
    pool = _pool(req)

    nom_u = (nom or "").strip()
    prenom_u = (prenom or "").strip()
    date_n = (date_naissance or "").strip() or None

    if not nom_u or not prenom_u:
        raise HTTPException(status_code=400, detail="nom + prenom requis")

    # 1. Identité INPI — match insensible casse/accents pour gérer "Mignon"
    # vs "MIGNON" et "DUFOÛR" vs "DUFOUR" qui sont les mêmes personnes.
    inpi = await _safe(pool.fetchrow(
        """SELECT
              MAX(nom) AS nom, MAX(prenom) AS prenom,
              MAX(date_naissance) AS date_naissance, MAX(age_2026) AS age,
              MAX(n_mandats_total) AS n_mandats_total,
              MAX(n_mandats_actifs) AS n_mandats_actifs,
              ARRAY(SELECT DISTINCT unnest(array_agg(sirens_mandats))) AS sirens_mandats,
              ARRAY(SELECT DISTINCT unnest(array_agg(denominations))) AS denominations,
              ARRAY(SELECT DISTINCT unnest(array_agg(formes_juridiques))) AS formes_juridiques,
              ARRAY(SELECT DISTINCT unnest(array_agg(roles))) AS roles,
              MIN(first_mandat_date) AS first_mandat_date,
              MAX(last_mandat_date) AS last_mandat_date,
              bool_or(is_multi_mandat) AS is_multi_mandat
           FROM silver.inpi_dirigeants
           WHERE UPPER(unaccent(nom)) = UPPER(unaccent($1))
             AND UPPER(unaccent(prenom)) = UPPER(unaccent($2))
             AND ($3::text IS NULL OR date_naissance LIKE $3 || '%')""",
        nom_u, prenom_u, date_n,
    ))

    # Pour les fallbacks ci-dessous, on UPPER + strip-accents côté Python pour
    # exploiter les index btree (nom) / btree (nom, prenom) sur
    # silver.dirigeants_360 et gold.dirigeants_master. UPPER(unaccent(...))
    # côté SQL force un seq scan → timeout 4s sur tables 8M+ rows.
    # On essaie avec ET sans accent pour couvrir les 2 conventions ETL :
    #   - "ÉRIC BACONNIER" cité par le LLM (avec accent)
    #   - "ERIC" stocké dans gold (sans accent, vérifié SQL direct)
    #   - "GRÉGOIRE" stocké aussi (CHERTOK) — donc OR sur les 2 versions.
    import unicodedata
    def _strip_accents(s: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    nom_uc = nom_u.upper()
    prenom_uc = prenom_u.upper()
    nom_uc_na = _strip_accents(nom_uc)
    prenom_uc_na = _strip_accents(prenom_uc)

    # Fallback 1 : silver.dirigeants_360 — feature store consolidé. Couvre les
    # dirigeants présents dans gold.dirigeants_master mais absents/incomplets
    # en silver.inpi_dirigeants (ex. ArraySubscriptError sur agg corrupt).
    if not inpi or not inpi.get("nom"):
        inpi = await _safe(pool.fetchrow(
            """SELECT nom, prenom, date_naissance, age_2026 AS age,
                      n_mandats_total, n_mandats_actifs,
                      sirens_mandats, denominations,
                      formes_juridiques, roles,
                      first_mandat_date, last_mandat_date,
                      is_multi_mandat
               FROM silver.dirigeants_360
               WHERE nom IN ($1, $2)
                 AND prenom IN ($3, $4)
                 AND ($5::text IS NULL OR date_naissance LIKE $5 || '%')
               ORDER BY n_mandats_actifs DESC NULLS LAST
               LIMIT 1""",
            nom_uc, nom_uc_na, prenom_uc, prenom_uc_na, date_n,
        ), timeout_s=8.0)

    # Fallback 2 : gold.dirigeants_master — au minimum on récupère le grain de base
    # pour ne pas 404 sur un dirigeant exposé en card mais absent des silvers
    # (cas v6 : Olivier Esteve / Maxime Moczulski / Tania Geny / Gregoire Chertok
    # remontés par fetchPersons depuis gold mais 404 sur l'ancienne route silver-only).
    if not inpi or not inpi.get("nom"):
        inpi = await _safe(pool.fetchrow(
            """SELECT nom, prenom,
                      NULL::text AS date_naissance,
                      age_2026 AS age,
                      NULL::bigint AS n_mandats_total,
                      n_mandats_actifs,
                      NULL::char(9)[] AS sirens_mandats,
                      NULL::text[] AS denominations,
                      NULL::text[] AS formes_juridiques,
                      NULL::text[] AS roles,
                      NULL::date AS first_mandat_date,
                      NULL::date AS last_mandat_date,
                      (n_mandats_actifs >= 5) AS is_multi_mandat
               FROM gold.dirigeants_master
               WHERE nom IN ($1, $2) AND prenom IN ($3, $4)
               ORDER BY pro_ma_score DESC NULLS LAST
               LIMIT 1""",
            nom_uc, nom_uc_na, prenom_uc, prenom_uc_na,
        ), timeout_s=8.0)

    if not inpi or not inpi.get("nom"):
        raise HTTPException(
            status_code=404,
            detail="Dirigeant introuvable (silver.inpi_dirigeants / silver.dirigeants_360 / gold.dirigeants_master)",
        )

    # 2. Patrimoine SCI agrégé sur (nom, prenom, date_naissance) normalisé
    sci = await _safe(pool.fetchrow(
        """SELECT
              SUM(n_sci) AS n_sci,
              SUM(total_capital_sci) AS total_capital_sci,
              ARRAY(SELECT DISTINCT unnest(array_agg(sci_denominations))) AS sci_denominations,
              ARRAY(SELECT DISTINCT unnest(array_agg(sci_sirens))) AS sci_sirens,
              ARRAY(SELECT DISTINCT unnest(array_agg(sci_code_postaux))) AS sci_code_postaux,
              MIN(first_sci_date) AS first_sci_date
           FROM silver.dirigeant_sci_patrimoine
           WHERE UPPER(unaccent(nom)) = UPPER(unaccent($1))
             AND UPPER(unaccent(prenom)) = UPPER(unaccent($2))
             AND ($3::text IS NULL OR date_naissance LIKE $3 || '%')""",
        nom_u, prenom_u, date_n,
    ))

    # 2 bis. Valeur réelle du patrimoine SCI : agrégation des derniers comptes
    # déposés à l'INPI pour chaque siren SCI du dirigeant.
    sci_values: list = []
    sci_value_total: dict | None = None
    if sci and sci.get("sci_sirens"):
        sirens = [s for s in sci.get("sci_sirens") or [] if s]
        if sirens:
            sci_values = await _safe(pool.fetch(
                """SELECT DISTINCT ON (siren)
                       siren, denomination, date_cloture,
                       total_actif, immo_corporelles,
                       capitaux_propres, ca_net, resultat_net,
                       capital_social, emprunts_dettes
                   FROM silver.inpi_comptes
                   WHERE siren = ANY($1::char(9)[])
                   ORDER BY siren, date_cloture DESC NULLS LAST""",
                sirens,
            ), default=[])
            # Agrégation totale
            sum_actif = sum((float(r["total_actif"]) for r in sci_values if r["total_actif"] is not None), 0.0)
            sum_immo = sum((float(r["immo_corporelles"]) for r in sci_values if r["immo_corporelles"] is not None), 0.0)
            sum_cp = sum((float(r["capitaux_propres"]) for r in sci_values if r["capitaux_propres"] is not None), 0.0)
            sum_ca = sum((float(r["ca_net"]) for r in sci_values if r["ca_net"] is not None), 0.0)
            sum_dettes = sum((float(r["emprunts_dettes"]) for r in sci_values if r["emprunts_dettes"] is not None), 0.0)
            sci_value_total = {
                "total_actif": sum_actif if sum_actif else None,
                "immo_corporelles": sum_immo if sum_immo else None,
                "capitaux_propres": sum_cp if sum_cp else None,
                "ca_net_total": sum_ca if sum_ca else None,
                "emprunts_dettes": sum_dettes if sum_dettes else None,
                "n_sci_with_comptes": len(sci_values),
            }

    # 3. OSINT (LinkedIn, GitHub, Twitter, sites perso, entreprise principale)
    # JOIN robuste : prenom dans prenoms[] insensible casse/accents
    osint = await _safe(pool.fetchrow(
        """SELECT
              person_uid, siren_main, representant_id, prenoms,
              n_linkedin, n_github, n_twitter, n_other_sites, n_total_social,
              has_linkedin, has_github, has_any_social,
              denomination_main_company, forme_juridique_main,
              capital_main, date_immat_main, n_mandats_inpi,
              last_scanned_at
           FROM silver.osint_persons_enriched
           WHERE UPPER(unaccent(nom)) = UPPER(unaccent($1))
             AND EXISTS (
                   SELECT 1 FROM unnest(prenoms) p
                   WHERE UPPER(unaccent(p)) = UPPER(unaccent($2))
             )
             AND ($3::text IS NULL OR date_naissance LIKE $3 || '%')
           ORDER BY n_total_social DESC NULLS LAST
           LIMIT 1""",
        nom_u, prenom_u, date_n,
    ))

    # 3 bis. OSINT brut : URLs LinkedIn / GitHub / Twitter / Crunchbase / Medium /
    # YouTube / Facebook / Instagram + emails testes/valides + sources scannees.
    # Source : silver.osint_persons_enriched (yaml etendu, exposera ces colonnes
    # apres le prochain refresh interval_hours=6).
    osint_raw = await _safe(pool.fetchrow(
        """SELECT
              linkedin_urls, github_usernames, twitter_handles,
              instagram_handles, medium_profiles, facebook_urls,
              youtube_channels, crunchbase_url,
              other_sites, emails_tested, emails_valid, email_services,
              sources_scanned
           FROM silver.osint_persons_enriched
           WHERE UPPER(unaccent(nom)) = UPPER(unaccent($1))
             AND EXISTS (
                   SELECT 1 FROM unnest(prenoms) p
                   WHERE UPPER(unaccent(p)) = UPPER(unaccent($2))
             )
             AND ($3::text IS NULL OR date_naissance LIKE $3 || '%')
           ORDER BY last_scanned_at DESC NULLS LAST
           LIMIT 1""",
        nom_u, prenom_u, date_n,
    ))

    # 4. Sanctions personne — match dans caption insensible casse/accents
    sanctions = await _safe(pool.fetch(
        """SELECT entity_id, caption, schema, topics, countries,
                  sanctions_programs, first_seen, last_seen, alias_names
           FROM silver.opensanctions
           WHERE schema = 'Person'
             AND UPPER(unaccent(name)) ILIKE '%' || UPPER(unaccent($1)) || '%'
             AND UPPER(unaccent(name)) ILIKE '%' || UPPER(unaccent($2)) || '%'
           LIMIT 20""",
        nom_u, prenom_u,
    ), default=[])

    # 5. DVF immo — transactions liées aux SCI du dirigeant
    dvf_summary: dict | None = None
    if sci and sci.get("sci_sirens"):
        # Note : DVF n'a pas de siren, on récupère par code_postal des SCI
        # (proxy approximatif). Bilan = nombre + valeur cumulée par CP.
        cps = sci.get("sci_code_postaux") or []
        if cps:
            dvf_rows = await _safe(pool.fetch(
                """SELECT code_postal, COUNT(*) AS n, SUM(valeur_fonciere) AS total
                   FROM silver.dvf_transactions
                   WHERE code_postal = ANY($1::text[])
                   GROUP BY code_postal
                   ORDER BY total DESC NULLS LAST
                   LIMIT 10""",
                cps,
            ), default=[])
            dvf_summary = {
                "n_zones": len(dvf_rows),
                "by_cp": [_serialize(r) for r in dvf_rows],
            }

    return {
        "identity": _serialize(inpi),
        "sci_patrimoine": _serialize(sci) if sci else None,
        "sci_value_total": sci_value_total,
        "sci_values_per_company": [_serialize(v) for v in sci_values],
        "osint": _serialize(osint) if osint else None,
        "osint_raw": _serialize(osint_raw) if osint_raw else None,
        "sanctions": [_serialize(s) for s in sanctions],
        "dvf_zones": dvf_summary,
    }


@router.get("/scoring/{siren}")
async def scoring_detail(req: Request, siren: str):
    """Détail scoring M&A v3 PRO — barème advisor 4 axes business multiplicatif.

    Source : gold.scoring_ma v3 (formule géométrique Transmission × Attractivity ×
    Scale × Risk_multiplier, percentile-based tier).

    Output keys :
    - deal_score (0-100), tier (A_HOT/B_WARM/C_PIPELINE/D_WATCH/E_REJECT/Z_ELIM),
      deal_percentile (1-100)
    - axes : {transmission, attractivity, scale, structure} chacun 0-100
    - risk : {multiplier, sanctions, procedure_collective, contentieux, late_filing}
    - financials : {ca_latest, proxy_ebitda, proxy_margin, sector_multiple, ev_estimated_eur}
    - context : {age_dirigeant_max, n_sci_dirigeants, n_dirigeants, has_pro_ma, ...}

    Voir docs/SIGNAUX_MA.md pour le détail du barème.
    """
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")
    pool = _pool(req)

    if not await _table_exists(pool, "gold", "scoring_ma"):
        raise HTTPException(
            status_code=503,
            detail="gold.scoring_ma pas encore matérialisée — silver_runner en cours",
        )

    row = await _safe(pool.fetchrow(
        "SELECT row_to_json(s.*) AS r FROM gold.scoring_ma s WHERE s.siren = $1",
        siren,
    ), timeout_s=4.0)

    if not row:
        raise HTTPException(status_code=404, detail=f"Pas de scoring pour {siren}")

    data = row["r"]
    if isinstance(data, str):
        data = json.loads(data)

    # Format v3 PRO — 4 axes business + risk multiplier + EV estimée
    return {
        "siren": siren,
        "denomination": data.get("denomination"),
        # Score global et tier
        "deal_score": data.get("deal_score_raw") or data.get("score_total") or 0,
        "deal_percentile": data.get("deal_percentile"),
        "tier": data.get("tier"),
        # 4 axes business 0-100
        "axes": {
            "transmission": data.get("transmission_score", 0),
            "attractivity": data.get("attractivity_score", 0),
            "scale": data.get("scale_score", 0),
            "structure": data.get("structure_score", 0),
        },
        # Risk multiplier détaillé
        "risk": {
            "multiplier": float(data.get("risk_multiplier") or 1.0),
            "has_sanction_ofac_eu": bool(data.get("has_sanction_ofac_eu")),
            "has_sanction_cnil": bool(data.get("has_sanction_cnil")),
            "has_sanction_dgccrf": bool(data.get("has_sanction_dgccrf")),
            "has_proc_collective_recent": bool(data.get("has_proc_collective_recent")),
            "has_cession_recent": bool(data.get("has_cession_recent")),
            "n_contentieux_recent": data.get("n_contentieux_recent") or 0,
            "has_late_filing": bool(data.get("has_late_filing")),
        },
        # Financials proxies + EV estimée
        "financials": {
            "ca_latest": float(data["ca_latest"]) if data.get("ca_latest") else None,
            "capitaux_propres_latest": float(data["capitaux_propres_latest"]) if data.get("capitaux_propres_latest") else None,
            "resultat_net_latest": float(data["resultat_net_latest"]) if data.get("resultat_net_latest") else None,
            "proxy_ebitda": float(data["proxy_ebitda"]) if data.get("proxy_ebitda") else None,
            # proxy_margin = (resultat_net + 5% capital) / ca_latest. Sur les
            # holdings avec gros capital social (Equans : 2,2 Md€) et faible
            # CA opérationnel, le 5% capital dépasse le CA → marge >100% qui
            # n'a aucun sens M&A. Cap [-100, 100] côté API pour ne pas afficher
            # "Marge proxy 114,6%" dans la fiche.
            "proxy_margin": (
                max(-1.0, min(1.0, float(data["proxy_margin"])))
                if data.get("proxy_margin") is not None else None
            ),
            "sector_multiple": float(data["sector_multiple"]) if data.get("sector_multiple") else None,
            "ev_estimated_eur": float(data["ev_estimated_eur"]) if data.get("ev_estimated_eur") else None,
        },
        # Contexte (filtres / affichage)
        "context": {
            "code_ape": data.get("code_ape"),
            "adresse_dept": data.get("adresse_dept"),
            "forme_juridique": data.get("forme_juridique"),
            "capital_social": float(data["capital_social"]) if data.get("capital_social") else None,
            "age_entreprise": data.get("age_entreprise"),
            "effectif_salarie": data.get("effectif_salarie"),
            "age_dirigeant_max": data.get("age_dirigeant_max"),
            "n_dirigeants": data.get("n_dirigeants"),
            "n_mandats_dirigeant_max": data.get("n_mandats_dirigeant_max"),
            "has_pro_ma": bool(data.get("has_pro_ma")),
            "has_dirigeant_senior": bool(data.get("has_dirigeant_senior")),
            "n_sci_dirigeants": float(data["n_sci_dirigeants"]) if data.get("n_sci_dirigeants") else None,
            "total_capital_sci": float(data["total_capital_sci"]) if data.get("total_capital_sci") else None,
            "has_holding_patrimoniale": bool(data.get("has_holding_patrimoniale")),
            "is_sector_premium": bool(data.get("is_sector_premium")),
            "is_geo_premium": bool(data.get("is_geo_premium")),
            "is_stable": bool(data.get("is_stable")),
            "is_clean_legal_form": bool(data.get("is_clean_legal_form")),
            "lei": data.get("lei"),
        },
        # Compat ascendante : ancien score_total mappé sur deal_score
        "score_total": data.get("deal_score_raw") or data.get("score_total") or 0,
        "feature_version": "v3_pro_4axes",
        "derniere_maj": str(data.get("materialized_at")) if data.get("materialized_at") else None,
    }


@router.get("/_scoring_detail_legacy/{siren}")
async def scoring_detail_legacy(req: Request, siren: str):
    """Legacy : ancien format 13 dimensions / 123 signaux additif.

    Conservé pour compat ascendante (clients qui consomment encore l'ancien format).
    À déprécier après migration complète frontend → format v3.
    """
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")
    pool = _pool(req)
    if not await _table_exists(pool, "gold", "scoring_ma"):
        raise HTTPException(status_code=503, detail="scoring_ma pas matérialisée")
    row = await _safe(pool.fetchrow(
        "SELECT row_to_json(s.*) AS r FROM gold.scoring_ma s WHERE s.siren = $1", siren,
    ), timeout_s=4.0)
    if not row:
        raise HTTPException(status_code=404, detail=f"Pas de scoring pour {siren}")
    data = row["r"]
    if isinstance(data, str):
        data = json.loads(data)

    # Décompose les signaux par dimension pour l'UI
    DIM_SIGNALS = {
        "1_maturite": [
            ("sig_founder_60_no_successor", "Fondateur 60+ sans successeur", 7),
            ("sig_founder_over_65", "Dirigeant 65+", 6),
            ("sig_director_withdrawal", "Retrait progressif fondateur", 5),
            ("sig_spouse_director_departure", "Départ conjoint co-dirigeant", 5),
            ("sig_founder_age_55_65", "Dirigeant 55-65 ans", 3),
            ("sig_director_mandate_20plus", "Mandat > 20 ans", 2),
            ("sig_dirigeant_multi_mandats", "Multi-mandats", 3),
            ("sig_director_new_ventures", "Nouveaux projets", 2),
            ("sig_director_speaker", "Conférences / speaker", 2),
            ("sig_director_health_proxy", "Activité réduite (proxy)", 1),
        ],
        "2_patrimoniaux": [
            ("sig_holding_creation", "Création holding patrimoniale", 7),
            ("sig_bodacc_cession", "BODACC cession", 7),
            ("sig_apport_cession_structure", "Apport-cession 150-0 B ter", 6),
            ("sig_share_sale_by_director", "Cession parts dirigeant", 6),
            ("sig_beneficiaire_effectif_change", "Changement BE", 5),
            ("sig_bodacc_capital_change", "Modif capital BODACC", 5),
            ("sig_legal_form_change", "Transformation SARL→SAS", 4),
            ("sig_big4_audit", "Nomination Big 4", 4),
            ("sig_infogreffe_capital_change", "Modif capital Infogreffe", 4),
            ("sig_sci_creation_linked", "SCI liée (separation immo)", 3),
            ("sig_bodacc_dissolution", "Dissolution / liquidation", 3),
            ("sig_donation_partage", "Donation-partage", 3),
            ("sig_pacte_dutreil", "Pacte Dutreil", 2),
            ("sig_auditor_change", "Changement CAC", 2),
            ("sig_hq_relocation", "Déménagement siège", 1),
        ],
        "3_financier": [
            ("sig_procedure_collective", "Procédure collective", 6),
            ("sig_lbo_4_years", "LBO > 4 ans", 5),
            ("sig_revenue_decline_2years", "Baisse CA > 10%", 4),
            ("sig_ebitda_margin_compression", "Compression marge EBITDA", 4),
            ("sig_pret_garanti_etat", "PGE en cours", 3),
            ("sig_debt_ratio_deterioration", "Ratio endettement > 4x EBITDA", 3),
            ("sig_exceptional_dividend", "Dividende exceptionnel", 3),
            ("sig_ca_growth_2years", "Croissance CA > 15%", 3),
            ("sig_score_defaillance_interne", "Score défaillance élevé", 3),
            ("sig_headcount_growth_20", "Croissance effectifs > 20%", 2),
            ("sig_late_filing", "Retard dépôt comptes", 2),
            ("sig_working_capital_stress", "Tension BFR", 2),
            ("sig_capex_decline", "Baisse capex", 1),
            ("sig_new_establishment", "Nouvel établissement", 1),
            ("sig_bpifrance_aid", "Aide BPI", 1),
            ("sig_presse_levee_fonds", "Presse : levée fonds", 2),
            ("sig_presse_difficultes", "Presse : difficultés", 4),
        ],
        "4_rh": [
            ("sig_daf_pe_recruitment", "Recrutement DAF ex-PE/Big4", 5),
            ("sig_key_hire_manda", "Recrutement directeur M&A", 5),
            ("sig_interim_management", "Manager de transition", 4),
            ("sig_infogreffe_nouveau_dirigeant", "Nouveau dirigeant", 4),
            ("sig_management_package_setup", "Management package BSPCE/AGA", 3),
            ("sig_cofounder_departure", "Départ co-fondateur", 3),
            ("sig_board_composition_change", "Modif conseil", 3),
            ("sig_mass_layoff_plan", "Plan licenciement", 2),
            ("sig_cse_information_consultation", "Info-consult CSE", 2),
            ("sig_linkedin_turnover_spike", "Pic turnover", 1),
        ],
        "5_consolidation": [
            ("sig_pe_platform_in_sector", "Plateforme PE active", 4),
            ("sig_competitor_acquired", "Concurrent racheté", 4),
            ("sig_infogreffe_fusion_absorption", "Fusion / absorption", 4),
            ("sig_sector_consolidation", "Consolidation sectorielle", 3),
            ("sig_foreign_buyer_entry", "Acquéreur étranger", 2),
            ("sig_sector_regulation_change", "Reg. sectorielle", 2),
            ("sig_presse_partenariat", "Partenariat", 2),
            ("sig_ma_event", "Transaction M&A secteur", 1),
            ("sig_sector_multiple_expansion", "Multiples valorisation", 1),
        ],
        "6_juridique": [
            ("sig_mandat_ad_hoc", "Mandat ad hoc", 4),
            ("sig_conciliation_procedure", "Conciliation", 4),
            ("sig_commercial_court_filing", "Tribunal Commerce", 3),
            ("sig_sanction_detected", "Sanction (gels/AMF/ACPR)", 3),
            ("sig_infogreffe_transfert_siege", "Transfert siège", 2),
            ("sig_change_of_purpose", "Modif objet social", 1),
            ("sig_litigation_signal", "Contentieux", 1),
            ("sig_rgpd_sanction", "Sanction CNIL/RGPD", 1),
            ("sig_environmental_sanction", "Sanction environnementale", 1),
        ],
        "13_proprietaires": [
            ("sig_dirigeant_high_net_worth", "Dirigeant fortuné (capital SCI > 5 M€)", 3),
            ("sig_dvf_dirigeant_cash_out", "Achat immo dirigeant > 1 M€ post-cession", 3),
            ("sig_clan_familial", "Clan familial (≥3 dirigeants même nom)", 2),
            ("sig_micro_empire", "Empire mandats (CA<5M + ≥10 mandats)", 2),
            ("sig_immo_corporelles_high", "Immo corporelles > 50% actif", 2),
            ("sig_treasury_excess", "Trésorerie excessive (CP > 70% passif)", 2),
            ("sig_ca_export_high", "Export > 30% CA", 1),
            ("sig_capex_underinvest", "Sous-investissement chronique", 1),
            ("sig_digital_powerhouse", "Tech-forward (LinkedIn 100+ + GitHub)", 2),
            ("sig_low_profile_target", "Fortune cachée (CA>5M sans présence digitale)", 3),
            ("sig_has_lei_code", "Code LEI international actif", 1),
            ("sig_active_lobbying_recent", "Lobbying HATVP < 24m", 1),
            ("sig_high_lobbying_budget", "Budget lobbying > 200 k€/an", 2),
            ("sig_dirigeant_pep", "Dirigeant PEP (Politically Exposed)", 3),
            ("sig_offshore_link", "Match ICIJ Panama/Paradise Papers", 4),
            ("sig_litigation_pattern", "≥3 cassations/CA en 5 ans", 2),
            ("sig_radiation_proche", "Radiation BODACC < 3m", 3),
            ("sig_avis_de_tiers", "Avis de tiers (créancier opposé)", 1),
            ("sig_phantom_holding", "Holding silencieuse + CA décroît", 3),
            ("sig_geographic_expansion", "Expansion ≥3 départements en 12m", 1),
        ],
    }

    dimensions_detail = []
    for dim_key, signals in DIM_SIGNALS.items():
        active = [{"key": k, "label": l, "points": p} for k, l, p in signals if data.get(k)]
        max_points = {
            "1_maturite": 20, "2_patrimoniaux": 20, "3_financier": 15,
            "4_rh": 12, "5_consolidation": 10, "6_juridique": 8,
            "13_proprietaires": 15,
        }[dim_key]
        score_key = f"score_dim{dim_key.split('_')[0]}"
        dimensions_detail.append({
            "dim": dim_key,
            "score": data.get(score_key, 0),
            "max": max_points,
            "active_signals": active,
            "n_total_signals": len(signals),
        })

    composites_active = [
        {"key": k, "active": data.get(k, False)}
        for k in ["composite_triple_patrimoine", "composite_exit_preparation",
                  "composite_distressed", "composite_succession_urgency", "composite_sector_wave"]
    ]

    return {
        "siren": siren,
        "score_total": data.get("score_total"),
        "score_brut": data.get("score_brut"),
        "priority_class": data.get("priority_class"),
        "composite_multiplier": float(data.get("composite_multiplier") or 1.0),
        "n_signals_detected": data.get("n_signals_detected"),
        "feature_version": data.get("feature_version"),
        "derniere_maj": data.get("derniere_maj"),
        "dimensions": dimensions_detail,
        "composites": composites_active,
    }


@router.get("/dirigeant/{nom}/{prenom}/{date_naissance}")
async def dirigeant_full_with_dn(
    req: Request, nom: str, prenom: str, date_naissance: str
):
    """Drill-down dirigeant identifié par triplet (nom, prenom, date_naissance)."""
    return await _dirigeant_full(req, nom, prenom, date_naissance)


@router.get("/dirigeant/{nom}/{prenom}")
async def dirigeant_full_no_dn(req: Request, nom: str, prenom: str):
    """Drill-down dirigeant sans date_naissance (peut matcher plusieurs homonymes)."""
    return await _dirigeant_full(req, nom, prenom, None)


@router.get("/groupe-filiation/{siren}")
async def groupe_filiation(req: Request, siren: str):
    """Identifie filiales + maison mere d'une societe via 3 sources :
    - silver.gleif_lei : parent_lei + ultimate_parent_lei (LEI international)
    - bronze.inpi_formalites_personnes : siren <-> entreprise_siren (PM dirigeantes)
    - silver.bodacc_annonces : evenements fusion/absorption/prise participation

    NB : utilise bronze.inpi_formalites_personnes uniquement cote backend
    (le frontend voit le contrat silver+ via cet endpoint API).
    """
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")
    pool = _pool(req)

    # 1. GLEIF parent / ultimate_parent (LEI codes — entreprises internationales)
    gleif = await _safe(pool.fetchrow(
        """SELECT lei, legal_name, parent_lei, ultimate_parent_lei
           FROM silver.gleif_lei
           WHERE siren_fr = $1 LIMIT 1""",
        siren,
    ))

    # Codes role INPI capital (vraies meres/filiales — pas commissaires comptes 71-75) :
    #   30 = associe / actionnaire     11 = represent. PM (president PM)
    #   29 = societe liee              40 = representant permanent
    #   99 = autre (peut inclure capital, on garde par defaut)
    CAPITAL_ROLES = ["30", "11", "29", "40", "99"]

    # 2. Maison mere via INPI : qui detient X au capital (PM dirigeante) ?
    meres_rows = await _safe(pool.fetch(
        """SELECT DISTINCT
              entreprise_siren AS mere_siren,
              entreprise_denomination AS mere_nom,
              entreprise_role_entreprise AS role,
              entreprise_indicateur_associe_unique AS associe_unique
           FROM bronze.inpi_formalites_personnes
           WHERE siren = $1
             AND UPPER(type_de_personne) = 'ENTREPRISE'
             AND COALESCE(actif, true) = true
             AND entreprise_siren IS NOT NULL
             AND entreprise_siren != $1
             AND entreprise_role_entreprise = ANY($2::text[])
           LIMIT 10""",
        siren, CAPITAL_ROLES,
    ), default=[])

    # 3. Filiales via INPI : qui a X au capital (PM dirigeante) ?
    filiales_rows = await _safe(pool.fetch(
        """SELECT DISTINCT
              p.siren AS filiale_siren,
              e.denomination AS filiale_nom,
              p.entreprise_role_entreprise AS role,
              p.entreprise_indicateur_associe_unique AS associe_unique,
              e.code_ape AS filiale_naf,
              e.adresse_commune AS filiale_ville
           FROM bronze.inpi_formalites_personnes p
           LEFT JOIN bronze.inpi_formalites_entreprises e ON e.siren = p.siren
           WHERE p.entreprise_siren = $1
             AND UPPER(p.type_de_personne) = 'ENTREPRISE'
             AND COALESCE(p.actif, true) = true
             AND p.siren != $1
             AND p.entreprise_role_entreprise = ANY($2::text[])
           LIMIT 50""",
        siren, CAPITAL_ROLES,
    ), default=[])

    # 4. Evenements groupe (BODACC fusion / absorption / prise participation)
    events_rows = await _safe(pool.fetch(
        """SELECT date_parution, familleavis_lib, typeavis_lib
           FROM silver.bodacc_annonces
           WHERE siren = $1
             AND (familleavis_lib ILIKE '%fusion%'
                  OR familleavis_lib ILIKE '%absorption%'
                  OR familleavis_lib ILIKE '%participation%'
                  OR familleavis_lib ILIKE '%scission%')
           ORDER BY date_parution DESC
           LIMIT 10""",
        siren,
    ), default=[])

    # Si filiales > 0 => societe est probablement une mere/holding
    is_holding = len(filiales_rows) >= 3
    is_filiale = len(meres_rows) > 0

    return {
        "siren": siren,
        "is_holding": is_holding,
        "is_filiale": is_filiale,
        "n_filiales_detectees": len(filiales_rows),
        "n_meres_detectees": len(meres_rows),
        "gleif": _serialize(gleif) if gleif else None,
        "meres": [_serialize(r) for r in meres_rows],
        "filiales": [_serialize(r) for r in filiales_rows],
        "evenements_groupe": [_serialize(r) for r in events_rows],
    }


@router.get("/pitch/{siren}")
async def pitch_pdf(req: Request, siren: str):
    """Génère un pitch PDF imprimable (HTML auto-print). L'utilisateur clique
    sur le bouton et son navigateur ouvre le dialog print → save as PDF.

    Données live : appelle /fiche en interne pour avoir les mêmes infos que
    la TargetSheet (financier, dirigeants, signaux, presse, network)."""
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")

    # Fetch la fiche enrichie
    f = await fiche_entreprise(req, siren)
    fiche = f["fiche"]
    dirigeants = f.get("dirigeants", [])
    signaux = f.get("signaux", [])
    network = f.get("network", [])
    presse = f.get("presse", [])
    red_flags = f.get("red_flags", [])

    def _h(s):
        return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def _fmt_eur(v):
        if v is None: return "—"
        try:
            n = float(v)
            if abs(n) >= 1e9: return f"{n/1e9:.1f} Md€"
            if abs(n) >= 1e6: return f"{n/1e6:.1f} M€"
            if abs(n) >= 1e3: return f"{n/1e3:.0f} k€"
            return f"{n:.0f} €"
        except (TypeError, ValueError):
            return "—"

    deno = _h(fiche.get("denomination") or siren)
    sigle = _h(fiche.get("sigle") or "")
    naf = _h(fiche.get("naf") or "—")
    naf_lib = _h(fiche.get("naf_libelle") or "")
    forme = _h(fiche.get("forme_juridique") or "—")
    annee = fiche.get("annee_creation") or "—"
    ville = _h(fiche.get("ville") or "—")
    cp = _h(fiche.get("adresse_code_postal") or "")
    dept = _h(fiche.get("dept") or "")
    adresse = _h(fiche.get("adresse") or "")
    ca = _fmt_eur(fiche.get("ca_dernier"))
    ebitda = _fmt_eur(fiche.get("ebitda_dernier"))
    capital = _fmt_eur(fiche.get("capital_social"))
    marge = fiche.get("marge_pct")
    marge_str = f"{marge}%" if marge is not None else "—"
    effectif = fiche.get("effectif_exact") or "—"
    n_etab = fiche.get("n_etablissements")
    n_etab_str = f"{n_etab} étab. ({fiche.get('n_etablissements_ouverts', 0)} ouverts)" if n_etab else "—"
    statut = fiche.get("statut", "actif")
    is_cesse = statut == "cesse"
    date_fermeture = fiche.get("date_fermeture")
    n_dirigeants = fiche.get("n_dirigeants", 0)
    n_bodacc = len(signaux) if signaux else fiche.get("n_bodacc", 0)
    n_sanctions = fiche.get("n_sanctions", 0)
    exercices = fiche.get("exercices", [])
    ca_history = fiche.get("ca_history", [])

    # Score breakdown (même heuristique que rowToTarget)
    try:
        ca_n = float(fiche.get("ca_dernier") or 0)
    except (TypeError, ValueError):
        ca_n = 0
    score = min(95, 50 + int(ca_n / 200_000)) if ca_n else 50

    dirigeants_html = "".join(
        f"""<tr>
            <td><strong>{_h(d.get('prenom', ''))} {_h(d.get('nom', ''))}</strong></td>
            <td>{_h(d.get('qualite') or d.get('roles', [''])[0] if d.get('roles') else '')}</td>
            <td>{_h(d.get('type_dirigeant', 'personne physique'))}</td>
            <td>{d.get('age') or '—'}</td>
            <td>{d.get('n_mandats_actifs') or 1} mandats</td>
        </tr>"""
        for d in dirigeants[:10]
    ) or '<tr><td colspan="5" style="color:#888">Aucun dirigeant identifié</td></tr>'

    signaux_html = "".join(
        f"""<tr>
            <td>{_h(str(s.get('event_date', ''))[:10])}</td>
            <td><strong>{_h(s.get('signal_type', ''))}</strong></td>
            <td>{_h(s.get('severity', ''))}</td>
            <td>{_h(s.get('source', ''))}</td>
            <td>{_h(s.get('ville', ''))}{f" ({_h(s.get('code_dept', ''))})" if s.get('code_dept') else ""}</td>
        </tr>"""
        for s in signaux[:15]
    ) or '<tr><td colspan="5" style="color:#888">Aucune annonce BODACC</td></tr>'

    network_html = "".join(
        f"""<li><strong>{_h(n.get('denomination', ''))}</strong> · siren <code>{_h(n.get('siren', ''))}</code> · <em>{_h(n.get('via_dirigeants', ''))}</em></li>"""
        for n in network[:15]
    ) or '<li style="color:#888">Aucun lien réseau</li>'

    presse_html = "".join(
        f"""<li>
            <span style="color:#666;font-size:10px">{_h(str(p.get('published_at', ''))[:16])}</span> ·
            <strong>{_h(p.get('source', ''))}</strong> ·
            {_h(p.get('title', ''))}
        </li>"""
        for p in presse[:10]
    ) or '<li style="color:#888">Aucun article de presse</li>'

    red_flags_html = "".join(
        f"""<li style="color:#e11d48">
            <strong>{_h(r.get('caption', r.get('entity_id', '')))}</strong> ·
            schema {_h(r.get('schema', ''))} ·
            {_h(', '.join(r.get('topics', []) if isinstance(r.get('topics'), list) else []))}
        </li>"""
        for r in red_flags[:10]
    ) or '<li style="color:#10b981">✓ Aucun red flag identifié (silver.opensanctions UE/US/UK/UN, ICIJ, PEP)</li>'

    cesse_badge = (
        f'<span style="background:#fee2e2;color:#b91c1c;padding:3px 10px;border-radius:999px;font-size:10px;font-weight:700;margin-left:10px;letter-spacing:.05em">'
        f'CESSÉE{f" · {date_fermeture}" if date_fermeture else ""}</span>'
        if is_cesse else ""
    )

    # CA history bars
    ca_bars_html = ""
    if ca_history and len(ca_history) >= 2:
        max_ca = max(ca_history)
        ca_bars_html = f"""
        <h2>Évolution chiffre d'affaires (5 derniers exercices)</h2>
        <table class="ca-history">
          <tr>{''.join(f'<th>{_h(str(e)[:4])}</th>' for e in exercices[-len(ca_history):])}</tr>
          <tr>{''.join(f'<td><div class="bar" style="height:{int((c/max_ca) * 80)}px"></div><div class="ca-val">{_fmt_eur(c)}</div></td>' for c in ca_history)}</tr>
        </table>
        """

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Pitch Ready — {deno}</title>
<style>
  @page {{ size: A4; margin: 12mm 14mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    color: #18181b;
    line-height: 1.5;
    font-size: 12px;
    margin: 0;
  }}
  h1 {{ font-size: 24px; margin: 0 0 4px; letter-spacing: -0.02em; font-weight: 700; }}
  h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; color: #6366f1; margin: 18px 0 8px; padding-bottom: 4px; border-bottom: 1px solid #e4e4e7; }}
  .header {{ border-bottom: 2px solid #18181b; padding-bottom: 12px; margin-bottom: 18px; display: flex; align-items: flex-start; gap: 16px; }}
  .score-circle {{
    width: 70px; height: 70px; border-radius: 50%;
    background: linear-gradient(135deg, #10b981, #059669);
    color: white; display: flex; align-items: center; justify-content: center;
    font-size: 28px; font-weight: 700; flex-shrink: 0;
  }}
  .meta-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 6px; font-size: 11px; color: #52525b; }}
  .meta-row span {{ white-space: nowrap; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 14px 0; }}
  .kpi {{ border: 1px solid #e4e4e7; border-radius: 8px; padding: 10px 12px; }}
  .kpi-label {{ font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: #71717a; font-weight: 600; }}
  .kpi-val {{ font-size: 18px; font-weight: 700; margin-top: 4px; font-variant-numeric: tabular-nums; }}
  .kpi-sub {{ font-size: 10px; color: #71717a; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  th, td {{ padding: 6px 8px; border-bottom: 1px solid #f3f4f6; text-align: left; }}
  th {{ background: #f9fafb; font-weight: 600; color: #6b7280; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; }}
  ul {{ margin: 6px 0; padding-left: 18px; }}
  li {{ margin-bottom: 4px; font-size: 11px; }}
  code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 10px; }}
  .verdict {{
    margin-top: 14px; padding: 12px 16px;
    background: linear-gradient(135deg, #eef2ff, #faf5ff);
    border-left: 3px solid #6366f1; border-radius: 6px;
  }}
  .verdict h3 {{ margin: 0 0 4px; color: #6366f1; font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; }}
  .footer {{ margin-top: 24px; padding-top: 12px; border-top: 1px solid #e4e4e7; font-size: 9px; color: #71717a; display: flex; justify-content: space-between; }}
  .ca-history td {{ vertical-align: bottom; text-align: center; padding: 4px 2px; }}
  .ca-history .bar {{ background: linear-gradient(180deg, #6366f1, #818cf8); border-radius: 2px 2px 0 0; min-height: 4px; margin: 0 auto; width: 36px; }}
  .ca-history .ca-val {{ font-size: 9px; color: #52525b; margin-top: 2px; font-variant-numeric: tabular-nums; }}
  .ca-history th {{ font-size: 9px; text-align: center; }}
  .source-tag {{
    display: inline-block; padding: 2px 6px; border-radius: 3px;
    background: #e0f2fe; color: #0369a1; font-size: 9px; font-weight: 600;
  }}
  @media print {{
    body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    h2 {{ page-break-after: avoid; }}
    table, ul {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body onload="setTimeout(() => window.print(), 350)">

<div class="header">
  <div class="score-circle">{score}</div>
  <div style="flex:1">
    <div style="font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; color: #6366f1; font-weight: 600;">
      EdRCF Pitch Ready · Cible M&A · NAF {naf}{f" — {naf_lib}" if naf_lib and naf_lib != naf else ""}
    </div>
    <h1>{deno} {f'<span style="font-size:16px;color:#71717a;font-weight:500">({sigle})</span>' if sigle else ""} {cesse_badge}</h1>
    <div class="meta-row">
      <span><strong>siren</strong> <code>{siren}</code></span>
      <span><strong>Forme</strong> {forme}</span>
      <span><strong>Créée en</strong> {annee}</span>
      <span><strong>Localisation</strong> {ville}{f' · {cp}' if cp else ''}{f' ({dept})' if dept else ''}</span>
      <span><strong>{n_etab_str}</strong></span>
    </div>
    {f'<div style="font-size:10px;color:#71717a;margin-top:4px">📍 {adresse}</div>' if adresse else ''}
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-label">CA dernier exercice</div>
    <div class="kpi-val">{ca}</div>
    <div class="kpi-sub">Exercice {str(exercices[-1])[:4] if exercices else '—'}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">EBITDA / Résultat</div>
    <div class="kpi-val">{ebitda}</div>
    <div class="kpi-sub">Marge {marge_str}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Effectif</div>
    <div class="kpi-val">{effectif}</div>
    <div class="kpi-sub">moyen exercice</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Capital social</div>
    <div class="kpi-val">{capital}</div>
    <div class="kpi-sub">{forme}</div>
  </div>
</div>

<div class="verdict">
  <h3>Verdict DEMOEMA</h3>
  <p style="margin:0">
    Cible <strong>{'HIGH' if score >= 80 else 'MID-HIGH' if score >= 70 else 'MID'} potentiel</strong> ·
    Score <strong>{score}/100</strong> — {'tier-1, prioritaire' if score >= 80 else 'tier-1, à qualifier' if score >= 70 else 'tier-2, surveillance'}.
    {('Attention : société CESSÉE le ' + (date_fermeture or '')) if is_cesse else ''}
    {('Compliance : ' + str(n_sanctions) + ' red flag(s) OpenSanctions à expliquer en DD.') if n_sanctions else 'Compliance OK (OpenSanctions UE/US/UK/UN, ICIJ, PEP).'}
  </p>
</div>

{ca_bars_html}

<h2>Dirigeants ({n_dirigeants})</h2>
<table>
  <tr><th>Nom</th><th>Qualité</th><th>Type</th><th>Âge</th><th>Mandats</th></tr>
  {dirigeants_html}
</table>

<h2>Réseau (co-mandats / personnes morales liées)</h2>
<ul>{network_html}</ul>

<h2>Compliance — OpenSanctions</h2>
<ul>{red_flags_html}</ul>

<h2>Signaux BODACC ({n_bodacc})</h2>
<table>
  <tr><th>Date</th><th>Type</th><th>Famille</th><th>Tribunal</th><th>Ville</th></tr>
  {signaux_html}
</table>

<h2>Presse — Google News (10 derniers articles)</h2>
<ul>{presse_html}</ul>

<div class="footer">
  <div>
    <strong>EdRCF Pitch Ready</strong> · Document confidentiel · Anne Dupont · siren {siren}<br>
    Sources : <span class="source-tag">silver.inpi_comptes</span> <span class="source-tag">recherche-entreprises.api.gouv.fr</span> <span class="source-tag">bodacc-datadila</span> <span class="source-tag">silver.opensanctions</span> <span class="source-tag">Google News</span>
  </div>
  <div style="text-align:right">Généré le {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
</div>

</body>
</html>"""

    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/pitch-pdf/{siren}")
async def pitch_pdf_real(req: Request, siren: str):
    """Génère un VRAI PDF côté serveur (Bug S rapport QA — avant : window.print
    en HTML). Utilise WeasyPrint pour rendre le HTML pitch en PDF.

    Si WeasyPrint n'est pas disponible (libs natives cairo/pango manquantes),
    fallback gracieux vers le HTML print-friendly + Content-Disposition
    inline pour que le navigateur l'affiche sans déclencher /print.
    """
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")

    # Récupère le HTML existant via la route /pitch
    html_response = await pitch_pdf(req, siren)
    html_content = html_response.body.decode("utf-8") if isinstance(html_response.body, bytes) else str(html_response.body)

    # Tente WeasyPrint
    try:
        from weasyprint import HTML  # type: ignore
        pdf_bytes = HTML(string=html_content, base_url=str(req.base_url)).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="pitch_{siren}.pdf"',
                "Cache-Control": "no-store",
            },
        )
    except ImportError:
        # WeasyPrint pas installé : fallback HTML imprimable
        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="pitch_{siren}.html"',
                "X-PDF-Notice": "WeasyPrint not available — HTML returned. Use browser print → Save as PDF.",
            },
        )
    except Exception as e:
        # Erreur rendu (ex: CSS non supporté) : log + fallback HTML
        print(f"[pitch_pdf_real] WeasyPrint failed for {siren}: {type(e).__name__}: {e}")
        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="pitch_{siren}.html"',
                "X-PDF-Notice": f"WeasyPrint error: {type(e).__name__}",
            },
        )


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

    # Bug v6/1.11 — /dashboard utilisait _cibles_from_silver qui retourne
    # toujours score 95 (proxy LEAST(95, 50+CA/200000)). /api/datalake/cibles
    # utilise la logique gold avec axes Transmission/Attractivity/Scale/
    # Structure et scores réels [78-91]. Du coup même session = 2 scorings
    # contradictoires (top_targets toujours 95, /cibles 78-91).
    # Fix : router via gold quand dispo, exactement comme cibles_search.
    top_targets = await _cibles_with_routing(pool, "score_ma", 5, 0)

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
    (10-50M), dd (50-100M), loi (100-500M), closing (>500M).

    Bug v6/1.11 — utilise _cibles_with_routing pour aller chercher en gold
    quand dispo (axes scoring v3) au lieu du proxy capé 95 du silver path.
    """
    pool = _pool(req)
    cibles = await _cibles_with_routing(pool, "score_ma", 50, 0)

    def stage_for(ca: float) -> str:
        if ca >= 500_000_000: return "closing"
        if ca >= 100_000_000: return "loi"
        if ca >= 50_000_000: return "dd"
        if ca >= 10_000_000: return "approche"
        return "sourcing"

    deals = []
    for i, c in enumerate(cibles["cibles"]):
        # Filtre les sociétés cessées : pas de M&A possible sur radiation/dissolution.
        if c.get("statut") in ("cesse", "cessée", "C", "RADIE"):
            continue
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


@router.get("/graph/{siren}")
async def graph_for_siren(req: Request, siren: str, depth: int = Query(1, ge=1, le=2)):
    """Graphe réseau autour d'un siren cible — UTILISE EXACTEMENT la même
    logique que /fiche/{siren}.network pour garantir cohérence (Bug M
    rapport QA : Graphe affichait 1 nœud quand Fiche en montrait 6).

    Format : { nodes: [{id, name, type, role, color, score?, ...}],
               links: [{source, target, label, value}] }

    Cache TTL 5 min — bug v6/1.4 (graph p95 4,6s).
    """
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")
    cache_key = f"graph:{siren}:{depth}"
    cached = _gen_cache_get(cache_key, 300.0)
    if cached is not None:
        return cached
    pool = _pool(req)

    # Centre = la cible
    center_row = await _safe(pool.fetchrow(
        """SELECT siren, denomination,
                  COALESCE(em.code_ape, '') AS code_ape,
                  COALESCE(em.adresse_dept, '') AS dept,
                  em.ca_latest, sm.deal_score_raw, sm.tier
           FROM gold.entreprises_master em
           LEFT JOIN gold.scoring_ma sm ON sm.siren = em.siren
           WHERE em.siren = $1::char(9)
           LIMIT 1""",
        siren,
    ), default=None)
    if not center_row:
        # Fallback bronze
        center_row = await _safe(pool.fetchrow(
            """SELECT siren, denomination, code_ape, NULL::numeric AS ca_latest,
                      NULL::int AS deal_score_raw, NULL::text AS tier
               FROM bronze.inpi_formalites_entreprises
               WHERE siren = $1::char(9) LIMIT 1""",
            siren,
        ), default=None)
    if not center_row:
        raise HTTPException(status_code=404, detail=f"siren {siren} introuvable")

    # Co-mandats — Bug M rapport QA v4 : pour des siren cessés (DUFOUR 005650189),
    # silver.inpi_dirigeants.sirens_mandats ne contient QUE les mandats actifs,
    # donc 0 résultats. On délègue désormais à fiche_entreprise.network qui a
    # le bon fallback (gouv API personnes morales, BODACC, etc.) — garantit que
    # /graph et /fiche.network montrent le MÊME réseau.
    try:
        fiche_data = await fiche_entreprise(req, siren)
        fiche_network = fiche_data.get("network") or []
    except Exception:
        fiche_network = []

    # Format network_rows compatible avec le code downstream (siren, denomination, via_dirigeants)
    network_rows = [
        {
            "siren": (str(n.get("siren") or "")).strip(),
            "denomination": n.get("denomination") or "",
            "via_dirigeants": n.get("via_dirigeants") or "co-mandat",
            "n_dirig_communs": int(n.get("n_dirig_communs") or 1),
        }
        for n in fiche_network
        if n.get("siren") and str(n.get("siren")).strip() != siren
    ][:30]

    # Construction graphe
    center_id = f"target-{siren}"
    nodes = [
        {
            "id": center_id,
            "name": center_row.get("denomination") or siren,
            "type": "target",
            "role": "Cible",
            "color": "#a78bfa",
            "siren": siren,
            "score": center_row.get("deal_score_raw"),
            "priority": center_row.get("tier"),
            "sector": center_row.get("code_ape") or None,
            "city": center_row.get("dept") or None,
        }
    ]
    links = []
    seen = {center_id}
    for r in network_rows:
        sib_id = f"company-{r['siren']}"
        if sib_id in seen:
            continue
        seen.add(sib_id)
        nodes.append({
            "id": sib_id,
            "name": r.get("denomination") or str(r.get("siren") or "?"),
            "type": "company",
            "role": "Co-mandat",
            "color": "#60a5fa",
            "siren": str(r.get("siren") or ""),
        })
        links.append({
            "source": center_id,
            "target": sib_id,
            "label": r.get("via_dirigeants") or "co-mandat",
            "value": int(r.get("n_dirig_communs") or 1),
        })

    result = {
        "data": {
            "nodes": nodes,
            "links": links,
            "center_siren": siren,
        }
    }
    _gen_cache_set(cache_key, result)
    return result


@router.get("/graph")
async def graph_global(req: Request, limit: int = Query(50, ge=10, le=200)):
    """Graphe global top cibles M&A — réseau condensé top deal_score
    avec leurs co-mandats principaux. Source : gold.cibles_ma_top.

    Bug M rapport QA : ce endpoint utilise la même structure que
    /graph/{siren} pour garantir cohérence Graph view ↔ Fiche.network.

    Cache TTL 5 min — bug v6/1.4 perf.
    """
    cache_key = f"graph_global:{limit}"
    cached = _gen_cache_get(cache_key, 300.0)
    if cached is not None:
        return cached
    pool = _pool(req)
    if not await _table_exists(pool, "gold", "cibles_ma_top"):
        return {"data": {"nodes": [], "links": []}, "notice": "gold.cibles_ma_top pas matérialisée"}

    rows = await _safe(pool.fetch(
        """SELECT siren, denomination, code_ape, adresse_dept,
                  ca_latest, deal_score_raw, tier
           FROM gold.cibles_ma_top
           WHERE tier IN ('A_HOT', 'B_WARM')
           ORDER BY deal_score_raw DESC NULLS LAST
           LIMIT $1""",
        limit,
    ), default=[])

    nodes = [
        {
            "id": f"target-{r['siren']}",
            "name": r.get("denomination") or str(r['siren']),
            "type": "target",
            "role": "Cible top M&A",
            "color": "#a78bfa" if r.get("tier") == "A_HOT" else "#60a5fa",
            "siren": str(r['siren']),
            "score": r.get("deal_score_raw"),
            "priority": r.get("tier"),
            "sector": r.get("code_ape"),
            "city": r.get("adresse_dept"),
        }
        for r in rows
    ]
    result = {"data": {"nodes": nodes, "links": [], "n_targets": len(nodes)}}
    _gen_cache_set(cache_key, result)
    return result


@router.post("/agent-retry/{source_id}")
async def agent_retry(req: Request, source_id: str):
    """Demande au worker agents-platform de relancer une ingestion bronze.

    Source rapport QA v3 — Bug N : workers les_echos_rss / cfnews_rss en FAILED
    sans bouton retry. Ce endpoint proxie vers agents-platform :8100/ingestion/run/{source_id}
    qui ré-exécute le fetcher pour cette source.

    Ne valide pas le source_id (laisse agents-platform gérer si la source existe).
    Renvoie 200 avec le payload tel quel ou 502 si agents-platform indisponible.
    """
    if not source_id or len(source_id) > 80 or not source_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="source_id invalide")
    import httpx
    import os as _os
    agents_url = _os.environ.get("AGENTS_PLATFORM_URL", "http://agents-platform:8100")
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(f"{agents_url}/ingestion/run/{source_id}")
            return {
                "source_id": source_id,
                "status_code": r.status_code,
                "agents_response": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:500],
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"agents-platform unreachable: {type(e).__name__}")


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
    autres entreprises co-mandatées, SCI patrimoine) + liens.

    Cache TTL 5 min — bug v6/1.4 (graph p95 = 4.6s).
    """
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")
    cache_key = f"network:{siren}"
    cached = _gen_cache_get(cache_key, 300.0)
    if cached is not None:
        return cached
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
           WHERE $1::char(9) = ANY(sirens_mandats)
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

    result = {"nodes": nodes, "links": links}
    _gen_cache_set(cache_key, result)
    return result


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
    # Bug 3.4 rapport QA v4 — colonnes ma_signal_type/sentiment/summary
    # n'existent pas dans silver.press_mentions_matched (introspect confirmé).
    # On les expose en NULL pour rétrocompat front, et on filtre par siren only.
    if signal:
        # Le filtre par signal_type n'est plus possible — silent ignore
        pass
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    # Bug v5/3.4 + v6 — endpoint timeoutait à 30s sur une MV vide ou en
    # refresh long. Cap explicite à 4s pour ne JAMAIS bloquer l'UI : si la
    # table est lente (locks, refresh), on retourne vide avec notice plutôt
    # que de bloquer le chargement de la fiche.
    try:
        rows = await asyncio.wait_for(
            pool.fetch(
                f"""SELECT published_at, source, title, url, denomination, siren,
                           NULL::text AS ma_signal_type, NULL::text AS sentiment,
                           snippet AS summary, match_method, match_score, is_recent
                    FROM silver.press_mentions_matched
                    {where_sql}
                    ORDER BY published_at DESC NULLS LAST
                    LIMIT {int(limit)}""",
                *params,
            ),
            timeout=4.0,
        )
        return {"articles": [_serialize(r) for r in rows]}
    except asyncio.TimeoutError:
        print("[press/recent] timeout 4s — silver.press_mentions_matched probablement en refresh ou lock")
        return {"articles": [], "notice": "press_mentions_matched indisponible (timeout 4s)"}
    except Exception as e:
        # Pas de 500 utilisateur — on retourne empty + notice diagnostique
        print(f"[press/recent] failed: {type(e).__name__}: {e}")
        return {"articles": [], "notice": f"erreur silver.press_mentions_matched: {type(e).__name__}"}


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
    vers Cible avec rowToCible (résilient aux variations).

    Cache TTL 60s — bug v6/1.4 (p95 = 5,6s sur listings).
    """
    # Hash compact des params pour clé de cache
    cache_key = (
        f"cibles:{q}|{dept}|{naf}|{min_score}|{is_pro_ma}|"
        f"{is_asset_rich}|{has_red_flags}|{sort}|{limit}|{offset}"
    )
    cached = _gen_cache_get(cache_key, 60.0)
    if cached is not None:
        return cached

    pool = _pool(req)

    if await _table_exists(pool, "gold", "entreprises_master"):
        try:
            result = await _cibles_from_gold(pool, q, dept, naf, min_score, is_pro_ma, is_asset_rich, has_red_flags, sort, limit, offset)
            _gen_cache_set(cache_key, result)
            return result
        except Exception as e:
            # Si la branche gold pète (colonne manquante après migration partielle, etc),
            # on retombe gracieusement sur silver au lieu de propager 500 au front.
            print(f"[cibles gold] erreur, fallback silver: {type(e).__name__}: {e}")
    result = await _cibles_from_silver(pool, q, dept, naf, min_score, sort, limit, offset)
    _gen_cache_set(cache_key, result)
    return result


async def _cibles_with_routing(pool, sort: str, limit: int, offset: int):
    """Helper bug v6/1.11 — appelé par /dashboard et /pipeline qui n'ont pas
    besoin des filtres q/dept/naf/etc, juste du top N par score_ma.
    Route automatiquement vers gold (axes v3) si dispo, sinon silver fallback.

    Évite que dashboard/pipeline servent des scores capés à 95 alors que
    /cibles sert des scores 78-91 issus de gold.scoring_ma.
    """
    if await _table_exists(pool, "gold", "entreprises_master"):
        try:
            return await _cibles_from_gold(
                pool, None, None, None, None, None, None, None,
                sort, limit, offset,
            )
        except Exception as e:
            print(f"[cibles routing] gold a échoué, fallback silver: {type(e).__name__}: {e}")
    return await _cibles_from_silver(pool, None, None, None, None, sort, limit, offset)


async def _cibles_from_gold(pool, q, dept, naf, min_score, is_pro_ma, is_asset_rich, has_red_flags, sort, limit, offset):
    # Si gold.scoring_ma existe (matérialisée par silver_runner), on l'utilise
    # comme source de vérité pour le score (103 signaux × 12 dimensions).
    # Sinon fallback sur entreprises_master.score_ma (formule heuristique 8
    # signaux). À terme cette branche disparaîtra et entreprises_master sera
    # alimentée par scoring_ma directement.
    # Adapté schema v3 PRO de gold.entreprises_master :
    # - statut → insee_etat_administratif (A/F)
    # - siege_dept → adresse_dept
    # - naf → code_ape
    # - score_ma → pro_ma_score (legacy) / sm.deal_score_raw (v3)
    # - is_pro_ma → has_pro_ma
    # - is_asset_rich → has_holding_patrimoniale
    # - ca_dernier → ca_latest
    # - date_creation → date_immatriculation
    has_scoring = await _table_exists(pool, "gold", "scoring_ma")
    score_join = ""
    score_col = "t.pro_ma_score"
    extra_select = ""
    if has_scoring:
        score_join = " LEFT JOIN gold.scoring_ma sm ON sm.siren = t.siren"
        score_col = "COALESCE(sm.deal_score_raw, sm.score_total, t.pro_ma_score)"
        extra_select = (
            ", sm.transmission_score, sm.attractivity_score, sm.scale_score, "
            "sm.structure_score, sm.tier, sm.deal_percentile, sm.risk_multiplier, "
            "sm.ev_estimated_eur, sm.proxy_margin, sm.sector_multiple"
        )

    # Statut "actif" v3 = insee_etat_administratif != 'F' (F = Fermé/Radié)
    where: list[str] = ["(t.insee_etat_administratif IS NULL OR t.insee_etat_administratif != 'F')"]
    params: list[Any] = []
    if q:
        if q.isdigit() and len(q) == 9:
            params.append(q)
            where.append(f"t.siren = ${len(params)}")
        else:
            params.append(f"%{q}%")
            where.append(f"t.denomination ILIKE ${len(params)}")
    if dept:
        params.append(dept)
        where.append(f"t.adresse_dept = ${len(params)}")
    if naf:
        params.append(f"{naf}%")
        where.append(f"t.code_ape ILIKE ${len(params)}")
    if min_score is not None:
        params.append(min_score)
        if has_scoring:
            where.append(f"COALESCE(sm.deal_score_raw, sm.score_total, t.pro_ma_score) >= ${len(params)}")
        else:
            where.append(f"t.pro_ma_score >= ${len(params)}")
    if is_pro_ma is True:
        where.append("COALESCE(t.has_pro_ma, false) = true")
    if is_asset_rich is True:
        where.append("COALESCE(t.has_holding_patrimoniale, false) = true")
    if has_red_flags is True and has_scoring:
        # Risk haircut > 0 = au moins une pénalité
        where.append("(sm.risk_multiplier IS NOT NULL AND sm.risk_multiplier < 1.0)")
    elif has_red_flags is False and has_scoring:
        where.append("(sm.risk_multiplier IS NULL OR sm.risk_multiplier >= 1.0)")

    # Mapping order_col v3
    order_col = {
        "score_ma": score_col,
        "ca_dernier": "t.ca_latest",
        "date_creation": "t.date_immatriculation",
    }[sort]
    sql = f"""
        SELECT row_to_json(t.*) AS row, {score_col} AS score_ma_resolved{extra_select}
        FROM gold.entreprises_master t
        {score_join}
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
        # Compat ascendante : alias score_ma + statut + naf + siege_dept + ca_dernier
        # depuis les noms v3 de gold.entreprises_master
        v["score_ma"] = r["score_ma_resolved"] if r.get("score_ma_resolved") is not None else v.get("pro_ma_score")
        v.setdefault("statut", "actif" if v.get("insee_etat_administratif") != "F" else "cessé")
        v.setdefault("naf", v.get("code_ape"))
        v.setdefault("siege_dept", v.get("adresse_dept"))
        v.setdefault("ca_dernier", v.get("ca_latest"))
        v.setdefault("date_creation", v.get("date_immatriculation"))
        v.setdefault("is_pro_ma", v.get("has_pro_ma"))
        v.setdefault("is_asset_rich", v.get("has_holding_patrimoniale"))
        # Hydrate les champs scoring v3 (axes + tier + EV) si dispo
        for k in (
            "transmission_score", "attractivity_score", "scale_score", "structure_score",
            "tier", "deal_percentile", "risk_multiplier", "ev_estimated_eur",
            "proxy_margin", "sector_multiple",
        ):
            if k in r and r[k] is not None:
                v[k] = float(r[k]) if k in ("risk_multiplier", "proxy_margin", "sector_multiple", "ev_estimated_eur") else r[k]
        cibles.append(v)
    return {"cibles": cibles, "limit": limit, "offset": offset, "has_more": len(cibles) == limit, "source": "gold", "scoring_v2": has_scoring}


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
    # Floor 1M€ par défaut pour ne pas scanner les 6M inpi_comptes (95% sont
    # des micro-entreprises sans intérêt M&A). min_score plus haut → ca_min plus haut.
    ca_min = max(1_000_000, (min_score - 50) * 200_000) if min_score is not None else 1_000_000
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

    # JOIN conditionnel : silver.entreprises_signals expose naf/forme/ville/dept,
    # mais la table peut ne pas exister encore (silver_bootstrap en cours).
    # On la JOIN seulement si elle existe — sinon les colonnes sont NULL et l'UI
    # affiche un placeholder. Frontend reste sur le contrat silver+.
    has_es = await _table_exists(pool, "silver", "entreprises_signals")
    es_join_clause = "LEFT JOIN silver.entreprises_signals es ON es.siren = lc.siren" if has_es else ""
    es_naf = "es.code_ape" if has_es else "NULL::text"
    es_forme = "es.forme_juridique" if has_es else "NULL::text"
    es_date_creation = "es.date_immatriculation" if has_es else "NULL::date"
    es_cp = "es.adresse_code_postal" if has_es else "NULL::text"
    es_ville = "es.adresse_commune" if has_es else "NULL::text"
    es_dept = "COALESCE(es.adresse_dept, LEFT(es.adresse_code_postal, 2))" if has_es else "NULL::text"

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
        enriched AS (
            SELECT lc.*,
                   {es_naf} AS naf,
                   {es_forme} AS forme_juridique,
                   {es_date_creation} AS date_creation_unite,
                   {es_cp} AS adresse_code_postal,
                   {es_ville} AS ville_sirene,
                   {es_dept} AS dept_sirene,
                   (SELECT b.code_dept FROM silver.bodacc_annonces b
                    WHERE b.siren = lc.siren AND b.code_dept IS NOT NULL
                    ORDER BY b.date_parution DESC LIMIT 1) AS dept_bodacc,
                   (SELECT b.ville FROM silver.bodacc_annonces b
                    WHERE b.siren = lc.siren AND b.ville IS NOT NULL
                    ORDER BY b.date_parution DESC LIMIT 1) AS ville_bodacc
            FROM last_compte lc
            {es_join_clause}
        )
        SELECT siren,
               denomination,
               naf,
               NULL::text AS naf_libelle,
               forme_juridique,
               COALESCE(dept_sirene, dept_bodacc, LEFT(NULLIF(adresse_code_postal, ''), 2)) AS dept,
               COALESCE(ville_sirene, ville_bodacc) AS ville,
               COALESCE(adresse_code_postal, '') AS adresse_code_postal,
               COALESCE(date_creation_unite, date_cloture) AS date_creation,
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
               -- has_compliance_red_flag : on évalue côté Python pour éviter les
               -- erreurs SQL si la colonne sirens_fr n'existe pas en silver.opensanctions
               -- ou si le type ne match pas. Default false ici, override en post-traitement.
               false AS has_compliance_red_flag,
               false AS is_listed,
               -- top_dirigeant_* exposes via /fiche/SIREN (drill-down rapide)
               NULL::text AS top_dirigeant_nom,
               NULL::text AS top_dirigeant_prenom,
               NULL::text AS top_dirigeant_full_name,
               NULL::int AS top_dirigeant_age,
               NULL::int AS top_dirigeant_n_mandats,
               NULL::int AS top_dirigeant_pro_ma_score
        FROM enriched
        WHERE 1=1 {extra_where}
        ORDER BY {order_sql}
        LIMIT {int(limit)} OFFSET {int(offset)}
    """
    try:
        rows = await pool.fetch(sql, *params)
    except Exception as e:
        # Au lieu de 500, on retourne une liste vide avec un flag d'erreur. Le front
        # affiche un état "no results" propre au lieu d'un crash. Trace gardée serveur.
        print(f"[cibles silver fallback] erreur SQL: {type(e).__name__}: {e}")
        return {
            "cibles": [],
            "limit": limit,
            "offset": offset,
            "has_more": False,
            "source": "silver_fallback_error",
            "error": f"{type(e).__name__}: {str(e)[:200]}",
        }

    cibles = [_serialize(r) for r in rows]

    # Enrichissement compliance red flag en best-effort (ne casse pas si la table absente)
    try:
        sirens = [c.get("siren") for c in cibles if c.get("siren")]
        if sirens:
            sanc_rows = await pool.fetch(
                "SELECT DISTINCT siren FROM silver.sanctions WHERE siren = ANY($1::text[])",
                sirens,
            )
            flagged = {r["siren"] for r in sanc_rows}
            for c in cibles:
                if c.get("siren") in flagged:
                    c["has_compliance_red_flag"] = True
    except Exception as e:
        print(f"[cibles] compliance enrichment skipped: {e}")

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


# IMPORTANT : registration EN DERNIER. FastAPI matche en order de registration
# et le pattern /{schema}/{table} catche tout (entreprise/X, network/Y, etc).
# En l'enregistrant après les routes spécifiques (fiche, co-mandats, dashboard,
# pipeline, cibles, press/recent, agent-actions, source-health, _introspect,
# tables), elles sont essayées d'abord.
router.add_api_route("/{schema}/{table}", query_table, methods=["GET"], tags=["datalake"])
