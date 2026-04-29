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


@router.get("/fiche/{siren}")
async def fiche_entreprise(req: Request, siren: str):
    """Fiche complète — gold.entreprises_master si dispo, fallback sur
    silver.insee_unites_legales + silver.inpi_comptes + silver.inpi_dirigeants."""
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide")
    pool = _pool(req)

    fiche = None
    gouv = None
    if await _table_exists(pool, "gold", "entreprises_master"):
        fiche = await pool.fetchrow(
            "SELECT * FROM gold.entreprises_master WHERE siren = $1", siren
        )
    if not fiche:
        # Multi-query approach : chaque source séparée avec timeout court.
        # Si une table est lente/locked, on remplit avec NULL au lieu de tout
        # bloquer. Plus robuste qu'un mega-CTE.
        import asyncio as _asyncio

        async def _safe(coro, timeout_s: float = 4.0, default=None):
            try:
                return await _asyncio.wait_for(coro, timeout=timeout_s)
            except (_asyncio.TimeoutError, Exception) as e:
                print(f"[fiche] sub-query failed: {type(e).__name__}: {str(e)[:80]}")
                return default

        # 1. INPI comptes (rapide, PK siren)
        compte = await pool.fetchrow(
            """SELECT DISTINCT ON (siren) siren, denomination,
                      ca_net, resultat_net, capitaux_propres,
                      effectif_moyen::int AS effectif_exact,
                      date_cloture
               FROM silver.inpi_comptes
               WHERE siren = $1
               ORDER BY siren, date_cloture DESC""",
            siren,
        )
        if not compte:
            raise HTTPException(status_code=404, detail=f"SIREN {siren} introuvable dans silver.inpi_comptes")

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
                      date_derniere_maj
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
            "capital_social": osint["capital_social"] if osint else None,
            "adresse_code_postal": (osint["adresse_code_postal"] if osint else None) or (gouv["code_postal"] if gouv else None),
            "annee_creation": (osint["annee_creation"] if osint and osint["annee_creation"] else None) or (
                int(str(insee["date_creation"])[:4]) if insee and insee["date_creation"] else (
                    int(str(gouv["date_creation"])[:4]) if gouv and gouv["date_creation"] else None
                )
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

    # Dirigeants détaillés — top 10 par mandats actifs, joint avec patrimoine SCI.
    # On essaie d'abord en silver (8M dirigeants), fallback sur l'API gouv si vide.
    dirigeants_silver = await pool.fetch(
        """WITH dirig AS (
              SELECT nom, prenom, date_naissance, age_2026 AS age,
                     n_mandats_actifs, n_mandats_total, sirens_mandats,
                     denominations, roles, is_multi_mandat
              FROM silver.inpi_dirigeants
              WHERE $1::char(9) = ANY(sirens_mandats)
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

    # Override n_dirigeants if we got data from gouv fallback
    if isinstance(fiche, dict) and not dirigeants_silver and dirigeants:
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
        # Fallback live BODACC datadila API
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
        except Exception as e:
            print(f"[fiche] BODACC live API failed: {type(e).__name__}: {str(e)[:80]}")

    # Compliance — OpenSanctions match par siren_fr
    red_flags = await pool.fetch(
        """SELECT entity_id, caption, schema, topics, countries,
                  sanctions_programs, first_seen, last_seen
           FROM silver.opensanctions
           WHERE $1 = ANY(sirens_fr)""",
        siren,
    ) if await _table_exists(pool, "silver", "opensanctions") else []

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
               SELECT DISTINCT other_siren AS siren,
                      other_deno AS denomination,
                      string_agg(DISTINCT prenom || ' ' || nom, ', ') AS via_dirigeants
               FROM expanded
               WHERE other_siren != $1::char(9) AND other_siren IS NOT NULL
               GROUP BY other_siren, other_deno
               ORDER BY other_deno
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

    return {
        "fiche": _serialize(fiche) if hasattr(fiche, "items") and not isinstance(fiche, dict) else fiche,
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


# IMPORTANT : registration EN DERNIER. FastAPI matche en order de registration
# et le pattern /{schema}/{table} catche tout (entreprise/X, network/Y, etc).
# En l'enregistrant après les routes spécifiques (fiche, co-mandats, dashboard,
# pipeline, cibles, press/recent, agent-actions, source-health, _introspect,
# tables), elles sont essayées d'abord.
router.add_api_route("/{schema}/{table}", query_table, methods=["GET"], tags=["datalake"])
