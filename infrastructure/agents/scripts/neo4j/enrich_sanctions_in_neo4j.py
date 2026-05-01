#!/usr/bin/env python3
"""Neo4j Sanctions enrichment.

Match silver.opensanctions (schema='Person') avec les Person nodes Neo4j
existantes (créés par neo4j_sync.py). Flag les matches avec :
- is_sanctioned = true
- sanctions_programs = [list]
- sanctions_topics = [list]
- sanctions_countries = [list]
- sanctions_caption = "OFAC SDN: ..."

Approach : ne crée PAS de nouveaux nodes (silver.opensanctions = 280K rows
internationaux, dont 99% n'ont aucun lien avec dirigeants FR). On enrichit
les Persons existantes uniquement. Match best-effort sur (nom, prenom) avec
upper(unaccent).

Usage :
    DSN=postgres://... NEO4J_URI=bolt://neo4j:7687 NEO4J_PASSWORD=...
    python3 enrich_sanctions_in_neo4j.py [--limit N]
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
    print("ERROR: neo4j driver missing. pip install neo4j", file=sys.stderr)
    sys.exit(2)


NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "demoema_neo4j_pass")
BATCH = int(os.environ.get("NEO4J_BATCH", "500"))


# Chaque opensanctions row est un (entity_id, name, schema='Person', alias_names[],
# topics[], countries[], sanctions_programs[]). Le `name` est libre (peut être
# "JOHN SMITH", "SMITH John", "John Q. Smith", etc.). On tokenize basique :
# split sur espaces → 1er token = potentiellement prenom, dernier = nom.
PICK_SQL = """
WITH split_names AS (
    SELECT
        entity_id,
        upper(unaccent(name)) AS name_uc,
        regexp_split_to_array(upper(unaccent(trim(name))), '\s+') AS parts,
        topics,
        countries,
        sanctions_programs,
        caption
    FROM silver.opensanctions
    WHERE schema = 'Person'
      AND name IS NOT NULL
      AND length(name) > 4
)
SELECT
    parts[array_upper(parts, 1)] AS nom_uc,    -- dernier token = nom
    parts[1] AS prenom_uc,                      -- 1er token = prenom
    array_agg(DISTINCT entity_id) AS entity_ids,
    array_agg(DISTINCT caption) FILTER (WHERE caption IS NOT NULL) AS captions,
    array_agg(DISTINCT t) AS topics
        FROM (
            SELECT entity_id, parts, caption, unnest(coalesce(topics, ARRAY[]::text[])) AS t
            FROM split_names
        ) tt,
        unnest(ARRAY[1]) AS dummy
    GROUP BY parts[array_upper(parts, 1)], parts[1]
HAVING parts[1] != parts[array_upper(parts, 1)]  -- Au moins 2 tokens distincts
LIMIT %s
"""

# Pas de subquery imbriquée : un seul row par sanctioned name + on garde
# directement le 1er topics/programs/countries (la plupart des persons n'ont
# qu'1 entry sanctions de toute façon).
PICK_SQL_SIMPLE = """
SELECT
  upper(unaccent(name)) AS name_uc,
  (array_agg(entity_id))[1:5] AS entity_ids,
  (array_agg(caption))[1:5] AS captions,
  (array_agg(topics))[1] AS topics,
  (array_agg(sanctions_programs))[1] AS programs,
  (array_agg(countries))[1] AS countries
FROM silver.opensanctions
WHERE schema = 'Person'
  AND name IS NOT NULL
  AND length(name) > 4
GROUP BY upper(unaccent(name))
LIMIT %s
"""


# Cypher : pour chaque sanctioned name, MATCH les Persons dont
# upper(unaccent(prenom + ' ' + nom)) ou (nom + ' ' + prenom) match le name.
# On stocke en property tableau (multi-leak possible).
ENRICH_CYPHER = """
UNWIND $rows AS row
MATCH (p:Person)
WHERE upper(p.nom + ' ' + p.prenom) = row.name_uc
   OR upper(p.prenom + ' ' + p.nom) = row.name_uc
SET p.is_sanctioned = true,
    p.sanctions_entity_ids = coalesce(p.sanctions_entity_ids, []) + row.entity_ids,
    p.sanctions_captions = coalesce(p.sanctions_captions, []) + row.captions,
    p.sanctions_topics = row.topics,
    p.sanctions_programs = row.programs,
    p.sanctions_countries = row.countries
RETURN count(DISTINCT p) AS persons_flagged
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300000,
                    help="Max sanctions rows à processer (default 300K = tout silver)")
    args = ap.parse_args()

    dsn = os.environ.get("DSN")
    if not dsn:
        print("ERROR: DSN env var required", file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()

    n_processed = 0
    n_flagged = 0

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(PICK_SQL_SIMPLE, (args.limit,))
        rows = cur.fetchall()
        print(f"[sanctions→neo4j] {len(rows)} sanctioned names à matcher", file=sys.stderr)

        with driver.session() as s:
            for i in range(0, len(rows), BATCH):
                chunk = rows[i:i + BATCH]
                params = [
                    {
                        "name_uc": r[0],
                        "entity_ids": r[1] or [],
                        "captions": r[2] or [],
                        "topics": r[3] or [],
                        "programs": r[4] or [],
                        "countries": r[5] or [],
                    }
                    for r in chunk
                ]
                result = s.run(ENRICH_CYPHER, rows=params).single()
                n_flagged += int(result["persons_flagged"]) if result else 0
                n_processed += len(params)
                if n_processed % 5000 == 0:
                    print(f"  [{n_processed}/{len(rows)}] flagged: {n_flagged}",
                          file=sys.stderr)

    driver.close()
    print({
        "processed": n_processed,
        "persons_flagged": n_flagged,
        "duration_s": round(time.time() - t0, 1),
    })


if __name__ == "__main__":
    main()
