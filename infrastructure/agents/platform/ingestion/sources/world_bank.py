"""World Bank Open Data — indicateurs pays (PIB, démographie, GINI).

Source #141 d'ARCHITECTURE_DATA_V2.md. API publique REST JSON sans auth.
Endpoint : https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD
Licence : CC BY-4.0. RGPD : données agrégées pays uniquement (pas de personnes physiques).
Pattern : REST_JSON_WB (pagination par offset, rate-limit 5 req/s).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

WORLD_BANK_ENDPOINT = "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD"
PAGE_SIZE = 500
MAX_PAGES_PER_RUN = 1000
# Fenêtre backfill initiale large (données mondiales stables, pas de délai de publication)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_DAYS = 30


async def fetch_world_bank_delta() -> dict:
    """Récupère les indicateurs World Bank récents, upsert sur (country_code, indicator_code, year).
    1er run : 365 jours ; runs suivants : 30j (couvre délai publication + données révisées).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.world_bank_indicators_raw LIMIT 1")
            existing = (await _fetch_one(cur))[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(days=INCREMENTAL_DAYS)
    since_year = (datetime.now(tz=timezone.utc) - window).year
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    # Indicateurs prioritaires selon spec
    indicators = [
        "NY.GDP.MKTP.CD",
        "SL.UEM.TOTL.ZS",
        "SP.POP.TOTL",
    ]

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for indicator_code in indicators:
                    # Reset endpoint pour chaque indicateur
                    endpoint = f"https://api.worldbank.org/v2/country/all/indicator/{indicator_code}"
                    for page in range(MAX_PAGES_PER_RUN):
                        offset = page * PAGE_SIZE
                        params = {
                            "format": "json",
                            "date": f"{since_year}:",
                            "per_page": PAGE_SIZE,
                            "page": page + 1,
                        }
                        try:
                            r = await client.get(endpoint, params=params)
                        except httpx.TimeoutException:
                            log.warning("World Bank timeout (page %s, indicator %s)", page, indicator_code)
                            break
                        if r.status_code != 200:
                            log.warning("World Bank HTTP %s: %s", r.status_code, r.text[:200])
                            break
                        try:
                            data = r.json()
                        except ValueError:
                            log.warning("World Bank JSON parse error (page %s, indicator %s)", page, indicator_code)
                            break

                        # Structure : [metadata, records]
                        if not isinstance(data, list) or len(data) < 2:
                            break
                        records = data[1]
                        if not records:
                            break

                        total_fetched += len(records)

                        for rec in records:
                            try:
                                country = rec.get("country", {})
                                indicator = rec.get("indicator", {})
                                date_str = rec.get("date")
                                value = rec.get("value")

                                country_code = _s(country.get("id"))[:8]
                                country_name = _s(country.get("value"))[:255]
                                indicator_code_raw = _s(indicator.get("id"))[:64]
                                indicator_name = _s(indicator.get("value"))[:255]
                                year = _parse_year(date_str)
                                value_num = _parse_numeric(value)

                                if not country_code or not year:
                                    total_skipped += 1
                                    continue

                                payload = {
                                    "country": country,
                                    "indicator": indicator,
                                    "date": date_str,
                                    "value": value,
                                    "source": "world_bank",
                                    "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                                }

                                await cur.execute(
                                    """
                                    INSERT INTO bronze.world_bank_indicators_raw
                                      (country_code, country_name, indicator_code, indicator_name, year, value, payload)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (country_code, indicator_code, year) DO UPDATE SET
                                      country_name = EXCLUDED.country_name,
                                      indicator_name = EXCLUDED.indicator_name,
                                      value = EXCLUDED.value,
                                      payload = EXCLUDED.payload,
                                      ingested_at = now()
                                    """,
                                    (
                                        country_code,
                                        country_name,
                                        indicator_code_raw,
                                        indicator_name,
                                        year,
                                        value_num,
                                        Jsonb(payload),
                                    ),
                                )
                                if cur.rowcount > 0:
                                    total_inserted += 1
                                else:
                                    total_skipped += 1
                            except Exception as e:
                                log.warning("Skip record %s/%s/%s: %s", rec.get("country", {}).get("id"), indicator_code, rec.get("date"), e)
                                total_skipped += 1

                        if len(records) < PAGE_SIZE:
                            break

                await conn.commit()

    return {
        "source": "world_bank",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped_existing": total_skipped,
        "since_year": since_year,
    }


def _s(value) -> str:
    """Convertit n'importe quelle valeur en str sûre pour slicing (None → '')."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        import json as _json
        return _json.dumps(value, ensure_ascii=False)
    return str(value)


def _parse_year(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(s[:4])
    except (ValueError, TypeError):
        return None


def _parse_numeric(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


async def _fetch_one(cur) -> tuple:
    """Wrapper pour compatibilité psycopg 3.x (fetchone → fetchone)."""
    return await cur.fetchone()