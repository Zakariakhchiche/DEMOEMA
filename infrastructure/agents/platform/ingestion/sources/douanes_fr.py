"""Douanes FR — import/export agrégé.

Source #143 d'ARCHITECTURE_DATA_V2.md. API publique gratuite via Lékiosque.
Endpoint : https://lekiosque.finances.gouv.fr/api/stats
Pas d'auth. Rate-limit raisonnable. Licence Etalab 2.0.
RGPD : données agrégées (pas de personnes physiques identifiables).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

DOUANES_ENDPOINT = "https://lekiosque.finances.gouv.fr/api/stats"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 720  # 30 jours → 720h (conforme à refresh_trigger=720h)


async def fetch_douanes_fr_delta() -> dict:
    """Récupère les flux douaniers import/export via API Lékiosque.
    1er run : 365 jours historique ; runs suivants : 720h (30j) → couvre refresh_trigger.
    Upsert sur flow_id (clé naturelle composite : periode+nc8+pays+sens+flow_id non fourni → on génère).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.douanes_fr_raw LIMIT 1")
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
                        "where": f"periode >= '{since}'",
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "order_by": "periode DESC",
                    }
                    try:
                        r = await client.get(DOUANES_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("Douanes FR timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("Douanes FR HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    batch = []
                    for rec in records:
                        # Générer flow_id composite (spec exige flow_id comme PK)
                        periode = _s(rec.get("periode"))
                        nc8 = _s(rec.get("nc8"))
                        pays = _s(rec.get("pays"))
                        sens = _s(rec.get("sens"))
                        flow_id = f"{periode}|{nc8}|{pays}|{sens}"
                        if not flow_id or len(flow_id) > 64:
                            total_skipped += 1
                            continue

                        # Conversion stricte des champs numériques
                        valeur_eur = _parse_numeric(rec.get("valeur_eur"))
                        poids_net = _parse_numeric(rec.get("poids_net"))

                        batch.append((
                            flow_id[:64],
                            periode[:16],
                            nc8[:16],
                            pays[:8],
                            sens[:16],
                            valeur_eur,
                            poids_net,
                            Jsonb(rec),
                        ))

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.douanes_fr_raw
                                  (flow_id, periode, nc8, pays, sens, valeur_eur, poids_net, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (flow_id) DO UPDATE SET
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
        "source": "douanes_fr",
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


def _parse_numeric(value) -> float | None:
    """Parse valeur_eur/poids_net en NUMERIC (None si vide/non convertible)."""
    if value is None:
        return None
    try:
        v = float(value)
        return v if not (v != v) else None  # NaN check
    except (TypeError, ValueError):
        return None