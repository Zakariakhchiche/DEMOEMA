"""Rebuild COMPLET du côté Person du graphe Neo4j — identité unifiée.

Corrige le double schéma d'uid (bulk loader prenoms[0] vs sync prénoms triés).
Conserve les nœuds Company (et leur enrichissement scoring), wipe les Person
(+ leurs arêtes IS_DIRIGEANT/CO_MANDATE/A_CEDE) puis recharge persons + arêtes
IS_DIRIGEANT depuis bronze.inpi_formalites_personnes avec :
  - uid CANONIQUE (_person_uid : prénoms triés complets),
  - actif AGRÉGÉ par (personne, siren) = bool_or (actif si au moins un dépôt l'est).

⚠️ Destructif (wipe Person). À lancer supervisé, de préférence de nuit.
Après ce script, relancer les enrichissements :
  - CO_MANDATE : scripts/neo4j/build_co_mandates_full.py
  - cessions / compliance / financials : run_neo4j_rebuild()
  - lobbying / sanctions : backfill_person_influence.py

Usage : docker exec -w /app demomea-agents-platform python scripts/neo4j/neo4j_loader_full.py
(ou copié à la racine /app selon le montage).
"""
from __future__ import annotations

import sys
import time

if "/app" not in sys.path:
    sys.path.insert(0, "/app")

import psycopg
from neo4j import GraphDatabase

from config import settings
from ingestion.neo4j_sync import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, _person_uid

BATCH = 5000

# Pass A — TOUTES les sociétés (univers complet, sans filtre capital/forme).
# 1 ligne par siren (DISTINCT ON, on garde la plus récemment immatriculée).
COMPANY_SQL = """
SELECT DISTINCT ON (siren)
       siren, denomination, forme_juridique,
       COALESCE(montant_capital, 0) AS capital, code_ape,
       to_char(date_immatriculation, 'YYYY-MM-DD') AS date_immat,
       adresse_code_postal
FROM bronze.inpi_formalites_entreprises
WHERE siren IS NOT NULL
ORDER BY siren, date_immatriculation DESC NULLS LAST
"""

MERGE_COMPANY = """
UNWIND $rows AS row
MERGE (c:Company {siren: row.siren})
SET c.denomination = coalesce(row.denomination, c.denomination),
    c.forme_juridique = coalesce(row.forme_juridique, c.forme_juridique),
    c.capital = row.capital,
    c.code_ape = coalesce(row.code_ape, c.code_ape),
    c.date_immat = coalesce(row.date_immat, c.date_immat),
    c.code_postal = coalesce(row.code_postal, c.code_postal)
"""

# Persons + statut agrégé par (personne, siren). bool_or(actif) = actif si au
# moins un dépôt INPI le marque actif (hash agg ~90s sur 13M, pas de tri).
PERSON_SQL = """
SELECT siren, individu_nom, individu_prenoms, individu_date_naissance,
       bool_or(actif) AS actif,
       (array_agg(individu_role) FILTER (WHERE individu_role IS NOT NULL))[1] AS role
FROM bronze.inpi_formalites_personnes
WHERE type_de_personne = 'INDIVIDU'
  AND individu_nom IS NOT NULL
  AND siren IS NOT NULL
GROUP BY siren, individu_nom, individu_prenoms, individu_date_naissance
"""

WIPE_PERSONS = "MATCH (p:Person) CALL (p) { DETACH DELETE p } IN TRANSACTIONS OF 10000 ROWS"

MERGE_PERSON_EDGE = """
UNWIND $rows AS row
MERGE (p:Person {uid: row.uid})
  ON CREATE SET p.nom = row.nom, p.prenoms = row.prenoms,
                p.prenom = row.prenom, p.full_name = row.full_name,
                p.date_naissance = row.date_naissance
MERGE (c:Company {siren: row.siren})
MERGE (p)-[r:IS_DIRIGEANT]->(c)
SET r.actif = row.actif, r.individu_role = row.role
"""


def main() -> None:
    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()

    # ─── 0. Pass A : charge TOUTES les sociétés (univers complet, additif) ───
    import os
    if os.environ.get("SKIP_COMPANIES"):
        print("[1/3] load ALL companies… SKIPPED (SKIP_COMPANIES set)", flush=True)
    else:
        print("[1/3] load ALL companies…", flush=True)
        nco = 0
        cbatch: list[dict] = []
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor(name="loader_companies") as cur:
                cur.itersize = 20000
                cur.execute(COMPANY_SQL)
                for siren, deno, forme, cap, ape, dimm, cp in cur:
                    cbatch.append({"siren": siren, "denomination": deno, "forme_juridique": forme,
                                   "capital": float(cap or 0), "code_ape": ape,
                                   "date_immat": dimm, "code_postal": cp})
                    if len(cbatch) >= BATCH:
                        with driver.session() as s:
                            s.run(MERGE_COMPANY, rows=cbatch).consume()
                        nco += len(cbatch); cbatch = []
                        if nco % 1000000 == 0:
                            print(f"  ... {nco} sociétés ({int(time.time()-t0)}s)", flush=True)
                if cbatch:
                    with driver.session() as s:
                        s.run(MERGE_COMPANY, rows=cbatch).consume()
                    nco += len(cbatch)
        print(f"  companies loaded: {nco} ({int(time.time()-t0)}s)", flush=True)

    # ─── 1. Wipe Person (+ arêtes) en transactions batch ───
    print("[2/3] wipe Person nodes…", flush=True)
    with driver.session() as s:
        s.run(WIPE_PERSONS).consume()
    print(f"  wipe done ({int(time.time()-t0)}s)", flush=True)

    # ─── 2. Reload persons + IS_DIRIGEANT (uid canonique, actif agrégé) ───
    print("[3/3] reload persons + edges…", flush=True)
    total = 0
    batch: list[dict] = []

    def flush(rows: list[dict]) -> None:
        if rows:
            with driver.session() as s:
                s.run(MERGE_PERSON_EDGE, rows=rows).consume()

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor(name="loader_full") as cur:
            cur.itersize = 20000
            cur.execute(PERSON_SQL)
            for siren, nom, prenoms, dn, actif, role in cur:
                pl = list(prenoms or [])
                prenom0 = pl[0] if pl else ""
                full = " ".join(x for x in (prenom0, nom) if x).strip()
                batch.append({
                    "uid": _person_uid(nom, pl, dn),
                    "nom": nom, "prenoms": pl, "prenom": prenom0,
                    "full_name": full, "date_naissance": dn,
                    "siren": siren, "actif": bool(actif), "role": role,
                })
                if len(batch) >= BATCH:
                    flush(batch); total += len(batch); batch = []
                    if total % 500000 == 0:
                        print(f"  ... {total} arêtes ({int(time.time()-t0)}s)", flush=True)
            flush(batch); total += len(batch)

    with driver.session() as s:
        nc = s.run("MATCH (c:Company) RETURN count(c) AS n").single()["n"]
        npp = s.run("MATCH (p:Person) RETURN count(p) AS n").single()["n"]
        ne = s.run("MATCH ()-[r:IS_DIRIGEANT]->() RETURN count(r) AS n").single()["n"]
        na = s.run("MATCH ()-[r:IS_DIRIGEANT]->() WHERE r.actif RETURN count(r) AS n").single()["n"]
    driver.close()
    print({"companies": nc, "persons": npp, "edges": ne, "edges_actifs": na,
           "rows": total, "duration_s": int(time.time()-t0)}, flush=True)
    print("DONE neo4j_loader_full", flush=True)


if __name__ == "__main__":
    main()
