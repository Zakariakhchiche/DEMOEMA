"""AMF BDIF — Franchissements seuils, déclarations dirigeants.

Source #22 d'ARCHITECTURE_DATA_V2.md. API publique REST/JSON.
Endpoint : https://bdif.amf-france.org/api/v1/declarations
Licence : Public / Etalab 2.0 par défaut.
RGPD : pas de données sensibles (seuils, pourcentages, ISIN, sociétés).
Ne contient pas d'emails/tél/adresses personnelles → conforme Y1.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

AMF_BDIF_ENDPOINT = "https://bdif.amf-france.org/api/v1/declarations"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k déclarations par run
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_amf_bdif_delta() -> dict:
    """Récupère les déclarations AMF BDIF récentes, dedup sur declaration_id.
    1er run : 365 jours ; runs suivants : 48h (couvre délai publication).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.amf_bdif_raw LIMIT 1")
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
                        "order": "date_declaration DESC",
                        "filter[date_declaration][gte]": since,
                    }
                    try:
                        r = await client.get(AMF_BDIF_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("AMF BDIF timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("AMF BDIF HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("data", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        declaration_id_raw = rec.get("id") or rec.get("declaration_id")
                        declaration_id = _s(declaration_id_raw)
                        if not declaration_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.amf_bdif_raw
                                  (declaration_id, isin, societe, date_declaration, type_seuil, pourcentage, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (declaration_id) DO UPDATE SET payload = EXCLUDED.payload, ingested_at = now()
                                """,
                                (
                                    declaration_id[:64],
                                    _s(rec.get("isin"))[:12],
                                    _s(rec.get("societe"))[:512],
                                    _parse_date(rec.get("date_declaration")),
                                    _s(rec.get("type_seuil"))[:64],
                                    _parse_numeric(rec.get("pourcentage")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip declaration %s: %s", declaration_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "amf_bdif",
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
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None