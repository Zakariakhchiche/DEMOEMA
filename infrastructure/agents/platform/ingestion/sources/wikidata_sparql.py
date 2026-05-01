"""Wikidata Query Service — SPARQL FR humans + entreprises.

Source #11 d'ARCHITECTURE_DATA_V2.md. Endpoint public gratuit, sans auth.
Endpoint : https://query.wikidata.org/sparql
Licence : CC0 (public domain).

Deux requêtes paginées (OFFSET/LIMIT) :
  - humans_fr   : ~50K dirigeants / personnalités FR (QID, birth_year, ORCID, occupation)
  - companies_fr: ~50K entreprises FR (QID, SIREN, ISIN, LEI)

RGPD : birth_year uniquement (pas jour/mois), pas d'email/tél/adresse perso.
Usage : résolution d'entités SIREN↔LEI↔QID pour gold.dirigeants_master.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ENDPOINT = "https://query.wikidata.org/sparql"
PAGE_SIZE = 10000
MAX_PAGES_PER_RUN = 1000
BULK_BATCH_SIZE = 5000

HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "DEMOEMA-OSINT/1.0 (zkhchiche@hotmail.com)",
}

QUERY_HUMANS_FR = """SELECT ?qid ?label ?birth ?occupation ?wikipedia ?orcid ?employerLabel WHERE {
  ?qid wdt:P31 wd:Q5 .
  ?qid wdt:P27 wd:Q142 .
  OPTIONAL { ?qid rdfs:label ?label FILTER(LANG(?label) = "fr") }
  OPTIONAL { ?qid wdt:P569 ?birth }
  OPTIONAL { ?qid wdt:P106 ?occupation }
  OPTIONAL { ?qid wdt:P496 ?orcid }
  OPTIONAL { ?qid wdt:P108 ?employer .
             ?employer rdfs:label ?employerLabel FILTER(LANG(?employerLabel)="fr") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
LIMIT 50000
"""

QUERY_COMPANIES_FR = """SELECT ?qid ?label ?siren ?isin ?lei ?inception ?ceoLabel WHERE {
  ?qid wdt:P17 wd:Q142 .
  ?qid wdt:P31/wdt:P279* wd:Q4830453 .
  OPTIONAL { ?qid rdfs:label ?label FILTER(LANG(?label)="fr") }
  OPTIONAL { ?qid wdt:P1616 ?siren }
  OPTIONAL { ?qid wdt:P946 ?isin }
  OPTIONAL { ?qid wdt:P1278 ?lei }
  OPTIONAL { ?qid wdt:P571 ?inception }
  OPTIONAL { ?qid wdt:P169 ?ceo .
             ?ceo rdfs:label ?ceoLabel FILTER(LANG(?ceoLabel)="fr") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
LIMIT 50000
"""


def _s(value) -> str:
    """Convertit n'importe quelle valeur en str sûre (None → '')."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _extract_qid(uri: str | None) -> str:
    """http://www.wikidata.org/entity/Q42 → Q42."""
    if not uri:
        return ""
    return uri.split("/")[-1]


def _extract_year(date_str: str | None) -> int | None:
    """Extrait l'année depuis une date ISO Wikidata."""
    if not date_str:
        return None
    try:
        return int(str(date_str)[:4])
    except (ValueError, TypeError):
        return None


async def fetch_wikidata_sparql_delta() -> dict:
    """Récupère les entités Wikidata FR (humains + entreprises) via SPARQL.
    Full refresh hebdo avec upsert (ON CONFLICT DO UPDATE)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Détection first-run pour les métriques (pas de filtre temporel SPARQL ici)
    async with await psycopg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.wikidata_entreprises_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

    is_backfill = existing == 0
    mode = "backfill" if is_backfill else "incremental"

    total_fetched = 0
    total_inserted = 0
    total_errors = 0

    queries = [
        ("humans_fr", QUERY_HUMANS_FR),
        ("companies_fr", QUERY_COMPANIES_FR),
    ]

    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for query_name, query_template in queries:
                    offset = 0
                    for page in range(MAX_PAGES_PER_RUN):
                        query_paginated = query_template.replace(
                            "LIMIT 50000", f"OFFSET {offset} LIMIT {PAGE_SIZE}"
                        )

                        try:
                            r = await client.post(
                                ENDPOINT,
                                data={"query": query_paginated},
                                headers=HEADERS,
                            )
                        except Exception as e:
                            log.warning("Wikidata %s page %d: HTTP error %s", query_name, page, e)
                            break

                        if r.status_code != 200:
                            log.warning(
                                "Wikidata %s page %d: HTTP %s — %s",
                                query_name,
                                page,
                                r.status_code,
                                r.text[:200],
                            )
                            break

                        try:
                            data = r.json()
                        except Exception as e:
                            log.warning("Wikidata %s page %d: JSON parse error %s", query_name, page, e)
                            break

                        bindings = data.get("results", {}).get("bindings", [])
                        if not bindings:
                            break

                        batch: list[tuple] = []
                        for binding in bindings:
                            qid = _extract_qid(binding.get("qid", {}).get("value"))
                            if not qid:
                                total_errors += 1
                                continue

                            batch.append((
                                qid[:32],
                                _s(binding.get("label", {}).get("value"))[:512] or None,
                                _s(binding.get("siren", {}).get("value"))[:9] or None,
                                _s(binding.get("isin", {}).get("value"))[:12] or None,
                                _s(binding.get("lei", {}).get("value"))[:20] or None,
                                _s(binding.get("orcid", {}).get("value"))[:32] or None,
                                _extract_year(binding.get("birth", {}).get("value")),
                                _s(binding.get("occupation", {}).get("value"))[:256] or None,
                                Jsonb(binding),
                            ))

                            if len(batch) >= BULK_BATCH_SIZE:
                                try:
                                    await cur.executemany(
                                        """
                                        INSERT INTO bronze.wikidata_entreprises_raw
                                          (qid, label, siren, isin, lei, orcid, birth_year, occupation, payload, ingested_at)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                                        ON CONFLICT (qid) DO UPDATE SET payload = EXCLUDED.payload, ingested_at = NOW()
                                        """,
                                        batch,
                                    )
                                    total_inserted += cur.rowcount or 0
                                    await conn.commit()
                                except Exception as e:
                                    log.warning("Wikidata %s batch error: %s", query_name, e)
                                    total_errors += len(batch)
                                    # Sans rollback, la transaction reste en
                                    # état aborted → tous les batches suivants
                                    # échouent en cascade ("current transaction
                                    # is aborted, commands ignored").
                                    await conn.rollback()
                                batch.clear()

                        if batch:
                            try:
                                await cur.executemany(
                                    """
                                    INSERT INTO bronze.wikidata_entreprises_raw
                                      (qid, label, siren, isin, lei, orcid, birth_year, occupation, payload, ingested_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                                    ON CONFLICT (qid) DO UPDATE SET payload = EXCLUDED.payload, ingested_at = NOW()
                                    """,
                                    batch,
                                )
                                total_inserted += cur.rowcount or 0
                                await conn.commit()
                            except Exception as e:
                                log.warning("Wikidata %s final batch error: %s", query_name, e)
                                total_errors += len(batch)
                                await conn.rollback()
                            batch.clear()

                        fetched_page = len(bindings)
                        total_fetched += fetched_page
                        log.info(
                            "Wikidata %s page %d: fetched=%d, total_fetched=%d",
                            query_name,
                            page,
                            fetched_page,
                            total_fetched,
                        )

                        if fetched_page < PAGE_SIZE:
                            break

                        offset += PAGE_SIZE

    return {
        "source": "wikidata_sparql",
        "rows": total_inserted,
        "fetched": total_fetched,
        "errors": total_errors,
        "mode": mode,
    }