"""BASIAS — anciens sites industriels et commerciaux.

Source #88 d'ARCHITECTURE_DATA_V2.md. API publique via data.gouv.fr.
Endpoint : https://www.data.gouv.fr/api/1/datasets/basias-sites-industriels/
Licence : Etalab 2.0 (public). Aucune donnée personnelle → pas de RGPD spécifique.
Pattern : REST JSON paginé, sans authentification.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

BASIAS_ENDPOINT = "https://www.data.gouv.fr/api/1/datasets/basias-sites-industriels/records/"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000  # ~10k enregistrements max par run (source ~80k totaux)
BACKFILL_DAYS_FIRST_RUN = 3650  # backfill complet si table vide
INCREMENTAL_HOURS = 24  # delta quotidien


async def fetch_basias_delta() -> dict:
    """Récupère les sites BASIAS récents, upsert sur code_basias.
    1er run : 365 jours de données (backfill complet) ; runs suivants : 24h.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.basias_sites_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
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
                        "limit": PAGE_SIZE,
                        "offset": offset,
                    }
                    r = await client.get(BASIAS_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("BASIAS HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        code_basias_raw = rec.get("code_basias")
                        code_basias = _s(code_basias_raw)
                        if not code_basias:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.basias_sites_raw
                                  (code_basias, raison_sociale, code_insee, activite_principale, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, now())
                                ON CONFLICT (code_basias) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    code_basias[:32],
                                    _s(rec.get("raison_sociale"))[:512],
                                    _s(rec.get("code_insee"))[:8],
                                    _s(rec.get("activite_principale")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip code_basias %s: %s", code_basias, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "basias",
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