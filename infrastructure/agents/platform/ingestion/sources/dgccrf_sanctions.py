"""DGCCRF sanctions — pratiques commerciales.

Source #38 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://www.economie.gouv.fr/dgccrf/api/sanctions
Licence : Etalab 2.0 par défaut. Aucune authentification.
RGPD : pas de données personnelles sensibles (nom, SIREN, montant, motif, date).
Pas de parsing métier ici — uniquement ingestion bronze.
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

DGCCRF_ENDPOINT = "https://www.economie.gouv.fr/dgccrf/api/sanctions"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48
BULK_BATCH_SIZE = 1000


async def fetch_dgccrf_sanctions_delta() -> dict:
    """Récupère les sanctions DGCCRF récentes, dedup sur sanction_id.
    1er run : 365 jours ; runs suivants : 48h (couvre délai publication).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.dgccrf_sanctions_raw LIMIT 1")
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
                        "order_by": "date_decision DESC",
                        "filter[date_decision][gte]": since,
                    }
                    try:
                        r = await client.get(DGCCRF_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("DGCCRF timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("DGCCRF HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    batch: list[tuple] = []
                    for rec in records:
                        sanction_id_raw = rec.get("id") or rec.get("sanction_id")
                        sanction_id = _s(sanction_id_raw)
                        if not sanction_id:
                            total_skipped += 1
                            continue

                        batch.append((
                            sanction_id[:64],
                            _s(rec.get("entreprise"))[:512],
                            _parse_date(rec.get("date_decision")),
                            _parse_numeric(rec.get("montant_amende")),
                            _s(rec.get("motif"))[:None],
                            Jsonb(rec),
                        ))

                        if len(batch) >= BULK_BATCH_SIZE:
                            try:
                                await cur.executemany(
                                    """
                                    INSERT INTO bronze.dgccrf_sanctions_raw
                                      (sanction_id, entreprise, date_decision, montant_amende, motif, payload)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (sanction_id) DO UPDATE SET
                                      payload = EXCLUDED.payload,
                                      ingested_at = now()
                                    """,
                                    batch,
                                )
                                total_inserted += cur.rowcount or 0
                                await conn.commit()
                                log.info("DGCCRF delta : %d inserted / %d fetched", total_inserted, total_fetched)
                            except Exception as e:
                                log.warning("Batch error: %s", e)
                                total_skipped += len(batch)
                            batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.dgccrf_sanctions_raw
                                  (sanction_id, entreprise, date_decision, montant_amende, motif, payload)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (sanction_id) DO UPDATE SET
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
        "source": "dgccrf_sanctions",
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
        return json.dumps(value, ensure_ascii=False)
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


def _parse_numeric(s: str | float | int | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None