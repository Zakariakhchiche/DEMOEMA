"""ANSM — Agence Nationale Sécurité Médicament.

Source #127 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://ansm.sante.fr/api/v1/decisions
Pas d'auth. Rate-limit : 3 req/s. License Etalab 2.0.
Données sensibles : pas d'information personnelle (pas de SIREN direct, pas d'adresse/email).
RGPD : on stocke uniquement les décisions (type, date, laboratoire, médicament, motif).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ANSM_ENDPOINT = "https://ansm.sante.fr/api/v1/decisions"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k décisions par run — backfill 1 an via plusieurs invocations
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_ansm_delta() -> dict:
    """Récupère les décisions ANSM récentes, dedup sur decision_id.
    1er run : 365 jours ; runs suivants : 48h (couvre délai publication).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.ansm_decisions_raw LIMIT 1")
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
                        "order": "date_decision DESC",
                        "filter[date_decision][gte]": since,
                    }
                    try:
                        r = await client.get(ANSM_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("ANSM timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("ANSM HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        decision_id_raw = rec.get("id") or rec.get("decision_id")
                        decision_id = _s(decision_id_raw)[:64]
                        if not decision_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.ansm_decisions_raw
                                  (decision_id, type_decision, date_decision, laboratoire,
                                   medicament_cis, motif, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (decision_id) DO NOTHING
                                """,
                                (
                                    decision_id,
                                    _s(rec.get("type_decision"))[:64],
                                    _parse_date(rec.get("date_decision")),
                                    _s(rec.get("laboratoire"))[:512],
                                    _s(rec.get("medicament_cis"))[:32],
                                    _s(rec.get("motif")),
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
        "source": "ansm",
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