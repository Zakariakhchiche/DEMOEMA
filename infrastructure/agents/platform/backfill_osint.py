"""Enrichit le graphe Neo4j avec l'OSINT autour du dirigeant.

1. Sociétés (silver.osint_companies_enriched, ~11,5k) : présence digitale —
   primary_domain, digital_presence_score, tech_stack, has_github/linkedin.
   Match par siren.
2. Personnes (silver.osint_persons_enriched, ~2k) : profils sociaux —
   linkedin/github/twitter, emails vérifiés, n_social. Match par uid canonique
   (_person_uid sur nom/prénoms/date_naissance).

⚠️ Couverture limitée par le scan OSINT lui-même (échantillon cible, pas tout
le datalake). À relancer après un rebuild des Person.

Usage : docker exec -w /app demomea-agents-platform python backfill_osint.py
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

BATCH = 1000

COMPANY_SQL = """
SELECT siren, primary_domain, all_domains, tech_stack,
       COALESCE(has_github_org, false) AS has_github,
       COALESCE(has_linkedin_page, false) AS has_linkedin,
       COALESCE(digital_presence_score, 0) AS digital_score,
       COALESCE(domains_count, 0) AS domains_count
FROM silver.osint_companies_enriched
WHERE siren IS NOT NULL
"""

COMPANY_CYPHER = """
UNWIND $rows AS row
MATCH (c:Company {siren: row.siren})
SET c.primary_domain = row.primary_domain,
    c.all_domains = row.all_domains,
    c.tech_stack = row.tech_stack,
    c.has_github_org = row.has_github,
    c.has_linkedin_page = row.has_linkedin,
    c.digital_presence_score = row.digital_score,
    c.osint_domains_count = row.domains_count
"""

PERSON_SQL = """
SELECT nom, prenoms, date_naissance,
       linkedin_urls, github_usernames, twitter_handles, emails_valid,
       COALESCE(has_linkedin, false) AS has_linkedin,
       COALESCE(has_github, false)   AS has_github,
       COALESCE(n_total_social, 0)   AS n_social
FROM silver.osint_persons_enriched
WHERE nom IS NOT NULL
"""

PERSON_CYPHER = """
UNWIND $rows AS row
MATCH (p:Person {uid: row.uid})
SET p.linkedin_urls = row.linkedin_urls,
    p.github_usernames = row.github_usernames,
    p.twitter_handles = row.twitter_handles,
    p.emails_valid = row.emails_valid,
    p.has_linkedin = row.has_linkedin,
    p.has_github = row.has_github,
    p.n_social = row.n_social,
    p.has_osint = true
"""


def main() -> None:
    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def run(cypher, rows):
        if rows:
            with driver.session() as s:
                return s.run(cypher, rows=rows).consume().counters.properties_set
        return 0

    # 1. Sociétés
    cp = 0
    batch = []
    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        cur.execute(COMPANY_SQL)
        for siren, dom, alld, tech, hg, hl, ds, dc in cur:
            batch.append({"siren": siren, "primary_domain": dom, "all_domains": alld,
                          "tech_stack": tech, "has_github": bool(hg), "has_linkedin": bool(hl),
                          "digital_score": int(ds or 0), "domains_count": int(dc or 0)})
            if len(batch) >= BATCH:
                cp += run(COMPANY_CYPHER, batch); batch = []
        cp += run(COMPANY_CYPHER, batch)
    print(f"[osint sociétés] {cp} props set ({int(time.time()-t0)}s)", flush=True)

    # 2. Personnes
    pp = 0
    batch = []
    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        cur.execute(PERSON_SQL)
        for nom, prenoms, dn, li, gh, tw, em, hl, hg, ns in cur:
            batch.append({
                "uid": _person_uid(nom, list(prenoms or []), dn),
                "linkedin_urls": li, "github_usernames": gh, "twitter_handles": tw,
                "emails_valid": em, "has_linkedin": bool(hl), "has_github": bool(hg),
                "n_social": int(ns or 0),
            })
            if len(batch) >= BATCH:
                pp += run(PERSON_CYPHER, batch); batch = []
        pp += run(PERSON_CYPHER, batch)
    print(f"[osint personnes] {pp} props set ({int(time.time()-t0)}s)", flush=True)

    driver.close()
    print(f"DONE osint backfill en {int(time.time()-t0)}s", flush=True)


if __name__ == "__main__":
    main()
