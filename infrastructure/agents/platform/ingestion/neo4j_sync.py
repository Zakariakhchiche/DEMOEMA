"""Neo4j graph sync — charge les dirigeants/companies depuis Postgres vers Neo4j.

Appelé par engine.py via un job scheduler quotidien (cron 04:00 Paris).
Utilise une materialized view silver (idéalement silver.inpi_dirigeants) comme
source si disponible, sinon fallback sur bronze.inpi_formalites_personnes/entreprises.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time

import psycopg

from config import settings

log = logging.getLogger("demoema.neo4j_sync")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://demomea-neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "demoema_neo4j_pass")

COMPANIES_LIMIT = int(os.environ.get("NEO4J_COMPANIES_LIMIT", "10000"))
BATCH = int(os.environ.get("NEO4J_BATCH", "500"))


def _slug(s: str) -> str:
    """Slug ASCII lowercase pour la composition du person_uid."""
    import unicodedata, re
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]", "", s).lower()


def _person_uid(nom: str, prenoms: list[str] | str | None, dn: str) -> str:
    """UID stable pour un dirigeant individu.

    L'ordre des prénoms dans `bronze.inpi_formalites_personnes.individu_prenoms`
    n'est pas garanti stable entre dumps INPI. On hashait avant sur prenoms[0],
    ce qui produisait des UID différents selon l'ordre fourni → doublons silent
    Neo4j (deux nodes Person pour la même personne).

    Désormais : hash sur la TUPLE TRIÉE des prénoms, normalisée. Stable peu
    importe l'ordre upstream.

    Compat : accepte aussi un str (legacy callers) — sera traité comme [str].
    """
    if isinstance(prenoms, str):
        prenoms_list = [prenoms]
    else:
        prenoms_list = list(prenoms or [])
    canonical_prenoms = "|".join(sorted(_slug(p) for p in prenoms_list if p))
    return hashlib.sha1(
        f"{_slug(nom)}|{canonical_prenoms}|{dn or ''}".encode()
    ).hexdigest()[:40]


def _ensure_schema(driver):
    with driver.session() as s:
        s.run("CREATE CONSTRAINT company_siren IF NOT EXISTS FOR (c:Company) REQUIRE c.siren IS UNIQUE")
        s.run("CREATE CONSTRAINT person_uid   IF NOT EXISTS FOR (p:Person)  REQUIRE p.uid   IS UNIQUE")
        s.run("CREATE INDEX person_nom IF NOT EXISTS FOR (p:Person) ON (p.nom)")
        s.run("CREATE INDEX person_full_name IF NOT EXISTS FOR (p:Person) ON (p.full_name)")
        s.run("CREATE INDEX company_forme IF NOT EXISTS FOR (c:Company) ON (c.forme_juridique)")


COMPANY_QUERY = """
SELECT siren, denomination, forme_juridique,
       COALESCE(montant_capital, 0) AS capital,
       code_ape,
       to_char(date_immatriculation, 'YYYY-MM-DD') AS date_immat,
       adresse_code_postal
FROM bronze.inpi_formalites_entreprises
WHERE forme_juridique IN ('5710','5720','5730','5485','5499','5505','5510','5515','5520','5530','5540','5599',
                          '5385','5308','5306','5202','5203')
  AND COALESCE(montant_capital, 0) >= 500000
ORDER BY montant_capital DESC NULLS LAST
LIMIT %s
"""

PERSON_QUERY = """
SELECT p.siren, p.individu_nom, p.individu_prenoms, p.individu_date_naissance,
       p.role_entreprise, p.actif, p.individu_role
FROM bronze.inpi_formalites_personnes p
WHERE p.siren = ANY(%s)
  AND p.type_de_personne = 'INDIVIDU'
  AND p.individu_nom IS NOT NULL
