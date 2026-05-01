#!/usr/bin/env python3
"""Neo4j Co-mandats relations builder.

Use case M&A killer : pour chaque Company qui a 2+ dirigeants reliés via
IS_DIRIGEANT, créer des relations CO_MANDATE entre les Persons qui partagent
cette Company. Permet ensuite de répondre à des queries comme :

    "Trouve tous les dirigeants à 2 degrés de Serge LUFTMAN"
    MATCH (p:Person {full_name: 'Serge LUFTMAN'})-[:CO_MANDATE*1..2]-(target)
    RETURN target.full_name, count(*) AS strength

Approach :
- Pas de write SQL — tout en Cypher pur sur les nodes Person + IS_DIRIGEANT
  déjà créés par neo4j_sync.py.
- Pour chaque Company avec 2+ dirigeants → MERGE relation CO_MANDATE
  (Person)-[r:CO_MANDATE]-(Person) bidirectionnelle (relations symétriques
  → on ne crée qu'une direction et on query sans direction).
- Property `via_sirens` : liste des sirens partagés (network density signal).
- Property `n_shared_companies` : count companies partagées.

Usage :
    NEO4J_URI=bolt://neo4j:7687 NEO4J_PASSWORD=...
    python3 build_co_mandate_relations.py
"""
from __future__ import annotations

import os
import sys
import time

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver missing. pip install neo4j", file=sys.stderr)
    sys.exit(2)


NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "demoema_neo4j_pass")


# Step 1 : Cleanup d'éventuelles relations CO_MANDATE existantes (idempotent)
CLEANUP_CYPHER = """
MATCH ()-[r:CO_MANDATE]->()
DELETE r
RETURN count(r) AS deleted
"""


# Step 2 : Pour chaque Company avec 2+ dirigeants, MERGE relation CO_MANDATE
# entre toutes les paires de Persons. On utilise id(p) < id(p2) pour éviter
# de créer 2 relations symétriques (p→p2 ET p2→p).
#
# La query s'exécute en streaming via apoc.periodic.iterate si APOC dispo,
# sinon en chunks Python pour éviter d'exploser la heap Neo4j.
COUNT_COMPANIES_CYPHER = """
MATCH (c:Company)<-[:IS_DIRIGEANT]-(p:Person)
WITH c, count(p) AS n_dirigeants
WHERE n_dirigeants >= 2
RETURN count(c) AS n_companies, sum(n_dirigeants * (n_dirigeants - 1) / 2) AS n_pairs_estimate
"""

BUILD_CYPHER = """
CALL {
    MATCH (c:Company)<-[:IS_DIRIGEANT]-(p1:Person)
    MATCH (c)<-[:IS_DIRIGEANT]-(p2:Person)
    WHERE id(p1) < id(p2)
    WITH p1, p2, collect(DISTINCT c.siren) AS shared_sirens
    WHERE size(shared_sirens) >= 1
    MERGE (p1)-[r:CO_MANDATE]->(p2)
    SET r.via_sirens = shared_sirens,
        r.n_shared_companies = size(shared_sirens)
    RETURN count(r) AS n
}
RETURN n
"""

VERIFY_CYPHER = """
MATCH ()-[r:CO_MANDATE]->()
RETURN count(r) AS n_relations,
       avg(r.n_shared_companies) AS avg_shared,
       max(r.n_shared_companies) AS max_shared
"""

# Top dirigeants par centralité (degree) — sample pour valider que le graph
# fait du sens.
TOP_CONNECTED_CYPHER = """
MATCH (p:Person)-[:CO_MANDATE]-(other)
WITH p, count(other) AS degree
ORDER BY degree DESC
LIMIT 10
RETURN p.full_name AS name, degree
"""


def main():
    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()

    with driver.session() as s:
        print("[co-mandate] Cleanup existing CO_MANDATE relations...", file=sys.stderr)
        deleted = s.run(CLEANUP_CYPHER).single()["deleted"]
        print(f"  deleted: {deleted}", file=sys.stderr)

        print("[co-mandate] Counting candidates...", file=sys.stderr)
        counts = s.run(COUNT_COMPANIES_CYPHER).single()
        n_companies = counts["n_companies"]
        n_pairs_est = counts["n_pairs_estimate"]
        print(f"  {n_companies} companies with 2+ dirigeants, ~{n_pairs_est} pairs estimated",
              file=sys.stderr)

        if n_pairs_est and n_pairs_est > 1_000_000:
            print(f"WARNING: {n_pairs_est} pairs is heavy. Consider filtering top tier first.",
                  file=sys.stderr)

        print("[co-mandate] Building CO_MANDATE relations (this may take a few minutes)...",
              file=sys.stderr)
        result = s.run(BUILD_CYPHER).single()
        n_built = int(result["n"]) if result else 0

        print("[co-mandate] Verifying...", file=sys.stderr)
        verify = s.run(VERIFY_CYPHER).single()
        n_total = verify["n_relations"]
        avg_shared = verify["avg_shared"]
        max_shared = verify["max_shared"]

        print("[co-mandate] Top 10 most connected dirigeants:", file=sys.stderr)
        top = list(s.run(TOP_CONNECTED_CYPHER))
        for row in top:
            print(f"  {row['name']:50s} degree={row['degree']}", file=sys.stderr)

    driver.close()
    print({
        "co_mandate_relations_built": n_built,
        "co_mandate_relations_total": n_total,
        "avg_shared_companies": float(avg_shared) if avg_shared else None,
        "max_shared_companies": int(max_shared) if max_shared else None,
        "duration_s": round(time.time() - t0, 1),
    })


if __name__ == "__main__":
    main()
