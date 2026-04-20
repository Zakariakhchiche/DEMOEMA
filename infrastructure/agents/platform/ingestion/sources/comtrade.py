"""UN Comtrade — commerce international.

Source #142 d'ARCHITECTURE_DATA_V2.md. API publique gratuite (UN open data).
Endpoint : https://comtradeapi.un.org/public/v1/preview
Pas d'auth. Rate-limit : 1 req/s, 100 req/jour.
RGPD : données agrégées pays/pays, pas d'entité personne physique → pas de traitement sensibles.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

COMTRADE_ENDPOINT = "https://comtradeapi.un.org/public/v1/preview"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~10k flows par run — suffisant pour delta quotidien
BACKFILL_DAYS_FIRST_RUN = 3650  # backfill 1 an pour couvrir historique
INCREMENTAL_HOURS = 72  # delta 3 jours (couvre délai publication + week-end)

async def fetch_comtrade_delta() -> dict:
    """Récupère les flux import/export Comtrade récents, dedup sur flow_id.
    1er run : 365 jours ; runs suivants : 72h (couvre délai publication + week-end)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.comtrade_flows_raw LIMIT 1")
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
                        "type": "C",
                        "freq": "A",
                        "px": "HS",
                        "ps": since,
                        "r": "all",
                        "p": "all",
                        "rg": "all",
                        "fmt": "json",
                        "offset": offset,
                        "limit": PAGE_SIZE,
                    }
                    try:
                        r = await client.get(COMTRADE_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("Comtrade timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("Comtrade HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    results = data.get("results", [])
                    if not results:
                        break
                    total_fetched += len(results)

                    # Upsert bronze
                    for rec in results:
                        flow_id = _build_flow_id(rec)
                        if not flow_id:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.comtrade_flows_raw
                                  (flow_id, period, reporter_iso, partner_iso, trade_flow,
                                   commodity_code, trade_value_usd, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (flow_id) DO UPDATE SET payload = EXCLUDED.payload,
                                    ingested_at = now()
                                """,
                                (
                                    flow_id[:64],
                                    _s(rec.get("period"))[:16],
                                    _s(rec.get("reporterISO"))[:8],
                                    _s(rec.get("partnerISO"))[:8],
                                    _s(rec.get("tradeFlow"))[:32],
                                    _s(rec.get("commodityCode"))[:16],
                                    _parse_numeric(rec.get("tradeValueUSDCustoms")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip flow %s: %s", flow_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(results) < PAGE_SIZE:
                        break

    return {
        "source": "comtrade",
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


def _build_flow_id(rec: dict) -> str | None:
    """Génère un flow_id unique à partir des clés naturelles."""
    try:
        r = rec.get("reporterISO", "")
        p = rec.get("partnerISO", "")
        y = rec.get("period", "")
        f = rec.get("tradeFlow", "")
        c = rec.get("commodityCode", "")
        if not all([r, p, y, f]):
            return None
        return f"{r}-{p}-{y}-{f}-{c}"
    except Exception:
        return None


def _parse_numeric(value) -> float | None:
    """Parse valeur numérique (USD) → NUMERIC Postgres."""
    if value is None:
        return None
    try:
        v = float(value)
        return v if not (v != v or v == float("inf") or v == float("-inf")) else None
    except (TypeError, ValueError):
        return None