"""Banque de France Webstat — endettement sectoriel.

Source #18 d'ARCHITECTURE_DATA_V2.md. API publique REST JSON sans auth.
Endpoint : https://api.webstat.banque-france.fr/webstat-fr/v1/data
Licence : Public / Etalab 2.0 par défaut.
RGPD : Aucune donnée personnelle — seules des séries chiffrées sectorielles.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

WEBSTAT_ENDPOINT = "https://api.webstat.banque-france.fr/webstat-fr/v1/data"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000  # ~100k séries par run — couvre l'ensemble des séries actives
BACKFILL_DAYS_FIRST_RUN = 3650  # backfill 1 an pour couvrir les séries historiques
INCREMENTAL_HOURS = 720  # 30 jours (720h) pour couvrir les mises à jour mensuelles


async def fetch_bdf_webstat_delta() -> dict:
    """Récupère les séries Webstat récentes, upsert sur series_key.
    1er run : 365 jours d'historique ; runs suivants : 720h (couvre mise à jour mensuelle).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.bdf_webstat_raw LIMIT 1")
            existing = (await _fetch_one(cur))[0]

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
                        "startPeriod": since,
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "format": "json",
                    }
                    try:
                        r = await client.get(WEBSTAT_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("Webstat timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("Webstat HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    series = data.get("data", [])
                    if not series:
                        break
                    total_fetched += len(series)

                    for rec in series:
                        series_key_raw = rec.get("id") or rec.get("series_key")
                        series_key = _s(series_key_raw)[:128]
                        if not series_key:
                            total_skipped += 1
                            continue

                        # Extraire les champs requis
                        date_period = _parse_date(rec.get("time_period"))
                        value_raw = rec.get("value")
                        value = float(value_raw) if value_raw is not None else None
                        indicator_name = _s(rec.get("indicator_name"))[:255]

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.bdf_webstat_raw
                                  (series_key, date_period, value, indicator_name, payload)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (series_key) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    series_key,
                                    date_period,
                                    value,
                                    indicator_name,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip series %s: %s", series_key, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(series) < PAGE_SIZE:
                        break

    return {
        "source": "bdf_webstat",
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
        # Webstat fournit souvent YYYY-MM-DD
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None


async def _fetch_one(cur) -> tuple:
    """Wrapper pour éviter l'erreur de type avec psycopg 3.1+."""
    res = await cur.fetchone()
    return res if res is not None else (None,)