"""One-shot — backfill du flag `actif` sur TOUTES les arêtes IS_DIRIGEANT.

Contexte : run_neo4j_rebuild ne (re)charge que ~10k sociétés par passage
(COMPANIES_LIMIT), donc 99,8 % des arêtes IS_DIRIGEANT gardaient un `actif=false`
figé d'un ancien import (source INPI : ~84 % de mandats actifs). Ce script
recalcule `actif` par (personne, siren) = statut du DERNIER dépôt
(individu_date_effet_role DESC) depuis bronze.inpi_formalites_personnes, en
réutilisant _person_uid pour matcher exactement la clé des nœuds Person.

Usage (depuis le conteneur agents-platform, cwd=/app) :
    docker exec -w /app demomea-agents-platform python backfill_dirigeant_actif.py
"""
from __future__ import annotations

import sys
import time

if "/app" not in sys.path:
    sys.path.insert(0, "/app")

import psycopg
from neo4j import GraphDatabase

from config import settings
from ingestion.neo4j_sync import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, _person_uid,
)

# Statut par (personne, siren) : bool_or (actif si AU MOINS un dépôt le marque
# actif) — hash aggregate rapide, pas de tri sur tableau (le DISTINCT ON trié
# sur individu_prenoms[] était trop lent sur 13M lignes).
SQL = """
SELECT siren, individu_nom, individu_prenoms, individu_date_naissance,
       bool_or(actif) AS actif
FROM bronze.inpi_formalites_personnes
WHERE type_de_personne = 'INDIVIDU'
  AND individu_nom IS NOT NULL
  AND siren IS NOT NULL
GROUP BY siren, individu_nom, individu_prenoms, individu_date_naissance
"""

CYPHER = """
UNWIND $rows AS row
MATCH (p:Person {uid: row.uid})-[r:IS_DIRIGEANT]->(c:Company {siren: row.siren})
SET r.actif = row.actif
"""

BATCH = 5000


def main() -> None:
    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    total_src = 0
    total_set = 0
    batch: list[dict] = []

    def flush(rows: list[dict]) -> int:
        if not rows:
            return 0
        with driver.session() as s:
            res = s.run(CYPHER, rows=rows).consume()
        return res.counters.properties_set

    with psycopg.connect(settings.database_url) as conn:
        # curseur serveur (stream) pour ne pas charger 13M lignes en RAM
        with conn.cursor(name="bf_actif") as cur:
            cur.itersize = 20000
            cur.execute(SQL)
            for siren, nom, prenoms, dn, actif in cur:
                total_src += 1
                batch.append({
                    "uid": _person_uid(nom, list(prenoms or []), dn),
                    "siren": siren,
                    "actif": bool(actif),
                })
                if len(batch) >= BATCH:
                    total_set += flush(batch)
                    batch = []
                    if total_src % 500000 == 0:
                        print(f"  ... {total_src} lignes source, {total_set} arêtes MAJ "
                              f"({int(time.time()-t0)}s)", flush=True)
            total_set += flush(batch)

    driver.close()
    print(f"DONE backfill actif : {total_src} lignes source -> {total_set} arêtes "
          f"IS_DIRIGEANT mises à jour en {int(time.time()-t0)}s", flush=True)


if __name__ == "__main__":
    main()
