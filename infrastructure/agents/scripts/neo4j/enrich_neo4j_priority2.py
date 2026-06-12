#!/usr/bin/env python3
"""Neo4j Priority 2 enrichments — passage du graphe de RISQUE au graphe d'OPPORTUNITÉ M&A.

Deux enrichissements (séquentiels, idempotents) qui posent la base de la killer
feature « alertes pré-cession » :

1. SANTÉ FINANCIÈRE / DÉTRESSE sur les nœuds Company (depuis silver.entreprises_signals,
   les ratios calculés après le nettoyage du datalake) : financial_health_tier,
   debt_to_ebitda, ebitda_margin + drapeaux has_negative_equity / has_high_leverage /
   has_negative_ebitda / has_revenue_decline + is_distressed agrégé.
   → Débloque : « société en détresse dont un dirigeant dirige aussi une société saine »
     (M&A de consolidation / sauvetage), filtrage des cibles par solidité.

2. ARÊTES A_CEDE (serial sellers, depuis silver.bodacc_annonces) :
   (Person)-[:A_CEDE {last_date, n_cessions, type}]->(Company) pour chaque dirigeant
   d'une société ayant subi une cession/vente sur 36 mois. Un dirigeant avec >= 2
   arêtes A_CEDE est marqué is_serial_seller = true.
   → Débloque : « cibles dont un dirigeant est un vendeur en série » (signal pré-cession
     le plus fort, à 1 saut), réseaux de cession.

Pas de drivers ni schéma cassés : on n'ajoute QUE des props sur Company existant et
des arêtes entre Person/Company existants. Idempotent (MERGE + SET).

Usage :
    DSN=postgres://... NEO4J_URI=bolt://neo4j:7687 NEO4J_PASSWORD=...
    python3 enrich_neo4j_priority2.py [--skip fin,cession]

Use case killer (Cypher) :
    MATCH (target:Company)<-[:IS_DIRIGEANT]-(p:Person {is_serial_seller: true})
    WHERE target.has_pro_ma = true AND coalesce(target.is_distressed,false) = false
    RETURN target  // cibles saines pilotées par un vendeur en série
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


# ────────── 1. Santé financière / détresse sur Company ──────────
# Cast numériques en float8 → float Python natif (le driver Neo4j ne sérialise
# pas les Decimal de psycopg).
FIN_SQL = """
SELECT
  btrim(siren)                              AS siren,
  financial_health_tier                     AS tier,
  round(debt_to_ebitda::numeric, 3)::float8 AS debt_to_ebitda,
  round(ebitda_margin::numeric, 4)::float8  AS ebitda_margin,
  coalesce(has_negative_equity,  false)     AS has_negative_equity,
  coalesce(has_high_leverage,    false)     AS has_high_leverage,
  coalesce(has_negative_ebitda,  false)     AS has_negative_ebitda,
  coalesce(has_revenue_decline,  false)     AS has_revenue_decline
FROM silver.entreprises_signals
WHERE siren IS NOT NULL
"""

FIN_CYPHER = """
UNWIND $rows AS row
MATCH (c:Company {siren: row.siren})
SET c.financial_health_tier = row.tier,
    c.debt_to_ebitda        = toFloat(row.debt_to_ebitda),
    c.ebitda_margin          = toFloat(row.ebitda_margin),
    c.has_negative_equity    = row.has_negative_equity,
    c.has_high_leverage      = row.has_high_leverage,
    c.has_negative_ebitda    = row.has_negative_ebitda,
    c.has_revenue_decline    = row.has_revenue_decline,
    c.is_distressed = (row.has_negative_equity OR row.has_high_leverage
                       OR row.has_negative_ebitda OR row.has_revenue_decline)
RETURN count(DISTINCT c) AS flagged
"""


# ────────── 2. Arêtes A_CEDE (serial sellers depuis BODACC) ──────────
CESSION_SQL = """
SELECT
  btrim(siren)                   AS siren,
  max(date_parution)::text       AS last_cession_date,
  count(*)::int                  AS n_cessions,
  (array_agg(DISTINCT familleavis_lib))[1] AS cession_type
