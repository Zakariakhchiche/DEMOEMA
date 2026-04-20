"""Agribalyse — ACV agricoles.

Source #92 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://api.agribalyse.ademe.fr/api/v1/products
Licence : Etalab 2.0 (données publiques). Pas de données personnelles → pas de RGPD spécifique.
Pas d'auth. Rate-limit raisonnable (API publique ADEME).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

AGRIBALYSE_ENDPOINT = "https://api.agribalyse.ademe.fr/api/v1/products"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~10k produits par run — backfill complet ~10k produits
BACKFILL_DAYS_FIRST_RUN = 3650  # 10 ans pour couvrir historique complet (rarement mis à jour)
INCREMENTAL_HOURS = 720  # 30 jours pour delta (produits rarement modifiés)


async def fetch_agribalyse_delta() -> dict:
    """Récupère les produits Agribalyse, upsert sur ciqual_code.
    1er run : 10 ans ; runs suivants : 30 jours (couvre délai mise à jour).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.agribalyse_products_raw LIMIT 1")
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
                        "limit": PAGE_SIZE,
                        "offset": offset,
                    }
                    r = await client.get(AGRIBALYSE_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("Agribalyse HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        ciqual_code = _s(rec.get("ciqual_code"))
                        if not ciqual_code:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.agribalyse_products_raw
                                  (ciqual_code, label, gwp100, acidification, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, now())
                                ON CONFLICT (ciqual_code) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    ciqual_code[:16],
                                    _s(rec.get("label"))[:512],
                                    _to_numeric(rec.get("gwp100")),
                                    _to_numeric(rec.get("acidification")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip produit %s: %s", ciqual_code, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "agribalyse",
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


def _to_numeric(value) -> float | None:
    """Convertit en NUMERIC (float) avec gestion des erreurs."""
    try:
        v = _s(value)
        if v == "":
            return None
        return float(v)
    except (ValueError, TypeError):
        return None