"""

MERGE_COMPANY = """
UNWIND $rows AS row
MERGE (c:Company {siren: row.siren})
SET c.denomination = row.denomination,
    c.forme_juridique = row.forme_juridique,
    c.capital = row.capital,
    c.code_ape = row.code_ape,
    c.date_immat = row.date_immat,
    c.code_postal = row.code_postal
"""

MERGE_PERSON_EDGE = """
UNWIND $rows AS row
MERGE (p:Person {uid: row.uid})
SET p.nom = row.nom,
    p.prenoms = row.prenoms,
    p.prenom = row.prenom,
    p.full_name = row.full_name,
    p.date_naissance = row.date_naissance
WITH p, row
MATCH (c:Company {siren: row.siren})
MERGE (p)-[r:IS_DIRIGEANT]->(c)
SET r.role = row.role, r.actif = row.actif, r.individu_role = row.individu_role
"""

# Compliance enrichment — sync gold.entreprises_master compliance flags
# into Company nodes, then propagate to Person via aggregate.
# Permet de filtrer le graphe par compliance (ex: "show all Companies in RJ
# in the 75 dept"). Cron quotidien après le rebuild.
COMPLIANCE_COMPANY_QUERY = """
WITH proc AS (
  SELECT siren,
         max(date_parution) AS last_procedure_date,
         (array_agg(type_cession ORDER BY date_parution DESC))[1] AS last_procedure_nature,
         bool_or(date_parution >= now()::date - interval '36 months') AS has_procedure_collective_active
  FROM silver.cession_events
  WHERE siren IS NOT NULL
    AND type_cession IN ('procedure_collective', 'conciliation', 'retablissement')
  GROUP BY siren
)
SELECT em.siren,
       COALESCE(p.has_procedure_collective_active, FALSE) AS has_procedure_collective_active,
       to_char(p.last_procedure_date, 'YYYY-MM-DD') AS last_procedure_date,
       p.last_procedure_nature,
       COALESCE(em.has_late_filing, FALSE) AS has_late_filing,
       COALESCE(em.has_dirigeant_senior, FALSE) AS has_dirigeant_senior,
       COALESCE(em.has_pro_ma, FALSE) AS has_pro_ma,
       COALESCE(em.pro_ma_score, 0) AS pro_ma_score
FROM gold.entreprises_master em
LEFT JOIN proc p ON p.siren = em.siren
WHERE p.siren IS NOT NULL
   OR em.has_late_filing IS NOT NULL
   OR em.has_dirigeant_senior IS NOT NULL
"""

MERGE_COMPANY_COMPLIANCE = """
UNWIND $rows AS row
MATCH (c:Company {siren: row.siren})
SET c.has_procedure_collective_active = row.has_procedure_collective_active,
    c.last_procedure_date = row.last_procedure_date,
    c.last_procedure_nature = row.last_procedure_nature,
    c.has_late_filing = row.has_late_filing,
    c.has_dirigeant_senior = row.has_dirigeant_senior,
    c.has_pro_ma = row.has_pro_ma,
    c.pro_ma_score = row.pro_ma_score
"""

# Propagation Company → Person : approche restreinte pour rester sous le
# memory budget Neo4j (16.8 GiB transaction limit). On part des Companies
# en procédure (4k max) puis on remonte vers les Persons connectés.
# Itère donc sur ~4k Companies × N persons (jamais 7.9M Persons d'un coup).
# Persons non connectés gardent has_mandat_en_procedure = NULL (=false côté
# query layer).
PROPAGATE_PERSON_COMPLIANCE = """
MATCH (c:Company {has_procedure_collective_active: true})<-[:IS_DIRIGEANT]-(p:Person)
WITH p, count(DISTINCT c) AS n_proc
SET p.has_mandat_en_procedure = true,
    p.n_mandats_en_procedure = n_proc
"""

# Reset des Persons qui avaient un flag mais dont aucune company associée
# n'est plus en procédure (boîtes sorties de procédure). Borné par
# has_mandat_en_procedure = true → set restreint.
RESET_PERSON_COMPLIANCE = """
MATCH (p:Person {has_mandat_en_procedure: true})
WHERE NOT (p)-[:IS_DIRIGEANT]->(:Company {has_procedure_collective_active: true})
SET p.has_mandat_en_procedure = false,
    p.n_mandats_en_procedure = 0
