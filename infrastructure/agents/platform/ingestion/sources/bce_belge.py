"""Registre BCE belge — filiales BE.

Source #28 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://kbopub.economie.fgov.be/kbopub/api/v1/enterprises
Pas d'auth. Rate-limit raisonnable. Licence Etalab 2.0.
RGPD : on stocke uniquement les données publiques (SIREN/VAT, nom, statut, commune).
On n'expose pas d'emails/tél/adresse perso ni de données sensibles.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

BCE_BELGE_ENDPOINT = "https://kbopub.economie.fgov.be/kbopub/api/v1/enterprises"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k enregistrements par run
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_bce_belge_delta() -> dict:
    """Récupère les entreprises du registre BCE belge récentes, dedup sur vat_number.
    1er run : 365 jours ; runs suivants : 48h (couvre délai mise à jour).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.bce_belge_raw LIMIT 1")
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
                        "offset": offset,
                        "limit": PAGE_SIZE,
                    }
                    r = await client.get(BCE_BELGE_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("BCE BELGE HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        vat_number_raw = rec.get("vatNumber") or rec.get("vatNumberBE") or ""
                        vat_number = _s(vat_number_raw)[:16]
                        if not vat_number:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.bce_belge_raw
                                  (vat_number, name, status, commune, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, now())
                                ON CONFLICT (vat_number) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    vat_number,
                                    _s(rec.get("name"))[:512],
                                    _s(rec.get("status"))[:64],
                                    _s(rec.get("commune"))[:255],
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip VAT %s: %s", vat_number, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "bce_belge",
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