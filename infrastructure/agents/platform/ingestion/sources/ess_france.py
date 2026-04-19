"""Observatoire ESS France — Source #131 ARCHITECTURE_DATA_V2.

API publique JSON, sans auth. Licence Etalab 2.0 par défaut.
Endpoint : https://ess-france.org/api/v1/entreprises
RGPD : pas de données sensibles (effectif, forme juridique, secteur, localisation).
Ne pas stocker d'emails/téléphones/adresses personnelles — source fournit SIRET uniquement.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ESS_ENDPOINT = "https://ess-france.org/api/v1/entreprises"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 720  # 30 jours → 720h (conforme à refresh_trigger=720h)


async def fetch_ess_france_delta() -> dict:
    """Récupère les entreprises de l'Observatoire ESS France (delta ou full).
    1er run : 365 jours d'historique ; runs suivants : 720h (30 jours).
    Upsert sur SIRET (clé naturelle), payload complet en JSONB.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.ess_entreprises_raw LIMIT 1")
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
                        "order_by": "updated_at DESC",
                        "filter[updated_at][gte]": since,
                    }
                    try:
                        r = await client.get(ESS_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("ESS France timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("ESS France HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("data", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        siret_raw = rec.get("id") or rec.get("siret")
                        siret = _s(siret_raw)
                        if not siret or len(siret) != 14 or not siret.isdigit():
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.ess_entreprises_raw
                                  (siret, denomination, forme_ess, effectif, departement, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (siret) DO UPDATE SET
                                  denomination = EXCLUDED.denomination,
                                  forme_ess = EXCLUDED.forme_ess,
                                  effectif = EXCLUDED.effectif,
                                  departement = EXCLUDED.departement,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    siret[:14],
                                    _s(rec.get("attributes", {}).get("denomination"))[:512],
                                    _s(rec.get("attributes", {}).get("forme_ess"))[:64],
                                    _int(rec.get("attributes", {}).get("effectif")),
                                    _s(rec.get("attributes", {}).get("departement"))[:8],
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip siret %s: %s", siret, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "ess_france",
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
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _int(value) -> int | None:
    """Convertit en int, None si non convertible."""
    try:
        v = int(value)
        return v if v >= 0 else None
    except (TypeError, ValueError):
        return None