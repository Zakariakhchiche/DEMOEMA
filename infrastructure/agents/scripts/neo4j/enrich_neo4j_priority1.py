#!/usr/bin/env python3
"""Neo4j Priority 1 enrichments — props sur Person nodes existants.

Enrichments couverts dans ce script (séquentiel, idempotent) :
1. HATVP lobbying    : flag is_lobbyist + categorie + denomination_lobby
2. SCI patrimoine    : props n_sci, total_capital_sci, sci_sirens
3. OSINT social      : props linkedin_url, github_username, twitter, n_total_social
4. Wikidata bio      : props qid, birth_year, occupation (humans business FR)

Pas de nouveaux nodes — uniquement enrichissement props sur Person existant.
Approach memory-safe : chunks de 500 rows, idempotent sur chaque run.

Usage :
    DSN=postgres://... NEO4J_URI=bolt://neo4j:7687 NEO4J_PASSWORD=...
    python3 enrich_neo4j_priority1.py [--skip hatvp,sci,osint,wikidata]

Use case : MATCH (p:Person {is_lobbyist: true})-[:CO_MANDATE*1..2]-(target:Person {has_offshore: true}) → réseau lobby ↔ offshore.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import psycopg

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver missing", file=sys.stderr)
    sys.exit(2)


NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "demoema_neo4j_pass")
BATCH = 500


# ────────── HATVP : Lobbyistes inscrits ──────────
HATVP_SQL = """
SELECT
  dirigeant_nom AS nom_uc,
  dirigeant_prenom AS prenom_uc,
  array_agg(DISTINCT denomination ORDER BY denomination) FILTER (WHERE denomination IS NOT NULL) AS lobby_denoms,
  array_agg(DISTINCT categorie_organisation) FILTER (WHERE categorie_organisation IS NOT NULL) AS lobby_categories,
  bool_or(lobbying_actif) AS lobbying_actif
FROM silver.hatvp_lobbying_persons
WHERE dirigeant_nom IS NOT NULL AND dirigeant_prenom IS NOT NULL
GROUP BY dirigeant_nom, dirigeant_prenom
"""

HATVP_CYPHER = """
UNWIND $rows AS row
MATCH (p:Person)
WHERE upper(p.nom) = row.nom_uc
  AND (upper(p.prenom) = row.prenom_uc
       OR row.prenom_uc IN [x IN p.prenoms | upper(x)])
SET p.is_lobbyist = true,
    p.lobby_denominations = row.lobby_denoms,
    p.lobby_categories = row.lobby_categories,
    p.lobbying_actif = row.lobbying_actif
RETURN count(DISTINCT p) AS flagged
"""


# ────────── SCI patrimoine ──────────
SCI_SQL = """
SELECT
  upper(unaccent(nom)) AS nom_uc,
  upper(unaccent(prenom)) AS prenom_uc,
  sum(coalesce(n_sci, 0))::int AS total_n_sci,
  sum(coalesce(total_capital_sci, 0))::numeric AS total_capital,
  array_agg(DISTINCT denomination_sci) FILTER (WHERE denomination_sci IS NOT NULL) AS sci_denos
FROM silver.dirigeant_sci_patrimoine
WHERE nom IS NOT NULL AND prenom IS NOT NULL
GROUP BY upper(unaccent(nom)), upper(unaccent(prenom))
HAVING sum(coalesce(n_sci, 0)) > 0
"""

SCI_CYPHER = """
UNWIND $rows AS row
MATCH (p:Person)
WHERE upper(p.nom) = row.nom_uc
  AND (upper(p.prenom) = row.prenom_uc
       OR row.prenom_uc IN [x IN p.prenoms | upper(x)])
SET p.n_sci = row.total_n_sci,
    p.total_capital_sci = toFloat(row.total_capital),
    p.sci_denominations = row.sci_denos
