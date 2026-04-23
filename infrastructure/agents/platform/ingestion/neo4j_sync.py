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


def _person_uid(nom: str, prenom: str, dn: str) -> str:
    import unicodedata, re
    def _slug(s):
        if not s:
            return ""
        s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode()
        return re.sub(r"[^a-zA-Z0-9]", "", s).lower()
    return hashlib.sha1(f"{_slug(nom)}|{_slug(prenom)}|{dn or ''}".encode()).hexdigest()[:40]


def _ensure_schema(driver):
    with driver.session() as s:
        s.run("CREATE CONSTRAINT company_siren IF NOT EXISTS FOR (c:Company) REQUIRE c.siren IS UNIQUE")
        s.run("CREATE CONSTRAINT person_uid   IF NOT EXISTS FOR (p:Person)  REQUIRE p.uid   IS UNIQUE")
        s.run("CREATE INDEX person_nom IF NOT EXISTS FOR (p:Person) ON (p.nom)")
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
SET p.nom = row.nom, p.prenoms = row.prenoms, p.date_naissance = row.date_naissance
WITH p, row
MATCH (c:Company {siren: row.siren})
MERGE (p)-[r:IS_DIRIGEANT]->(c)
SET r.role = row.role, r.actif = row.actif, r.individu_role = row.individu_role
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
                prenom = (prenoms or [""])[0]
                params.append({
                    "uid": _person_uid(nom, prenom, dn),
                    "nom": nom, "prenoms": prenoms or [], "date_naissance": dn,
                    "siren": siren, "role": role_ent, "actif": bool(actif),
                    "individu_role": individu_role,
                })
            with driver.session() as s:
                for j in range(0, len(params), BATCH):
                    s.run(MERGE_PERSON_EDGE, rows=params[j:j + BATCH])
            n_persons += len(params)

    with driver.session() as s:
        cnt_c = s.run("MATCH (c:Company) RETURN count(c) AS n").single()["n"]
        cnt_p = s.run("MATCH (p:Person) RETURN count(p) AS n").single()["n"]
        cnt_e = s.run("MATCH ()-[r:IS_DIRIGEANT]->() RETURN count(r) AS n").single()["n"]
    driver.close()

    result = {
        "companies_loaded": n_companies,
        "persons_loaded": n_persons,
        "graph_companies": cnt_c,
        "graph_persons": cnt_p,
        "graph_edges": cnt_e,
        "duration_s": round(time.time() - t0, 1),
    }
    log.info("[neo4j_sync] %s", result)
    return result
