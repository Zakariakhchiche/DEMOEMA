"""API Cadastre IGN — parcelles — fetcher auto-généré (template rest_json_ods).

Source : api_cadastre_ign
Endpoint OpenDataSoft v2.1 : https://data.rennesmetropole.fr/api/records/1.0/search/?dataset=cadastre-parcelles
Licence : Public / Etalab 2.0 par défaut
Auth : none
Auto-généré par codegen template-first.
"""
from __future__ import annotations

import hashlib
import json as _json
import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ENDPOINT = "https://data.rennesmetropole.fr/api/records/1.0/search/"
DATASET = "cadastre-parcelles"
PAGE_SIZE = 100
MAX_PAGES = 100
BACKFILL_DAYS = 3650
INCREMENTAL_HOURS = 48


def _extract_records(js):
    """ODS v1 → {records:[{fields:...}]}, v2 → {results:[...]}, exports → [...]. Normalize."""
    if isinstance(js, list):
        return js
    if isinstance(js, dict):
        recs = js.get("results") or js.get("records") or []
        # Unwrap ODS v1 "fields" shape
        if recs and isinstance(recs[0], dict) and "fields" in recs[0]:
            return [r.get("fields") or {} for r in recs]
        return recs
    return []


async def count_upstream() -> int | None:
    """Total count amont — ODS v1 /search?rows=0 → nhits, v2 /records?limit=0 → total_count."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(ENDPOINT, params={"dataset": DATASET, "rows": 0, "limit": 0})
            if r.status_code != 200:
                return None
            js = r.json()
            if not isinstance(js, dict):
                return None
            v = js.get("total_count") or js.get("nhits")
            return int(v) if isinstance(v, int) and v >= 0 else None
    except Exception:
        return None


async def fetch_api_cadastre_ign_delta() -> dict:
    """Fetch delta ODS v2.1 — paginated with offset+limit."""
    if not settings.database_url:
        return {"source": "api_cadastre_ign", "rows": 0, "error": "no DB"}

    # Check table vide → backfill, sinon delta
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.api_cadastre_ign_raw")
            existing = (await cur.fetchone())[0]

    window = timedelta(days=BACKFILL_DAYS) if existing == 0 else timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")

    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES):
                    offset = page * PAGE_SIZE
                    # ODS v1 uses rows+start, v2 uses limit+offset. Pass both — unknown keys ignored.
                    params = {
                        "dataset": DATASET,
                        "rows": PAGE_SIZE, "start": offset,
                        "limit": PAGE_SIZE, "offset": offset,
                    }
                    r = await client.get(ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("api_cadastre_ign HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    records = _extract_records(r.json())
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        # Cascade clé : key_field → id → hash payload
                        key_val = rec.get("record_id") or rec.get("id")
                        if not key_val:
                            key_val = hashlib.sha1(
                                _json.dumps(rec, sort_keys=True, default=str).encode()
                            ).hexdigest()[:32]
                        key_str = str(key_val)[:128]
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.api_cadastre_ign_raw (record_id, payload, ingested_at)
                                VALUES (%s, %s, now())
                                ON CONFLICT (record_id) DO NOTHING
                                """,
                                (key_str, Jsonb(rec)),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("skip %s: %s", key_str[:30], e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "api_cadastre_ign",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped_existing": total_skipped,
        "since": since,
    }
