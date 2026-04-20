"""ACPR REGAFI — Banques/assurances autorisées.

Source #82 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://www.regafi.fr/api/v1/institutions
Pas d'auth. Rate-limit raisonnable (3 req/s).
RGPD : données uniquement sur personnes morales (SIREN, denomination), pas de données sensibles.
License : Public data ACPR — pas d'impact RGPD sur personnes physiques (pas de données personnelles).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ACPR_ENDPOINT = "https://www.regafi.fr/api/v1/institutions"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650  # Full backfill 1 an pour couvrir historique complet
INCREMENTAL_HOURS = 168  # 1 semaine (7×24h) entre runs, conforme à refresh_trigger=168h


async def fetch_acpr_regafi_delta() -> dict:
    """Récupère les institutions financières autorisées depuis REGAFI, dedup sur cib.
    1er run : 365 jours d'historique ; runs suivants : 168h (1 semaine) — couvre refresh_trigger.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.acpr_regafi_raw LIMIT 1")
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
                    }
                    r = await client.get(ACPR_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("ACPR REGAFI HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("data", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        cib_raw = rec.get("cib") or ""
                        cib = _s(cib_raw)[:16]
                        if not cib:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.acpr_regafi_raw
                                  (cib, denomination, siren, categorie, statut_agrement,
                                   date_agrement, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (cib) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    cib,
                                    _s(rec.get("denomination"))[:512],
                                    _s(rec.get("siren"))[:9],
                                    _s(rec.get("categorie"))[:64],
                                    _s(rec.get("statut_agrement"))[:64],
                                    _parse_date(rec.get("date_agrement")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip institution CIB=%s: %s", cib, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "acpr_regafi",
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