"""


# ─── Priority 2 — graphe d'OPPORTUNITÉ (killer feature pré-cession) ───
# 1. Santé financière / détresse sur Company (ratios silver.entreprises_signals).
FINANCIALS_COMPANY_QUERY = """
SELECT btrim(siren) AS siren,
       financial_health_tier,
       round(debt_to_ebitda::numeric, 3)::float8 AS debt_to_ebitda,
       round(ebitda_margin::numeric, 4)::float8 AS ebitda_margin,
       COALESCE(has_negative_equity, FALSE) AS has_negative_equity,
       COALESCE(has_high_leverage, FALSE) AS has_high_leverage,
       COALESCE(has_negative_ebitda, FALSE) AS has_negative_ebitda,
       COALESCE(has_revenue_decline, FALSE) AS has_revenue_decline
FROM silver.entreprises_signals
WHERE siren IS NOT NULL
"""

MERGE_COMPANY_FINANCIALS = """
UNWIND $rows AS row
MATCH (c:Company {siren: row.siren})
SET c.financial_health_tier = row.financial_health_tier,
    c.debt_to_ebitda = toFloat(row.debt_to_ebitda),
    c.ebitda_margin = toFloat(row.ebitda_margin),
    c.has_negative_equity = row.has_negative_equity,
    c.has_high_leverage = row.has_high_leverage,
    c.has_negative_ebitda = row.has_negative_ebitda,
    c.has_revenue_decline = row.has_revenue_decline,
    c.is_distressed = (row.has_negative_equity OR row.has_high_leverage
                       OR row.has_negative_ebitda OR row.has_revenue_decline)
"""

# 2. Arêtes A_CEDE (serial sellers) : sociétés ayant subi une cession/vente 36m.
CESSION_QUERY = """
SELECT btrim(siren) AS siren,
       max(date_parution)::text AS last_cession_date,
       count(*)::int AS n_cessions,
       (array_agg(DISTINCT familleavis_lib))[1] AS cession_type
FROM silver.bodacc_annonces
WHERE siren IS NOT NULL
  AND (familleavis_lib ILIKE '%cession%' OR familleavis_lib ILIKE '%vente%')
  AND date_parution > (now() - interval '36 months')
GROUP BY siren
"""

# Marque la société + crée A_CEDE depuis chacun de ses dirigeants (idempotent).
MERGE_CESSION_EDGES = """
UNWIND $rows AS row
MATCH (c:Company {siren: row.siren})
SET c.has_cession_recente = true,
    c.last_cession_date = row.last_cession_date,
    c.n_cessions_36m = row.n_cessions
WITH c, row
MATCH (p:Person)-[:IS_DIRIGEANT]->(c)
MERGE (p)-[r:A_CEDE]->(c)
SET r.last_date = row.last_cession_date,
    r.n_cessions = row.n_cessions,
    r.type = row.cession_type
"""

# Finalize : vendeur en série = >= 2 sociétés cédées distinctes.
MARK_SERIAL_SELLERS = """
MATCH (p:Person)-[:A_CEDE]->(c:Company)
WITH p, count(DISTINCT c) AS n_cedees
SET p.n_societes_cedees = n_cedees,
    p.is_serial_seller = (n_cedees >= 2)
