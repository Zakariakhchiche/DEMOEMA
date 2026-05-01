#!/usr/bin/env python3
"""Load INPI dirigeants → Neo4j graph.

Nodes:
  (Company {siren, denomination, forme_juridique, capital, code_ape, date_immat})
  (Person {uid, nom, prenoms, date_naissance})

Relations:
  (Person)-[IS_DIRIGEANT {role, actif, since}]->(Company)

Usage: neo4j_loader.py [--companies-limit N] [--batch 500]
Env: DSN (postgres), NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
"""
from __future__ import annotations
import argparse, hashlib, os, sys, time
import psycopg
from neo4j import GraphDatabase


def _slug(s: str) -> str:
    if not s:
        return ""
    import unicodedata, re
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"[^a-zA-Z0-9]", "", s).lower()


def person_uid(nom, prenoms, dn):
    parts = [_slug(nom), _slug((prenoms or [""])[0]), dn or ""]
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:40]


def ensure_schema(driver):
    with driver.session() as s:
        s.run("CREATE CONSTRAINT company_siren IF NOT EXISTS FOR (c:Company) REQUIRE c.siren IS UNIQUE")
        s.run("CREATE CONSTRAINT person_uid   IF NOT EXISTS FOR (p:Person)  REQUIRE p.uid   IS UNIQUE")
        s.run("CREATE INDEX person_nom IF NOT EXISTS FOR (p:Person) ON (p.nom)")
        s.run("CREATE INDEX company_forme IF NOT EXISTS FOR (c:Company) ON (c.forme_juridique)")


COMPANY_QUERY = """
WITH e AS (
  SELECT siren, denomination, forme_juridique,
         COALESCE(montant_capital, 0) AS capital,
         code_ape,
         date_immatriculation,
         adresse_code_postal
  FROM bronze.inpi_formalites_entreprises
  WHERE forme_juridique IN ('5710','5720','5730','5485','5499','5505','5510','5515','5520','5530','5540','5599',
                            '5385','5308','5306','5202','5203')
    AND COALESCE(montant_capital, 0) >= 500000
  ORDER BY montant_capital DESC NULLS LAST
  LIMIT %s
)
SELECT siren, denomination, forme_juridique, capital, code_ape,
       to_char(date_immatriculation, 'YYYY-MM-DD') AS date_immat,
       adresse_code_postal
FROM e
"""

PERSON_QUERY = """
SELECT p.representant_id, p.siren,
       p.individu_nom, p.individu_prenoms, p.individu_date_naissance,
       p.role_entreprise, p.actif, p.individu_role,
       p.type_de_personne
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
SET p.nom = row.nom,
    p.prenoms = row.prenoms,
    p.date_naissance = row.date_naissance
WITH p, row
MATCH (c:Company {siren: row.siren})
MERGE (p)-[r:IS_DIRIGEANT]->(c)
SET r.role = row.role,
    r.actif = row.actif,
    r.individu_role = row.individu_role
"""


def load_companies(pg_cur, driver, limit: int, batch: int) -> list[str]:
    pg_cur.execute(COMPANY_QUERY, (limit,))
    all_rows = pg_cur.fetchall()
    sirens = [r[0] for r in all_rows]
    print(f"  loading {len(all_rows)} companies into Neo4j", file=sys.stderr)
    with driver.session() as s:
        for i in range(0, len(all_rows), batch):
            chunk = all_rows[i:i + batch]
            params = [
                {"siren": r[0], "denomination": r[1], "forme_juridique": r[2],
                 "capital": float(r[3]) if r[3] else 0.0,
                 "code_ape": r[4], "date_immat": r[5], "code_postal": r[6]}
                for r in chunk
            ]
            s.run(MERGE_COMPANY, rows=params)
    return sirens


def load_persons_and_edges(pg_cur, driver, sirens: list[str], batch: int) -> int:
    # Chunk SIRENs because of SQL array arg limits
    total = 0
    S_CHUNK = 5000
    for i in range(0, len(sirens), S_CHUNK):
        sub = sirens[i:i + S_CHUNK]
        pg_cur.execute(PERSON_QUERY, (sub,))
        rows = pg_cur.fetchall()
        print(f"  processing {len(rows)} persons for siren chunk {i}..{i+len(sub)}",
              file=sys.stderr, flush=True)
        params = []
        for (representant_id, siren, nom, prenoms, dn, role_ent, actif, individu_role, _t) in rows:
            uid = person_uid(nom, prenoms, dn)
            params.append({
                "uid": uid, "nom": nom, "prenoms": prenoms or [], "date_naissance": dn,
                "siren": siren, "role": role_ent, "actif": bool(actif),
                "individu_role": individu_role,
            })
        with driver.session() as s:
            for j in range(0, len(params), batch):
                s.run(MERGE_PERSON_EDGE, rows=params[j:j + batch])
        total += len(rows)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies-limit", type=int, default=10000)
    ap.add_argument("--batch", type=int, default=500)
    args = ap.parse_args()

    dsn = os.environ.get("DSN")
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://demomea-neo4j:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_pass = os.environ.get("NEO4J_PASSWORD", "demoema_neo4j_pass")
    if not dsn:
        print("DSN env required", file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))
    driver.verify_connectivity()
    print(f"connected to {neo4j_uri}", file=sys.stderr)

    ensure_schema(driver)

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        sirens = load_companies(cur, driver, args.companies_limit, args.batch)
        persons = load_persons_and_edges(cur, driver, sirens, args.batch)

    # Stats
    with driver.session() as s:
        n_c = s.run("MATCH (c:Company) RETURN count(c) AS n").single()["n"]
        n_p = s.run("MATCH (p:Person)  RETURN count(p) AS n").single()["n"]
        n_e = s.run("MATCH ()-[r:IS_DIRIGEANT]->() RETURN count(r) AS n").single()["n"]
    driver.close()

    print({"companies": n_c, "persons": n_p, "edges": n_e,
           "duration_s": round(time.time() - t0, 1)})


if __name__ == "__main__":
    main()
