"""DARES — tensions métiers (Données sur l'emploi et le chômage).

Source #64 d'ARCHITECTURE_DATA_V2.md. API publique gratuite via OpenDataSoft.
Endpoint : https://data.dares.travail-emploi.gouv.fr/api/records/1.0/search
Licence : Etalab 2.0. Aucune donnée personnelle → pas d'impact RGPD.
Pattern : REST JSON paginé (offset/limit), pas de bulk export disponible.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

DARES_ENDPOINT = "https://data.dares.travail-emploi.gouv.fr/api/records/1.0/search"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
# FULL historique par pagination (API limitée à 10K records)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 168  # 1 semaine (7×24h) → aligné sur refresh_trigger=168h
BULK_BATCH_SIZE = 1000


async def fetch_dares_delta() -> dict:
    """Récupère les tensions métiers DARES (code_rome, région, indicateur, date).
    1er run : 365 jours ; runs suivants : 168h (1 semaine).
    Upsert sur clé naturelle (code_rome, region) → payload complet + timestamp."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.dares_tensions_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    where = f"date_observation >= date'{since}'"
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    params = {
                        "dataset": "tensions-metiers-regionales",
                        "q": "",
                        "refine.region": "",
                        "refine.code_rome": "",
                        "refine.date_observation": since,
                        "rows": PAGE_SIZE,
                        "start": offset,
                        "sort": "date_observation DESC",
                    }
                    try:
                        r = await client.get(DARES_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("DARES timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("DARES HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("records", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    batch: list[tuple] = []
                    for rec in records:
                        fields = rec.get("fields", {})
                        code_rome = _s(fields.get("code_rome"))
                        region = _s(fields.get("region"))
                        if not code_rome or not region:
                            total_skipped += 1
                            continue

                        tension_indicateur = fields.get("tension_indicateur")
                        tension_val = float(tension_indicateur) if tension_indicateur is not None else None

                        date_obs = _parse_date(fields.get("date_observation"))

                        payload = Jsonb(fields)

                        # Clé naturelle : (code_rome, region)
                        batch.append((
                            code_rome[:16],
                            region[:64],
                            tension_val,
                            date_obs,
                            payload,
                        ))

                        if len(batch) >= BULK_BATCH_SIZE:
                            try:
                                await cur.executemany(
                                    """
                                    INSERT INTO bronze.dares_tensions_raw
                                      (code_rome, region, tension_indicateur, date_observation, payload)
                                    VALUES (%s, %s, %s, %s, %s)
                                    ON CONFLICT (code_rome, region) DO UPDATE SET
                                      tension_indicateur = EXCLUDED.tension_indicateur,
                                      date_observation = EXCLUDED.date_observation,
                                      payload = EXCLUDED.payload,
                                      ingested_at = now()
                                    """,
                                    batch,
                                )
                                total_inserted += cur.rowcount or 0
                                await conn.commit()
                                log.info("DARES batch : %d inserted / %d fetched", cur.rowcount, len(batch))
                            except Exception as e:
                                log.warning("Batch error: %s", e)
                                total_skipped += len(batch)
                            batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.dares_tensions_raw
                                  (code_rome, region, tension_indicateur, date_observation, payload)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (code_rome, region) DO UPDATE SET
                                  tension_indicateur = EXCLUDED.tension_indicateur,
                                  date_observation = EXCLUDED.date_observation,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Final batch error: %s", e)
                            total_skipped += len(batch)

                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "dares",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped": total_skipped,
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