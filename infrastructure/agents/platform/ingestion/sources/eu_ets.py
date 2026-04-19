"""EU ETS EUTL — Quotas CO2 industriels.

Source #86 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://www.eea.europa.eu/data-and-maps/data/european-union-emissions-trading-scheme-17/eu-ets-data-download-latest-version.json
Pas d'auth. Données sous licence Etalab 2.0 (par défaut).
RGPD : données agrégées par installation (pas d'individus), pas de données sensibles.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

EU_ETS_ENDPOINT = "https://www.eea.europa.eu/data-and-maps/data/european-union-emissions-trading-scheme-17/eu-ets-data-download-latest-version.json"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 720  # 30 jours → couvre cycle de mise à jour EUTL (mensuel + corrections)


async def fetch_eu_ets_delta() -> dict:
    """Récupère les données EU ETS (quotas CO2 industriels) via API REST JSON.
    1er run : 365 jours historique ; runs suivants : 720h (30 jours) pour couvrir les mises à jour mensuelles.
    Upsert sur account_id (clé naturelle unique dans EUTL)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.eu_ets_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")

    total_fetched = 0
    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    params = {
                        "limit": PAGE_SIZE,
                        "offset": offset,
                    }
                    try:
                        r = await client.get(EU_ETS_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("EU ETS timeout at page %d", page)
                        break
                    except Exception as e:
                        log.warning("EU ETS network error at page %d: %s", page, e)
                        break

                    if r.status_code != 200:
                        log.warning("EU ETS HTTP %s: %s", r.status_code, r.text[:200])
                        break

                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    batch: list[tuple] = []
                    for rec in records:
                        account_id_raw = rec.get("account_id")
                        account_id = _s(account_id_raw)
                        if not account_id:
                            total_skipped += 1
                            continue

                        # Extract fields with safe conversion
                        installation_id = _s(rec.get("installation_id"))
                        name = _s(rec.get("name"))
                        country = _s(rec.get("country"))
                        year = _i(rec.get("year"))
                        emissions_tco2 = _n(rec.get("emissions_tco2"))

                        batch.append((
                            account_id[:64],
                            installation_id[:64],
                            name[:512],
                            country[:8],
                            year,
                            emissions_tco2,
                            Jsonb(rec),
                        ))

                        if len(batch) >= PAGE_SIZE:
                            try:
                                await cur.executemany(
                                    """
                                    INSERT INTO bronze.eu_ets_raw
                                      (account_id, installation_id, name, country, year, emissions_tco2, payload)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (account_id) DO UPDATE SET
                                      payload = EXCLUDED.payload,
                                      ingested_at = now()
                                    """,
                                    batch,
                                )
                                total_inserted += cur.rowcount or 0
                                await conn.commit()
                            except Exception as e:
                                log.warning("Batch error: %s", e)
                                total_errors += len(batch)
                            batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.eu_ets_raw
                                  (account_id, installation_id, name, country, year, emissions_tco2, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (account_id) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Final batch error: %s", e)
                            total_errors += len(batch)

                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "eu_ets",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped": total_skipped,
        "errors": total_errors,
        "since": since,
    }


def _s(value) -> str:
    """Convertit n'importe quelle valeur en str sûre pour slicing (None → '')."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _i(value) -> int | None:
    """Convertit en int, None si impossible."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _n(value) -> float | None:
    """Convertit en NUMERIC (float), None si impossible."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None