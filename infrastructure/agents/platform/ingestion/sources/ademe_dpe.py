"""ADEME DPE — Diagnostic de Performance Énergétique.

Source #74 d'ARCHITECTURE_DATA_V2.md. API publique gratuite via Koumoul Data Fair.
Endpoint : https://koumoul.com/data-fair/api/v1/datasets/dpe-france/lines
Pas d'auth. Licence Etalab 2.0. RGPD : données anonymisées (pas d'identifiants personnes physiques).
Ingestion bronze uniquement — pas de parsing métier ici.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ADEME_DPE_ENDPOINT = "https://koumoul.com/data-fair/api/v1/datasets/dpe-france/lines"
PAGE_SIZE = 500
MAX_PAGES_PER_RUN = 1000  # ~100k DPE par run — couvre ~100k bâtiments/an (volumétrie estimée)
BACKFILL_DAYS_FIRST_RUN = 3650  # 1 an de données historiques pour first run
INCREMENTAL_HOURS = 72  # 3 jours de marge sur refresh_trigger=720h


async def fetch_ademe_dpe_delta() -> dict:
    """Récupère les DPE récents, upsert sur dpe_id (clé naturelle).
    1er run : 365 jours ; runs suivants : 72h (couvre refresh_trigger=720h + marge)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.ademe_dpe_raw LIMIT 1")
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
                        "where": f"date_visite >= date'{since}'",
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "order_by": "date_visite DESC",
                    }
                    r = await client.get(ADEME_DPE_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("ADEME DPE HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        dpe_id_raw = rec.get("id") or rec.get("dpe_id")
                        dpe_id = _s(dpe_id_raw)
                        if not dpe_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.ademe_dpe_raw
                                  (dpe_id, code_insee, surface_habitable, classe_consommation,
                                   classe_ges, date_visite, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (dpe_id) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    dpe_id[:64],
                                    _s(rec.get("code_insee"))[:8],
                                    _parse_numeric(rec.get("surface_habitable")),
                                    _s(rec.get("classe_consommation"))[:8],
                                    _s(rec.get("classe_ges"))[:8],
                                    _parse_date(rec.get("date_visite")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip DPE %s: %s", dpe_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "ademe_dpe",
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


def _parse_numeric(value) -> float | None:
    """Convertit en NUMERIC (float) avec gestion d'erreurs."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_date(s: str | None) -> datetime.date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None