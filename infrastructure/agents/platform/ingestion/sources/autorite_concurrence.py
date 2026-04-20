"""Autorité de la Concurrence — décisions ententes / concentrations.

Source #37 d'ARCHITECTURE_DATA_V2.md. API publique REST JSON.
Endpoint : https://www.autoritedelaconcurrence.fr/api/decisions
Pas d'auth. Rate-limit : 2 req/s. Licence publique.
RGPD : pas de données personnelles sensibles (seulement noms d'entités, dates, montants).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ADLC_ENDPOINT = "https://www.autoritedelaconcurrence.fr/api/decisions"
PAGE_SIZE = 50
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_autorite_concurrence_delta() -> dict:
    """Récupère les décisions ADLC récentes, dedup sur decision_id.
    1er run : 90 jours ; runs suivants : 48h (couvre délai publication officielle)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.adlc_decisions_raw LIMIT 1")
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
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "order_by": "date_decision DESC",
                        "filter[date_decision][gte]": since,
                    }
                    try:
                        r = await client.get(ADLC_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("ADLC timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("ADLC HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        decision_id_raw = rec.get("decision_id") or rec.get("id")
                        decision_id = _s(decision_id_raw)[:64]
                        if not decision_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.adlc_decisions_raw
                                  (decision_id, numero, type_decision, date_decision, parties, secteur, montant_amende, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (decision_id) DO NOTHING
                                """,
                                (
                                    decision_id,
                                    _s(rec.get("numero"))[:32],
                                    _s(rec.get("type_decision"))[:64],
                                    _parse_date(rec.get("date_decision")),
                                    _s(rec.get("parties")),
                                    _s(rec.get("secteur"))[:255],
                                    _parse_numeric(rec.get("montant_amende")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip decision %s: %s", decision_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "autorite_concurrence",
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


def _parse_numeric(s: str | int | float | None):
    if s is None:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


async def _fetch_one(cur):
    """Wrapper pour éviter l'ambiguïté avec psycopg 3.x."""
    return await cur.fetchone()