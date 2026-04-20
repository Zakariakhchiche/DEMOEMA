"""AMF GECO — décisions, agréments.

Source #23 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://geco.amf-france.org/api/v1/decisions
Pas d'auth. Rate-limit raisonnable. Licence Etalab 2.0 par défaut.
RGPD : on stocke uniquement les métadonnées (id, date, type, société, description),
pas de données personnelles sensibles (pas de nom/prénom, pas de coordonnées).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

AMF_GECO_ENDPOINT = "https://geco.amf-france.org/api/v1/decisions"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k décisions par run — backfill 1 an via plusieurs invocations
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_amf_geco_delta() -> dict:
    """Récupère les décisions AMF GECO récentes, dedup sur decision_id.
    1er run : 365 jours ; runs suivants : 48h (couvre délai publication).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.amf_geco_raw LIMIT 1")
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
                    }
                    r = await client.get(AMF_GECO_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("AMF GECO HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        decision_id_raw = rec.get("decision_id") or rec.get("id")
                        decision_id = _s(decision_id_raw)[:64]
                        if not decision_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.amf_geco_raw
                                  (decision_id, date_decision, type, societe, description, payload)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (decision_id) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    decision_id,
                                    _parse_date(rec.get("date_decision")),
                                    _s(rec.get("type"))[:64],
                                    _s(rec.get("societe"))[:512],
                                    _s(rec.get("description"))[:1024],
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
        "source": "amf_geco",
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