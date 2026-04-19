"""Conseil d'État — ArianeWeb jurisprudence administrative.

Source #40 d'ARCHITECTURE_DATA_V2.md. API publique gratuite via data.gouv.fr.
Endpoint : https://www.conseil-etat.fr/api/arianeweb/v1/search
Licence : Open Licence 2.0 via data.gouv.fr.
RGPD : pas de données personnelles sensibles (seulement dates, solutions, résumés).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

CONSEIL_ETAT_ENDPOINT = "https://www.conseil-etat.fr/api/arianeweb/v1/search"
PAGE_SIZE = 50
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_conseil_etat_delta() -> dict:
    """Récupère les décisions CE + CAA récentes via ArianeWeb, dedup sur decision_id.
    1er run : 30 jours ; runs suivants : 48h (couvre délai publication officielle)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.conseil_etat_decisions_raw LIMIT 1")
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
                        "q": f"date_lecture:[{since}T00:00:00Z TO *]",
                        "rows": PAGE_SIZE,
                        "start": offset,
                        "sort": "date_lecture desc",
                    }
                    r = await client.get(CONSEIL_ETAT_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("Conseil d'État HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("response", {}).get("docs", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        decision_id_raw = rec.get("decision_id") or rec.get("id") or ""
                        decision_id = _s(decision_id_raw)[:64]
                        if not decision_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.conseil_etat_decisions_raw
                                  (decision_id, numero, formation, date_lecture, solution, resume, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (decision_id) DO NOTHING
                                """,
                                (
                                    decision_id,
                                    _s(rec.get("numero"))[:32],
                                    _s(rec.get("formation"))[:64],
                                    _parse_date(rec.get("date_lecture")),
                                    _s(rec.get("solution"))[:128],
                                    _s(rec.get("resume")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip décision %s: %s", decision_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "conseil_etat",
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
        # Format ISO8601 (ex: "2024-03-15T00:00:00Z")
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        try:
            # Format date simple (ex: "2024-03-15")
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None