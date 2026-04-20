"""Eurostat — macro-éco UE.

Source #139 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data
Pas d'auth. Rate-limit : 2 req/s. Licence : Eurostat reuse policy — attribution requise.
RGPD : données agrégées (pays, période), pas d'individus identifiables.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

EUROSTAT_ENDPOINT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000  # ~10k records par run (sécurité quota)
# Fenêtre de backfill initial large (Eurostat publie avec 1-3 semaines de délai typique)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 72


async def fetch_eurostat_delta() -> dict:
    """Récupère les indicateurs macro UE récents, upsert sur (dataset_code, indicator_key).
    1er run : 60 jours ; runs suivants : 72h (couvre délai publication + hebdo).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.eurostat_indicators_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    # Filtrer les datasets prioritaires (cf. spec.datasets_priorité)
    datasets_to_fetch = ["nama_10_gdp", "sbs_na_sca_r2", "nrg_pc_202"]

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for dataset_code in datasets_to_fetch:
                    # Récupération paginée pour ce dataset
                    for page in range(MAX_PAGES_PER_RUN):
                        offset = page * PAGE_SIZE
                        params = {
                            "format": "json",
                            "startPeriod": since,
                            "dataset": dataset_code,
                            "offset": offset,
                            "limit": PAGE_SIZE,
                        }
                        try:
                            r = await client.get(EUROSTAT_ENDPOINT, params=params)
                        except httpx.TimeoutException:
                            log.warning("Eurostat timeout pour dataset=%s offset=%s", dataset_code, offset)
                            break
                        if r.status_code != 200:
                            log.warning("Eurostat HTTP %s: %s", r.status_code, r.text[:200])
                            break
                        data = r.json()
                        records = data.get("value", {})
                        if not records:
                            break

                        # Parse les dimensions (time, geo) depuis response structure
                        # Structure : { "value": { "key": value }, "dimension": { ... } }
                        # On reconstruit les enregistrements plats
                        dimensions = data.get("dimension", {})
                        time_ids = dimensions.get("time", {}).get("category", {}).get("index", {})
                        geo_ids = dimensions.get("geo", {}).get("category", {}).get("index", {})
                        time_labels = dimensions.get("time", {}).get("category", {}).get("label", {})
                        geo_labels = dimensions.get("geo", {}).get("category", {}).get("label", {})

                        for key, value in records.items():
                            parts = key.split(",")
                            if len(parts) < 2:
                                continue
                            time_id = parts[-1]
                            geo_id = parts[-2]
                            period = time_labels.get(time_id, time_id)
                            country = geo_labels.get(geo_id, geo_id)

                            # Clé composite pour upsert
                            indicator_key = f"{dataset_code}_{geo_id}_{time_id}"

                            try:
                                await cur.execute(
                                    """
                                    INSERT INTO bronze.eurostat_indicators_raw
                                      (dataset_code, indicator_key, country, period, value, payload)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (dataset_code, indicator_key) 
                                    DO UPDATE SET payload = EXCLUDED.payload, ingested_at = now()
                                    """,
                                    (
                                        dataset_code[:64],
                                        indicator_key[:128],
                                        country[:8],
                                        period[:16],
                                        float(value) if value is not None else None,
                                        Jsonb({
                                            "dataset_code": dataset_code,
                                            "indicator_key": indicator_key,
                                            "country": country,
                                            "period": period,
                                            "value": float(value) if value is not None else None,
                                            "raw_key": key,
                                            "time_id": time_id,
                                            "geo_id": geo_id,
                                        }),
                                    ),
                                )
                                if cur.rowcount > 0:
                                    total_inserted += 1
                                else:
                                    total_skipped += 1
                            except Exception as e:
                                log.warning("Skip record %s: %s", indicator_key, e)
                                total_skipped += 1

                        total_fetched += len(records)
                        if len(records) < PAGE_SIZE:
                            break

    return {
        "source": "eurostat",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped_existing": total_skipped,
        "since": since,
    }