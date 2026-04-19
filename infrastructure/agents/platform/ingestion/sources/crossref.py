"""CrossRef — DOI, citations.

Source #61 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://api.crossref.org/works
Pas d'auth. Rate-limit raisonnable (~5 req/s). Licence Public / Etalab 2.0.
RGPD : pas de données personnelles sensibles (seulement DOI, titres, métadonnées bibliographiques).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

CROSSREF_ENDPOINT = "https://api.crossref.org/works"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000
# FULL historique non implémenté ici (trop volumineux : >100M DOI)
# → on se concentre sur les DOIs récents (delta)
INCREMENTAL_HOURS = 168  # 1 semaine (7×24h) pour couvrir la fréquence de rafraîchissement
BULK_BATCH_SIZE = 500  # commit tous les 500 rows


async def fetch_crossref_delta() -> dict:
    """Récupère les DOIs CrossRef récents (delta), dedup sur doi.
    1er run : 1 semaine ; runs suivants : 1 semaine (couvre la fréquence de rafraîchissement).
    Retourne {source, rows, fetched, skipped_existing, since}."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.crossref_works_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=365)  # backfill étendu pour la première ingestion
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    params = {
                        "rows": PAGE_SIZE,
                        "offset": offset,
                        "filter": f"from-pub-date:{since}",
                        "sort": "published",
                        "order": "asc",
                    }
                    r = await client.get(CROSSREF_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("CrossRef HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    items = data.get("message", {}).get("items", [])
                    if not items:
                        break
                    total_fetched += len(items)

                    # Upsert bronze
                    batch: list[tuple] = []
                    for rec in items:
                        doi_raw = rec.get("DOI")
                        doi = _s(doi_raw)
                        if not doi:
                            total_skipped += 1
                            continue

                        # Extraction des champs requis
                        title_raw = rec.get("title")
                        title = _s(title_raw[0] if isinstance(title_raw, list) and title_raw else title_raw)
                        publisher_raw = rec.get("publisher")
                        publisher = _s(publisher_raw) if publisher_raw else ""
                        published_raw = rec.get("published")
                        if isinstance(published_raw, dict):
                            date_parts = published_raw.get("date-parts")
                            if date_parts and date_parts[0]:
                                try:
                                    published_date = datetime(date_parts[0][0], date_parts[0][1] if len(date_parts[0]) > 1 else 1, date_parts[0][2] if len(date_parts[0]) > 2 else 1).date()
                                except Exception:
                                    published_date = None
                            else:
                                published_date = None
                        else:
                            published_date = None

                        ref_count_raw = rec.get("is-referenced-by-count")
                        ref_count = int(ref_count_raw) if isinstance(ref_count_raw, int) else 0

                        batch.append((
                            doi[:128],
                            title,
                            publisher[:255],
                            published_date,
                            ref_count,
                            Jsonb(rec),
                        ))

                        if len(batch) >= BULK_BATCH_SIZE:
                            try:
                                await cur.executemany(
                                    """
                                    INSERT INTO bronze.crossref_works_raw
                                      (doi, title, publisher, published_date, is_referenced_by_count, payload)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (doi) DO UPDATE SET
                                      payload = EXCLUDED.payload,
                                      ingested_at = now()
                                    """,
                                    batch,
                                )
                                total_inserted += cur.rowcount or 0
                                await conn.commit()
                                log.info("CrossRef bulk : %d inserted / %d fetched", total_inserted, total_fetched)
                            except Exception as e:
                                log.warning("Batch error: %s", e)
                                total_skipped += len(batch)
                            batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.crossref_works_raw
                                  (doi, title, publisher, published_date, is_referenced_by_count, payload)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (doi) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Final batch error: %s", e)

                    if len(items) < PAGE_SIZE:
                        break

    return {
        "source": "crossref",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped_existing": total_skipped,
        "since": since,
    }


def _s(value) -> str:
    """Convertit n'importe quelle valeur en str sûre pour slicing (None → '')."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        import json as _json
        return _json.dumps(value, ensure_ascii=False)
    return str(value)