RETURN count(DISTINCT p) AS flagged
"""


# ────────── OSINT social (Maigret/Holehe data) ──────────
OSINT_SQL = """
SELECT
  upper(unaccent(nom)) AS nom_uc,
  upper(unaccent(prenoms[1])) AS prenom_uc,
  (linkedin_urls)[1] AS linkedin,
  (github_usernames)[1] AS github,
  (twitter_handles)[1] AS twitter,
  coalesce(n_total_social, n_linkedin + n_github + n_twitter + n_other_sites, 0) AS n_total_social
FROM bronze.osint_persons
WHERE nom IS NOT NULL AND prenoms IS NOT NULL AND array_length(prenoms, 1) > 0
"""

OSINT_CYPHER = """
UNWIND $rows AS row
MATCH (p:Person)
WHERE upper(p.nom) = row.nom_uc
  AND (upper(p.prenom) = row.prenom_uc
       OR row.prenom_uc IN [x IN p.prenoms | upper(x)])
SET p.linkedin_url = row.linkedin,
    p.github_username = row.github,
    p.twitter_handle = row.twitter,
    p.n_total_social = row.n_total_social
RETURN count(DISTINCT p) AS flagged
"""


# ────────── Wikidata humans ──────────
WIKIDATA_SQL = """
SELECT
  upper(unaccent(split_part(label, ' ', 1))) AS prenom_uc,
  upper(unaccent(trim(substring(label from position(' ' in label) + 1)))) AS nom_uc,
  qid,
  birth_year,
  occupation
FROM bronze.wikidata_entreprises_raw
WHERE birth_year IS NOT NULL
  AND label IS NOT NULL
  AND position(' ' in label) > 0
"""

WIKIDATA_CYPHER = """
UNWIND $rows AS row
MATCH (p:Person)
WHERE upper(p.nom) = row.nom_uc
  AND (upper(p.prenom) = row.prenom_uc
       OR row.prenom_uc IN [x IN p.prenoms | upper(x)])
SET p.wikidata_qid = row.qid,
    p.wikidata_birth_year = row.birth_year,
    p.wikidata_occupation = row.occupation
RETURN count(DISTINCT p) AS flagged
"""


def _run_enrich(name, conn, driver, sql, cypher, key_func=None):
    """Generic enrichment runner."""
    print(f"[{name}] Picking from datalake...", file=sys.stderr)
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    print(f"[{name}] {len(rows)} rows to process", file=sys.stderr)

    n_flagged = 0
    if not rows:
        return 0
    columns = [d.name for d in cur.description]
    with driver.session() as s:
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            params = [dict(zip(columns, r)) for r in chunk]
            result = s.run(cypher, rows=params).single()
            n_flagged += int(result["flagged"]) if result else 0
            if (i // BATCH) % 20 == 0 and i > 0:
                print(f"  [{name}] {i+BATCH}/{len(rows)} flagged so far: {n_flagged}",
                      file=sys.stderr)
    print(f"[{name}] DONE — {n_flagged} Persons flagged", file=sys.stderr)
    return n_flagged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", default="", help="Comma-separated: hatvp,sci,osint,wikidata")
    args = ap.parse_args()
    skip = set(s.strip().lower() for s in args.skip.split(",") if s.strip())

    dsn = os.environ.get("DSN")
    if not dsn:
        print("ERROR: DSN env var required", file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()

    results = {}
    with psycopg.connect(dsn) as conn:
        if "hatvp" not in skip:
            results["hatvp"] = _run_enrich("hatvp", conn, driver, HATVP_SQL, HATVP_CYPHER)
        if "sci" not in skip:
            results["sci"] = _run_enrich("sci", conn, driver, SCI_SQL, SCI_CYPHER)
        if "osint" not in skip:
            results["osint"] = _run_enrich("osint", conn, driver, OSINT_SQL, OSINT_CYPHER)
        if "wikidata" not in skip:
            results["wikidata"] = _run_enrich("wikidata", conn, driver, WIKIDATA_SQL, WIKIDATA_CYPHER)

    driver.close()
    results["total_duration_s"] = round(time.time() - t0, 1)
    print(results)


if __name__ == "__main__":
    main()
