"""BRIS e-Justice EU — Base de données de sociétés européennes.

Source #137 d'ARCHITECTURE_DATA_V2.md. API publique gratuite (Etalab 2.0 par défaut).
Endpoint : https://e-justice.europa.eu/api/brs/v1/search
Pas d'auth. Rate-limit non documentée → on assume 10 req/min safe.
RGPD : on stocke uniquement les métadonnées (nom, pays, numéro d'entreprise, statut).
Aucune donnée sensible (email, SIREN non normalisé ici, pas de données personnelles fines).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

BRIS_ENDPOINT = "https://e-justice.europa.eu/api/brs/v1/search"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k enregistrements par run — backfill large puis delta
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_bris_ejustice_delta() -> dict:
    """Récupère les entreprises BRIS récentes, upsert sur entity_id.
    1er run : 365 jours ; runs suivants : 48h (couvre délai publication).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.bris_companies_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    params = {
                        "query": f"lastModified:[{since} TO *]",
                        "size": PAGE_SIZE,
                        "from": offset,
                    }
                    try:
                        r = await client.get(BRIS_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("BRIS timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("BRIS HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("hits", {}).get("hits", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        source_id = rec.get("_source", {})
                        entity_id_raw = source_id.get("entityId") or source_id.get("registrationNumber")
                        entity_id = _s(entity_id_raw)
                        if not entity_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.bris_companies_raw
                                  (entity_id, name, country, registration_number, status, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (entity_id) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    entity_id[:128],
                                    _s(source_id.get("name"))[:512],
                                    _s(source_id.get("country"))[:8],
                                    _s(source_id.get("registrationNumber"))[:64],
                                    _s(source_id.get("status"))[:64],
                                    Jsonb(source_id),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip entity %s: %s", entity_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "bris_ejustice",
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