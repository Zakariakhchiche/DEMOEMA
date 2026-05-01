#!/usr/bin/env python3
"""Neo4j ICIJ Offshore enrichment.

Pré-requis :
- silver.icij_offshore_match doit être peuplée (cf. setup_icij_silver_mv.sql)
- Neo4j up + neo4j_sync.py a déjà créé les Persons FR

Pour chaque match (officer ICIJ ↔ dirigeant FR), ajoute des propriétés sur
le node Person existant :
- has_offshore = true
- icij_leaks = ['panama_papers', 'paradise_papers', ...]
- icij_node_ids = ['12345', '67890', ...]
- icij_countries = ['BVI', 'PA', ...]

Approach : on n'AJOUTE PAS de nouveaux nodes ICIJ (ça exploserait à 1.5M).
On enrichit les Persons existantes avec un flag offshore + métadonnées
ICIJ. Pour le graph "relationships.csv" complet (intermediaries, addresses),
voir enrich_icij_relations_in_neo4j.py (à créer plus tard).

Usage :
    DSN=postgres://... NEO4J_URI=bolt://neo4j:7687 NEO4J_PASSWORD=...
    python3 enrich_icij_in_neo4j.py [--limit N]
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


# Aggregation SQL : groupe les matches ICIJ par (nom, prenom) pour avoir
# tous les leaks/nodes/countries d'un même dirigeant en une row.
PICK_SQL = """
SELECT
  nom,
  prenom,
  array_agg(DISTINCT icij_leak) FILTER (WHERE icij_leak IS NOT NULL) AS leaks,
  array_agg(DISTINCT icij_node_id) FILTER (WHERE icij_node_id IS NOT NULL) AS node_ids,
  array_agg(DISTINCT icij_country) FILTER (WHERE icij_country IS NOT NULL AND icij_country != '') AS countries,
  count(*) AS n_matches,
  max(pro_ma_score) AS pro_ma_score
FROM silver.icij_offshore_match
GROUP BY nom, prenom
ORDER BY pro_ma_score DESC NULLS LAST
LIMIT %s
"""


# Cypher : SET propriétés sur Person existant.
# On utilise nom + premier prénom pour matcher (les Persons FR ont prenom = prenoms[0]).
# Pas besoin de match exact sur date_naissance car c'est un enrichissement
# best-effort. Si plusieurs Persons matchent, toutes seront flaggées.
ENRICH_CYPHER = """
UNWIND $rows AS row
MATCH (p:Person)
WHERE p.nom = row.nom
  AND (p.prenom = row.prenom OR row.prenom IN p.prenoms)
SET p.has_offshore = true,
    p.icij_leaks = row.leaks,
    p.icij_node_ids = row.node_ids,
    p.icij_countries = row.countries,
    p.icij_n_matches = row.n_matches
RETURN count(DISTINCT p) AS persons_flagged
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100000,
                    help="Max ICIJ matches à processer (default 100K)")
    args = ap.parse_args()

    dsn = os.environ.get("DSN")
    if not dsn:
        print("ERROR: DSN env var required", file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: neo4j unreachable: {e}", file=sys.stderr)
        sys.exit(2)

    n_processed = 0
    n_flagged = 0

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(PICK_SQL, (args.limit,))
        rows = cur.fetchall()
        print(f"[icij→neo4j] {len(rows)} dirigeants ICIJ matchés à enrichir", file=sys.stderr)

        with driver.session() as s:
            for i in range(0, len(rows), BATCH):
                chunk = rows[i:i + BATCH]
                params = [
                    {
                        "nom": r[0],
                        "prenom": r[1],
                        "leaks": r[2] or [],
                        "node_ids": r[3] or [],
                        "countries": r[4] or [],
                        "n_matches": int(r[5] or 0),
                    }
                    for r in chunk
                ]
                result = s.run(ENRICH_CYPHER, rows=params).single()
                n_flagged += int(result["persons_flagged"]) if result else 0
                n_processed += len(params)
                if n_processed % 5000 == 0:
                    print(f"  [{n_processed}/{len(rows)}] flagged so far: {n_flagged}",
                          file=sys.stderr)

    driver.close()
    print({
        "processed": n_processed,
        "persons_flagged": n_flagged,
        "duration_s": round(time.time() - t0, 1),
    })


if __name__ == "__main__":
    main()