"""


async def run_neo4j_rebuild() -> dict:
    """Scheduled job: rebuild Neo4j graph from current Postgres state."""
    try:
        from neo4j import GraphDatabase
    except ImportError as e:
        log.warning("neo4j driver not installed: %s", e)
        return {"error": "neo4j driver missing", "detail": str(e)}

    if not settings.database_url:
        return {"error": "no database_url"}

    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
    except Exception as e:
        log.warning("neo4j unreachable: %s", e)
        return {"error": "neo4j unreachable", "detail": str(e)}

    _ensure_schema(driver)

    n_companies = 0
    n_persons = 0

    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        cur.execute(COMPANY_QUERY, (COMPANIES_LIMIT,))
        rows = cur.fetchall()
        sirens = [r[0] for r in rows]
        with driver.session() as s:
            for i in range(0, len(rows), BATCH):
                chunk = rows[i:i + BATCH]
                params = [
                    {"siren": r[0], "denomination": r[1], "forme_juridique": r[2],
                     "capital": float(r[3] or 0), "code_ape": r[4], "date_immat": r[5],
                     "code_postal": r[6]}
                    for r in chunk
                ]
                s.run(MERGE_COMPANY, rows=params)
                n_companies += len(params)

        S_CHUNK = 5000
        for i in range(0, len(sirens), S_CHUNK):
            cur.execute(PERSON_QUERY, (sirens[i:i + S_CHUNK],))
            prows = cur.fetchall()
            params = []
            for (siren, nom, prenoms, dn, role_ent, actif, individu_role) in prows:
                prenoms_list = list(prenoms or [])
                # `prenom` : 1er prénom pour l'affichage (caption Browser).
                # `uid` : hash sur la TOTALITÉ des prénoms TRIÉS (cf _person_uid)
                # — stable même si INPI réordonne le tableau entre dumps.
                prenom_display = prenoms_list[0] if prenoms_list else ""
                full_name = " ".join(part for part in (prenom_display, nom) if part).strip()
                params.append({
                    "uid": _person_uid(nom, prenoms_list, dn),
                    "nom": nom, "prenoms": prenoms_list, "prenom": prenom_display,
                    "full_name": full_name,
                    "date_naissance": dn,
                    "siren": siren, "role": role_ent, "actif": bool(actif),
                    "individu_role": individu_role,
                })
            with driver.session() as s:
                for j in range(0, len(params), BATCH):
                    s.run(MERGE_PERSON_EDGE, rows=params[j:j + BATCH])
            n_persons += len(params)

    # Cleanup orphans : Persons sans IS_DIRIGEANT — créés par les anciens
    # uids (avant la fix sorted prenoms) qui ne sont plus mergés. À la fin
    # du rebuild, tout dirigeant légitime a au moins un IS_DIRIGEANT vers
    # une des companies présentes. Les autres sont des duplicates à purger.
    n_orphans = 0
    with driver.session() as s:
        deleted = s.run(
            "MATCH (p:Person) WHERE NOT (p)-[:IS_DIRIGEANT]->() "
            "WITH p LIMIT 50000 DETACH DELETE p RETURN count(*) AS n"
        ).single()
        n_orphans = deleted["n"] if deleted else 0
        if n_orphans > 0:
            log.info("[neo4j_sync] cleanup: deleted %d orphan Person nodes", n_orphans)

    # Enrichment compliance — sync gold.entreprises_master flags vers Neo4j.
    # Permet de filtrer le graphe par compliance (recherche graphique). Le coût
    # est marginal : SELECT puis MERGE en batch sur les sirens déjà en graphe.
    n_compliance_companies = 0
    n_compliance_persons = 0
    try:
        with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
            cur.execute(COMPLIANCE_COMPANY_QUERY)
            comp_rows = cur.fetchall()
            params = [
                {
                    "siren": r[0],
                    "has_procedure_collective_active": bool(r[1]) if r[1] is not None else None,
                    "last_procedure_date": r[2],
                    "last_procedure_nature": r[3],
                    "has_late_filing": bool(r[4]),
                    "has_dirigeant_senior": bool(r[5]),
                    "has_pro_ma": bool(r[6]),
                    "pro_ma_score": int(r[7] or 0),
                }
                for r in comp_rows
            ]
            with driver.session() as s:
                for i in range(0, len(params), BATCH):
                    s.run(MERGE_COMPANY_COMPLIANCE, rows=params[i:i + BATCH])
                    n_compliance_companies += min(BATCH, len(params) - i)
                # Propagation Company → Person : restreinte aux Persons connectés
                # à au moins 1 Company en procédure (≪ 7.9M Persons totaux).
                p_result = s.run(PROPAGATE_PERSON_COMPLIANCE).consume()
                n_compliance_persons = p_result.counters.properties_set
                # Reset des Persons qui étaient flag=true mais dont aucune
                # company associée n'est plus en procédure.
                r_result = s.run(RESET_PERSON_COMPLIANCE).consume()
                n_compliance_persons += r_result.counters.properties_set
        log.info(
            "[neo4j_sync] compliance enrichment: %d companies, %d person props set",
            n_compliance_companies, n_compliance_persons,
        )
    except Exception as e:
        log.warning("[neo4j_sync] compliance enrichment failed: %s", e)

    # ─── Priority 2 : santé financière / détresse sur Company ───
    n_fin_companies = 0
    try:
        with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
            cur.execute(FINANCIALS_COMPANY_QUERY)
            cols = [d.name for d in cur.description]
            fin_rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        with driver.session() as s:
            for i in range(0, len(fin_rows), BATCH):
                s.run(MERGE_COMPANY_FINANCIALS, rows=fin_rows[i:i + BATCH])
                n_fin_companies += min(BATCH, len(fin_rows) - i)
        log.info("[neo4j_sync] financials enrichment: %d companies", n_fin_companies)
    except Exception as e:
        log.warning("[neo4j_sync] financials enrichment failed: %s", e)

    # ─── Priority 2 : arêtes A_CEDE (serial sellers) ───
    n_cession_companies = 0
    n_serial_sellers = 0
    try:
        with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
            cur.execute(CESSION_QUERY)
            cols = [d.name for d in cur.description]
            ces_rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        with driver.session() as s:
            for i in range(0, len(ces_rows), BATCH):
                s.run(MERGE_CESSION_EDGES, rows=ces_rows[i:i + BATCH])
                n_cession_companies += min(BATCH, len(ces_rows) - i)
            s.run(MARK_SERIAL_SELLERS).consume()
            sr = s.run(
                "MATCH (p:Person {is_serial_seller: true}) RETURN count(p) AS n"
            ).single()
            n_serial_sellers = sr["n"] if sr else 0
        log.info("[neo4j_sync] cession enrichment: %d companies cédées, %d serial sellers",
                 n_cession_companies, n_serial_sellers)
    except Exception as e:
        log.warning("[neo4j_sync] cession enrichment failed: %s", e)

    with driver.session() as s:
        cnt_c = s.run("MATCH (c:Company) RETURN count(c) AS n").single()["n"]
        cnt_p = s.run("MATCH (p:Person) RETURN count(p) AS n").single()["n"]
        cnt_e = s.run("MATCH ()-[r:IS_DIRIGEANT]->() RETURN count(r) AS n").single()["n"]
        cnt_proc = s.run(
            "MATCH (c:Company) WHERE c.has_procedure_collective_active = TRUE "
            "RETURN count(c) AS n"
        ).single()["n"]
        cnt_p_risk = s.run(
            "MATCH (p:Person) WHERE p.has_mandat_en_procedure = TRUE "
            "RETURN count(p) AS n"
        ).single()["n"]
    driver.close()

    result = {
        "companies_loaded": n_companies,
        "persons_loaded": n_persons,
        "orphans_deleted": n_orphans,
        "compliance_companies": n_compliance_companies,
        "compliance_persons_props": n_compliance_persons,
        "graph_companies": cnt_c,
        "graph_persons": cnt_p,
        "graph_edges": cnt_e,
        "graph_companies_in_procedure": cnt_proc,
        "graph_persons_with_mandat_in_procedure": cnt_p_risk,
        "duration_s": round(time.time() - t0, 1),
    }
    log.info("[neo4j_sync] %s", result)
    return result
