"""ESANE INSEE — benchmarks sectoriels CA/marge.

Source #17 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://www.insee.fr/fr/statistiques/esane/data.json
Pas d'auth. License Etalab 2.0 par défaut.
RGPD : données agrégées sectorielles (pas d'entités individuelles) → pas de traitement spécifique.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ESANE_ENDPOINT = "https://www.insee.fr/fr/statistiques/esane/data.json"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 8760  # 1 an (spec: refresh_trigger=8760h)
BULK_BATCH_SIZE = 1000


async def fetch_esane_delta() -> dict:
    """Récupère les benchmarks sectoriels ESANE (CA/marge/nb entrep.) via API publique.
    1er run : 365 jours d'historique ; runs suivants : 1 an (couvre cycle annuel de mise à jour).
    Upsert sur (naf, annee) avec payload complet.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.esane_sectoriels_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

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
                        "where": f"date_mise_a_jour >= date'{since}'",
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "order_by": "date_mise_a_jour DESC",
                    }
                    try:
                        r = await client.get(ESANE_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("ESANE timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("ESANE HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    batch: list[tuple] = []
                    for rec in records:
                        naf = _s(rec.get("naf") or "")
                        annee = _i(rec.get("annee"))
                        if not naf or not annee:
                            total_skipped += 1
                            continue
                        batch.append((
                            naf[:8],
                            annee,
                            _n(rec.get("ca_median")),
                            _n(rec.get("marge_mediane")),
                            _i(rec.get("nb_entreprises")),
                            Jsonb(rec),
                        ))

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.esane_sectoriels_raw
                                  (naf, annee, ca_median, marge_mediane, nb_entreprises, payload)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (naf, annee) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Batch error: %s", e)
                            total_skipped += len(batch)
                        batch.clear()

                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "esane",
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


def _i(value) -> int | None:
    """Convertit en int, None si impossible."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _n(value) -> float | None:
    """Convertit en NUMERIC (float), None si impossible."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None