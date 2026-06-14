"""One-shot — enrichit les nœuds Person/Company Neo4j avec le LOBBYING et les
SANCTIONS autour du dirigeant (absents du sync quotidien jusqu'ici).

1. Lobbying (silver.hatvp_lobbying_persons, 434k) : un dirigeant inscrit comme
   représentant d'intérêts (HATVP). Match par siren + nom sur le Person dirigeant
   de la société déclarante.
2. Sanctions société (gold.compliance_red_flags) : pose les drapeaux sanction/
   offshore sur la Company puis les propage aux dirigeants (has_societe_sanctionnee)
   — signal fiable basé sur le siren (vs matching nom-only risqué pour OpenSanctions
   personnes, qui n'ont pas de siren_fr).

Usage : docker exec -w /app demomea-agents-platform python backfill_person_influence.py
"""
from __future__ import annotations

import sys
import time

if "/app" not in sys.path:
    sys.path.insert(0, "/app")

import psycopg
from neo4j import GraphDatabase

from config import settings
from ingestion.neo4j_sync import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

BATCH = 2000

LOBBY_SQL = """
SELECT siren, dirigeant_nom, dirigeant_prenom, denomination,
       categorie_organisation, COALESCE(lobbying_actif, false) AS actif
FROM silver.hatvp_lobbying_persons
WHERE siren IS NOT NULL AND dirigeant_nom IS NOT NULL
"""

LOBBY_CYPHER = """
UNWIND $rows AS row
MATCH (c:Company {siren: row.siren})<-[:IS_DIRIGEANT]-(p:Person)
WHERE toLower(p.nom) = toLower(row.nom)
SET p.is_lobbyist = true,
    p.lobbying_actif = row.actif,
    p.lobby_organisation = row.denomination,
    p.lobby_categorie = row.categorie
"""

SANCTION_SQL = """
SELECT siren,
       COALESCE(has_sanction, false)        AS has_sanction,
       COALESCE(has_cnil_sanction, false)   AS has_cnil,
       COALESCE(has_dgccrf_sanction, false) AS has_dgccrf,
       COALESCE(has_offshore_link, false)   AS has_offshore,
       COALESCE(risk_score, 0)              AS risk_score
FROM gold.compliance_red_flags
WHERE has_sanction OR has_cnil_sanction OR has_dgccrf_sanction OR has_offshore_link
"""

SANCTION_COMPANY_CYPHER = """
UNWIND $rows AS row
MATCH (c:Company {siren: row.siren})
SET c.has_sanction = row.has_sanction,
    c.has_cnil_sanction = row.has_cnil,
    c.has_dgccrf_sanction = row.has_dgccrf,
    c.has_offshore_link = row.has_offshore,
    c.compliance_risk_score = row.risk_score
"""

# Propage le drapeau aux dirigeants des sociétés sanctionnées
SANCTION_PROPAGATE_CYPHER = """
MATCH (c:Company)<-[:IS_DIRIGEANT]-(p:Person)
WHERE c.has_sanction = true OR c.has_cnil_sanction = true
   OR c.has_dgccrf_sanction = true OR c.has_offshore_link = true
WITH p, count(c) AS n
SET p.has_societe_sanctionnee = true, p.n_societes_sanctionnees = n
"""


def main() -> None:
    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def flush(cypher: str, rows: list[dict]) -> int:
        if not rows:
            return 0
        with driver.session() as s:
            return s.run(cypher, rows=rows).consume().counters.properties_set

    # ─── 1. Lobbying ───
    lobby_props = 0
    batch: list[dict] = []
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor(name="bf_lobby") as cur:
            cur.itersize = 10000
            cur.execute(LOBBY_SQL)
            for siren, nom, prenom, deno, cat, actif in cur:
                batch.append({"siren": siren, "nom": nom, "denomination": deno,
                              "categorie": cat, "actif": bool(actif)})
                if len(batch) >= BATCH:
                    lobby_props += flush(LOBBY_CYPHER, batch); batch = []
            lobby_props += flush(LOBBY_CYPHER, batch)
    print(f"[lobbying] {lobby_props} props set ({int(time.time()-t0)}s)", flush=True)

    # ─── 2. Sanctions société + propagation dirigeant ───
    sanc_props = 0
    batch = []
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor(name="bf_sanc") as cur:
            cur.itersize = 10000
            cur.execute(SANCTION_SQL)
            for siren, hs, hc, hd, ho, risk in cur:
                batch.append({"siren": siren, "has_sanction": bool(hs), "has_cnil": bool(hc),
                              "has_dgccrf": bool(hd), "has_offshore": bool(ho),
                              "risk_score": int(risk or 0)})
                if len(batch) >= BATCH:
                    sanc_props += flush(SANCTION_COMPANY_CYPHER, batch); batch = []
            sanc_props += flush(SANCTION_COMPANY_CYPHER, batch)
    print(f"[sanctions société] {sanc_props} props set ({int(time.time()-t0)}s)", flush=True)

    with driver.session() as s:
        prop = s.run(SANCTION_PROPAGATE_CYPHER).consume().counters.properties_set
    print(f"[sanctions → dirigeants] {prop} props set ({int(time.time()-t0)}s)", flush=True)

    driver.close()
    print(f"DONE influence backfill en {int(time.time()-t0)}s", flush=True)


if __name__ == "__main__":
    main()
