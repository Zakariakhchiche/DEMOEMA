#!/usr/bin/env python3
"""Build CO_MANDATE relations on FULL graph (8M Persons).

Strategy : APOC iterate par chunks de 1000 companies à la fois pour éviter
OOM Neo4j. Filtre out concentrateurs (companies avec >50 dirigeants =
commissaires aux comptes type CAC qui font du bruit M&A).

Estimation finale : ~50-100M CO_MANDATE relations.
Durée : ~2-4h selon Neo4j heap.

Usage :
    NEO4J_URI=bolt://neo4j:7687 NEO4J_PASSWORD=...
    python3 build_co_mandates_full.py
"""
from __future__ import annotations

import os
import sys
import time

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver missing", file=sys.stderr)
    sys.exit(2)


NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "demoema_neo4j_pass")

# Resume mode : skip cleanup and resume from chunk N. Set when restarting after
# an interrupted run — MERGE is idempotent so re-doing chunks is safe but slow.
RESUME_SKIP = int(os.environ.get("RESUME_SKIP", "0"))
SKIP_CLEANUP = os.environ.get("SKIP_CLEANUP", "0") == "1" or RESUME_SKIP > 0


# Cleanup avant rebuild (idempotent).
CLEANUP_CYPHER = """
CALL apoc.periodic.iterate(
  'MATCH ()-[r:CO_MANDATE]->() RETURN r',
  'DELETE r',
  {batchSize: 50000, parallel: false}
)
"""

# Fallback si APOC pas dispo : DELETE en chunks Cypher pur.
CLEANUP_FALLBACK = """
MATCH ()-[r:CO_MANDATE]->()
WITH r LIMIT 100000
DELETE r
RETURN count(r) AS deleted
"""

# Build : pour chaque Company avec 2-50 dirigeants, MERGE CO_MANDATE entre
# toutes les paires (id(p1) < id(p2) → 1 direction unique).
# APOC iterate streame par batch sans OOM.
BUILD_APOC = """
CALL apoc.periodic.iterate(
  '
    MATCH (c:Company)<-[:IS_DIRIGEANT]-()
    WITH c, count(*) AS n
    WHERE n >= 2 AND n <= 50
    RETURN c
  ',
  '
    MATCH (c)<-[:IS_DIRIGEANT]-(p1:Person)
    MATCH (c)<-[:IS_DIRIGEANT]-(p2:Person)
    WHERE id(p1) < id(p2)
    MERGE (p1)-[r:CO_MANDATE]->(p2)
    ON CREATE SET r.via_sirens = [c.siren], r.n_shared_companies = 1
    ON MATCH SET r.via_sirens = coalesce(r.via_sirens, []) + c.siren,
                 r.n_shared_companies = coalesce(r.n_shared_companies, 0) + 1
  ',
  {batchSize: 500, parallel: false, retries: 3}
)
"""

# Fallback sans APOC : process par chunks de companies en Python.
COUNT_CHUNKS = """
MATCH (c:Company)<-[:IS_DIRIGEANT]-()
WITH c, count(*) AS n
WHERE n >= 2 AND n <= 50
RETURN count(c) AS total_companies
"""

CHUNK_BUILD = """
MATCH (c:Company)<-[:IS_DIRIGEANT]-()
WITH c, count(*) AS n
WHERE n >= 2 AND n <= 50
WITH c SKIP $skip LIMIT $limit
MATCH (c)<-[:IS_DIRIGEANT]-(p1:Person)
MATCH (c)<-[:IS_DIRIGEANT]-(p2:Person)
WHERE id(p1) < id(p2)
MERGE (p1)-[r:CO_MANDATE]->(p2)
ON CREATE SET r.via_sirens = [c.siren], r.n_shared_companies = 1
ON MATCH SET r.via_sirens = coalesce(r.via_sirens, []) + c.siren,
             r.n_shared_companies = coalesce(r.n_shared_companies, 0) + 1
RETURN count(c) AS processed
"""

VERIFY_CYPHER = """
MATCH ()-[r:CO_MANDATE]->()
RETURN count(r) AS total_relations
"""


def has_apoc(driver):
    try:
        with driver.session() as s:
            s.run("CALL apoc.help('iterate')").consume()
            return True
    except Exception:
        return False


def main():
    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()

    apoc = has_apoc(driver)
    print(f"[co-mandate] APOC available: {apoc}", file=sys.stderr)

    with driver.session() as s:
        if SKIP_CLEANUP:
            print(f"[co-mandate] SKIP cleanup (resume mode, RESUME_SKIP={RESUME_SKIP})",
                  file=sys.stderr)
        else:
            print("[co-mandate] Cleanup existing CO_MANDATE...", file=sys.stderr)
            if apoc:
                s.run(CLEANUP_CYPHER).consume()
            else:
                while True:
                    r = s.run(CLEANUP_FALLBACK).single()
                    deleted = r["deleted"] if r else 0
                    if not deleted:
                        break
                    print(f"  cleanup: deleted {deleted}", file=sys.stderr)

        print("[co-mandate] Counting companies with 2-50 dirigeants...", file=sys.stderr)
        total = s.run(COUNT_CHUNKS).single()["total_companies"]
        print(f"  {total} companies eligible", file=sys.stderr)

        if apoc:
            print("[co-mandate] Building via APOC iterate (batchSize=500)...", file=sys.stderr)
            r = s.run(BUILD_APOC).single()
            print(f"  apoc result: {dict(r) if r else None}", file=sys.stderr)
        else:
            print(f"[co-mandate] Building via Python chunks (no APOC) — start skip={RESUME_SKIP}...",
                  file=sys.stderr)
            CHUNK = 1000
            skip = RESUME_SKIP
            consecutive_empty = 0
            n_deadlock_retries = 0
            while skip < total:
                # Retry-on-transient-error : Neo4j Forseti deadlocks happen
                # under concurrent MERGE → retry up to 5x with jitter, then skip.
                processed = 0
                for attempt in range(5):
                    try:
                        r = s.run(CHUNK_BUILD, skip=skip, limit=CHUNK).single()
                        processed = r["processed"] if r else 0
                        break
                    except Exception as e:
                        # neo4j.exceptions.TransientError ou idem class
                        msg = str(e)
                        is_transient = (
                            "DeadlockDetected" in msg
                            or "TransientError" in type(e).__name__
                        )
                        if not is_transient or attempt == 4:
                            print(f"  chunk {skip} FATAL after {attempt+1} attempts: {type(e).__name__}: {msg[:150]}",
                                  file=sys.stderr, flush=True)
                            raise
                        n_deadlock_retries += 1
                        wait = 0.5 * (2 ** attempt) + (skip % 7) / 100.0
                        print(f"  chunk {skip} transient (attempt {attempt+1}/5), retry in {wait:.1f}s",
                              file=sys.stderr, flush=True)
                        time.sleep(wait)

                skip += CHUNK
                print(f"  chunk {skip}/{total} processed={processed}",
                      file=sys.stderr, flush=True)
                if processed == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 5:
                        break
                else:
                    consecutive_empty = 0
            print(f"[co-mandate] {n_deadlock_retries} transient retries during run",
                  file=sys.stderr, flush=True)

        verify = s.run(VERIFY_CYPHER).single()
        n_total = verify["total_relations"]

    driver.close()
    print({
        "co_mandate_relations_total": n_total,
        "duration_s": round(time.time() - t0, 1),
    })


if __name__ == "__main__":
    main()
