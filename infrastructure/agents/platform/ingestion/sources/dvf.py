"""DVF — Transactions immobilières depuis 2014.

Source #70 d'ARCHITECTURE_DATA_V2.md. API publique gratuite via CQQuest.
Endpoint : https://api.cquest.org/dvf
Licence : Etalab 2.0 par défaut. Pas d'auth.
RGPD : données anonymisées (pas d'adresse précise, pas de nom vendeur/acquéreur).
Ne contient pas de données personnelles sensibles (pas de SIREN directement lié à une personne physique).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

DVF_ENDPOINT = "https://api.cquest.org/dvf"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000
# FULL historique par bulk export non disponible → pagination offset limitée à 10K
# → backfill étendu sur 365 jours pour première ingestion
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 720  # 30 jours (spec: interval_hours=720)
BULK_BATCH_SIZE = 1000


async def fetch_dvf_delta() -> dict:
    """Récupère les transactions DVF récentes, dedup sur mutation_id.
    1er run : 365 jours ; runs suivants : 720h (30 jours, couvre intervalle spec).
    Pagination offset limitée à 10K → on s'arrête à 200 pages (200K lignes max/run)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.dvf_transactions_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

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
                        "date_mutation": f">={since}",
                    }
                    try:
                        r = await client.get(DVF_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("DVF timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("DVF HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    batch: list[tuple] = []
                    for rec in records:
                        mutation_id_raw = rec.get("mutation_id") or rec.get("id")
                        mutation_id = _s(mutation_id_raw)
                        if not mutation_id:
                            total_skipped += 1
                            continue

                        # Conversion str() obligatoire pour éviter TypeError sur int/None
                        batch.append((
                            mutation_id[:64],
                            _parse_date(rec.get("date_mutation")),
                            _parse_numeric(rec.get("valeur_fonciere")),
                            _s(rec.get("code_postal"))[:8],
                            _s(rec.get("type_local"))[:64],
                            _parse_numeric(rec.get("surface_bati")),
                            _parse_numeric(rec.get("geo_lon")),
                            _parse_numeric(rec.get("geo_lat")),
                            Jsonb(rec),
                        ))

                        if len(batch) >= BULK_BATCH_SIZE:
                            try:
                                await cur.executemany(
                                    """
                                    INSERT INTO bronze.dvf_transactions_raw
                                      (mutation_id, date_mutation, valeur_fonciere, code_postal,
                                       type_local, surface_bati, geo_lon, geo_lat, payload)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (mutation_id) DO UPDATE SET
                                      payload = EXCLUDED.payload,
                                      ingested_at = now()
                                    """,
                                    batch,
                                )
                                total_inserted += cur.rowcount or 0
                                await conn.commit()
                                log.info("DVF batch : %d inserted / %d fetched", cur.rowcount or 0, len(batch))
                            except Exception as e:
                                log.warning("Batch error: %s", e)
                                total_skipped += len(batch)
                            batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.dvf_transactions_raw
                                  (mutation_id, date_mutation, valeur_fonciere, code_postal,
                                   type_local, surface_bati, geo_lon, geo_lat, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (mutation_id) DO UPDATE SET
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
        "source": "dvf",
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


def _parse_numeric(value) -> float | None:
    """Convertit en NUMERIC (float) en gérant les erreurs."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None