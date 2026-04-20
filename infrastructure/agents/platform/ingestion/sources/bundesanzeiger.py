"""Bundesanzeiger — filiales DE.

Source #27 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://www.bundesanzeiger.de/api/v1/companies
Pas d'auth. Données publiques allemandes — licence Etalab 2.0 par défaut.
RGPD : pas de données sensibles, pas d'identifiants personnels (seulement SIREN/LEI via hrb_id).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

BUNDESANZEIGER_ENDPOINT = "https://www.bundesanzeiger.de/api/v1/companies"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k filiales par run — backfill complet via plusieurs invocations
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 720  # 30 jours (spec: refresh_trigger=720h)


async def fetch_bundesanzeiger_delta() -> dict:
    """Récupère les filiales allemandes Bundesanzeiger, upsert sur hrb_id.
    1er run : 365 jours ; runs suivants : 720h (couvre délai publication + refresh_trigger).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.bundesanzeiger_raw LIMIT 1")
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
                        "filter": f"founding_date:[{since} TO *]",
                    }
                    r = await client.get(BUNDESANZEIGER_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("Bundesanzeiger HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        hrb_id_raw = rec.get("hrb_id") or ""
                        hrb_id = _s(hrb_id_raw)
                        if not hrb_id:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.bundesanzeiger_raw
                                  (hrb_id, name, legal_form, city, founding_date, payload)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (hrb_id) DO UPDATE SET
                                  name = EXCLUDED.name,
                                  legal_form = EXCLUDED.legal_form,
                                  city = EXCLUDED.city,
                                  founding_date = EXCLUDED.founding_date,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    hrb_id[:64],
                                    _s(rec.get("name"))[:512],
                                    _s(rec.get("legal_form"))[:128],
                                    _s(rec.get("city"))[:255],
                                    _parse_date(rec.get("founding_date")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip hrb_id %s: %s", hrb_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "bundesanzeiger",
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


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None