FROM silver.bodacc_annonces
WHERE siren IS NOT NULL
  AND (familleavis_lib ILIKE '%cession%' OR familleavis_lib ILIKE '%vente%')
  AND date_parution > (now() - interval '36 months')
GROUP BY siren
"""

# Crée l'arête A_CEDE depuis CHAQUE dirigeant de la société cédée + marque la
# société. MERGE = idempotent.
CESSION_CYPHER = """
UNWIND $rows AS row
MATCH (c:Company {siren: row.siren})
SET c.has_cession_recente = true,
    c.last_cession_date    = row.last_cession_date,
    c.n_cessions_36m       = row.n_cessions
WITH c, row
MATCH (p:Person)-[:IS_DIRIGEANT]->(c)
MERGE (p)-[r:A_CEDE]->(c)
SET r.last_date   = row.last_cession_date,
    r.n_cessions  = row.n_cessions,
    r.type        = row.cession_type
RETURN count(DISTINCT c) AS flagged
"""

# Finalize : marque les vendeurs en série (>= 2 sociétés cédées distinctes).
SERIAL_SELLER_CYPHER = """
MATCH (p:Person)-[:A_CEDE]->(c:Company)
WITH p, count(DISTINCT c) AS n_cedees
SET p.n_societes_cedees = n_cedees,
    p.is_serial_seller  = (n_cedees >= 2)
RETURN count(*) AS persons_marked,
       sum(CASE WHEN n_cedees >= 2 THEN 1 ELSE 0 END) AS serial_sellers
"""

# Index Company(siren) — sécurise la perf des MATCH (no-op si déjà créé).
ENSURE_INDEX = "CREATE INDEX company_siren_idx IF NOT EXISTS FOR (c:Company) ON (c.siren)"


def _run_enrich(name, dsn, driver, sql, cypher):
    """Runner générique (cf. enrich_neo4j_priority1) : pick PG → batch Cypher."""
    print(f"[{name}] Picking from datalake (fresh connection)...", file=sys.stderr, flush=True)
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            columns = [d.name for d in cur.description]
    print(f"[{name}] {len(rows)} rows to process", file=sys.stderr, flush=True)

    if not rows:
        return 0
    n_flagged = 0
    n_errors = 0
    with driver.session() as s:
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            params = [dict(zip(columns, r)) for r in chunk]
            try:
                result = s.run(cypher, rows=params).single()
                n_flagged += int(result["flagged"]) if result else 0
            except Exception as e:
                n_errors += 1
                if n_errors <= 5:
                    print(f"  [{name}] batch {i} ERROR: {type(e).__name__}: {str(e)[:200]}",
                          file=sys.stderr, flush=True)
            if (i // BATCH) % 5 == 0:
                print(f"  [{name}] {min(i+BATCH, len(rows))}/{len(rows)} flagged: {n_flagged} errors: {n_errors}",
                      file=sys.stderr, flush=True)
    print(f"[{name}] DONE — {n_flagged} flagged, {n_errors} batch errors", file=sys.stderr, flush=True)
    return n_flagged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", default="", help="Comma-separated: fin,cession")
    args = ap.parse_args()
    skip = set(s.strip().lower() for s in args.skip.split(",") if s.strip())

    dsn = os.environ.get("DSN")
    if not dsn:
        print("ERROR: DSN env var required", file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    with driver.session() as s:
        s.run(ENSURE_INDEX)

    results = {}
    if "fin" not in skip:
        results["company_financials"] = _run_enrich("fin", dsn, driver, FIN_SQL, FIN_CYPHER)
    if "cession" not in skip:
        results["cession_edges"] = _run_enrich("cession", dsn, driver, CESSION_SQL, CESSION_CYPHER)
        with driver.session() as s:
            rec = s.run(SERIAL_SELLER_CYPHER).single()
            if rec:
                results["serial_sellers"] = int(rec["serial_sellers"] or 0)
                print(f"[serial_sellers] {rec['serial_sellers']} vendeurs en série marqués",
                      file=sys.stderr, flush=True)

    driver.close()
    results["total_duration_s"] = round(time.time() - t0, 1)
    print(results)


if __name__ == "__main__":
    main()
