"""ADEME Bilans GES — émissions CO2 obligatoires.

Source #84 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://bilans-ges.ademe.fr/api/v1/bilans-ges
Licence : Etalab 2.0. Pas de données personnelles sensibles (RGPD respecté).
Score scoring M&A dim 10 ESG.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ADEME_ENDPOINT = "https://bilans-ges.ademe.fr/api/v1/bilans-ges"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 720  # 30 jours → aligné sur spec interval_hours=720


async def fetch_ademe_bilans_ges_delta() -> dict:
    """Récupère les bilans GES entreprises >500 salariés, dedup sur bilan_id.
    1er run : 365 jours ; runs suivants : 720h (30 jours) — couvre délai publication.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.ademe_bilans_ges_raw LIMIT 1")
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
                        "order_by": "annee_reporting DESC",
                    }
                    r = await client.get(ADEME_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("ADEME HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        bilan_id_raw = rec.get("id") or rec.get("bilan_id")
                        bilan_id = _s(bilan_id_raw)
                        if not bilan_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.ademe_bilans_ges_raw
                                  (bilan_id, siren, raison_sociale, annee_reporting,
                                   emissions_scope1_tco2e, emissions_scope2_tco2e, emissions_scope3_tco2e,
                                   payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (bilan_id) DO UPDATE SET payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    bilan_id[:64],
                                    _s(rec.get("siren"))[:9],
                                    _s(rec.get("raison_sociale"))[:512],
                                    _int(rec.get("annee_reporting")),
                                    _numeric(rec.get("emissions_scope1_tco2e")),
                                    _numeric(rec.get("emissions_scope2_tco2e")),
                                    _numeric(rec.get("emissions_scope3_tco2e")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip bilan %s: %s", bilan_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "ademe_bilans_ges",
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


def _int(value) -> int | None:
    """Convertit en int si possible, None sinon."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _numeric(value) -> float | None:
    """Convertit en NUMERIC (float) si possible, None sinon."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None