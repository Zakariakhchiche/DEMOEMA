"""Agreste — Stats agricoles (API publique sectorielle).

Source #133 d'ARCHITECTURE_DATA_V2.md. API publique sans auth, licence Etalab 2.0.
Endpoint : https://agreste.agriculture.gouv.fr/api/v1/series
Données agricoles par région, indicateur, année → pas d'entités personnes → pas de RGPD spécifique.
Ingestion bronze : stockage brut (payload JSON complet) + décomposition des champs clés.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

AGRESTE_ENDPOINT = "https://agreste.agriculture.gouv.fr/api/v1/series"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000  # ~100k lignes max par run — suffisant pour delta hebdo
BACKFILL_DAYS_FIRST_RUN = 3650  # backfill 1 an si table vide
INCREMENTAL_HOURS = 720  # 30 jours (720h) pour couvrir delta mensuel


async def fetch_agreste_delta() -> dict:
    """Récupère les séries Agreste récentes, upsert sur series_id.
    1er run : 365 jours ; runs suivants : 720h (delta mensuel).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.agreste_series_raw LIMIT 1")
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
                        "where": f"annee >= {datetime.now().year - 2}",
                    }
                    try:
                        r = await client.get(AGRESTE_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("Agreste timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("Agreste HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        series_id_raw = rec.get("series_id")
                        series_id = _s(series_id_raw)[:64]
                        if not series_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.agreste_series_raw
                                  (series_id, indicateur, region, annee, valeur, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (series_id) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    series_id,
                                    _s(rec.get("indicateur"))[:255],
                                    _s(rec.get("region"))[:64],
                                    _int(rec.get("annee")),
                                    _num(rec.get("valeur")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip series_id %s: %s", series_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "agreste",
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


def _int(value) -> int | None:
    """Convertit en int, None si impossible."""
    try:
        v = int(value)
        return v
    except (TypeError, ValueError):
        return None


def _num(value) -> float | None:
    """Convertit en NUMERIC (float), None si impossible."""
    try:
        v = float(value)
        return v
    except (TypeError, ValueError):
        return None