"""CGSCOP — annuaire des coopératives (Scop.coop).

Source #132 d'ARCHITECTURE_DATA_V2.md. API publique REST/JSON sans auth.
Endpoint : https://les-scop.coop/api/v1/annuaire
Licence : Public / Etalab 2.0 par défaut.
RGPD : données uniquement juridiques (SIRET, denomination, NAF, type coopératif),
pas de données sensibles (pas de contacts, pas de données personnelles détaillées).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

CGSCOP_ENDPOINT = "https://les-scop.coop/api/v1/annuaire"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_cgscop_delta() -> dict:
    """Récupère les coopératives CGSCOP (annuaire en temps réel), dedup sur SIRET.
    1er run : 365 jours d'historique ; runs suivants : 48h (couvre délai mise à jour).
    Upsert conforme à conflict_strategy : ON CONFLICT (siret) DO UPDATE SET payload = EXCLUDED.payload, ingested_at = now().
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.cgscop_raw LIMIT 1")
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
                        "page": page + 1,
                        "per_page": PAGE_SIZE,
                        "updated_since": since,
                    }
                    try:
                        r = await client.get(CGSCOP_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("CGSCOP timeout after 30s on page %d", page)
                        break
                    if r.status_code != 200:
                        log.warning("CGSCOP HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("data", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        siret_raw = rec.get("siret")
                        siret = _s(siret_raw)
                        if not siret or len(siret) != 14:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.cgscop_raw
                                  (siret, denomination, type_cooperative, naf, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, now())
                                ON CONFLICT (siret) DO UPDATE SET
                                  denomination = EXCLUDED.denomination,
                                  type_cooperative = EXCLUDED.type_cooperative,
                                  naf = EXCLUDED.naf,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    siret,
                                    _s(rec.get("denomination"))[:512],
                                    _s(rec.get("type_cooperative"))[:64],
                                    _s(rec.get("naf"))[:8],
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip SIRET %s: %s", siret, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "cgscop",
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


async def _fetch_one(cursor) -> tuple:
    """Wrapper pour fetchone() qui gère les exceptions."""
    try:
        return await cursor.fetchone()
    except Exception:
        return (0,)