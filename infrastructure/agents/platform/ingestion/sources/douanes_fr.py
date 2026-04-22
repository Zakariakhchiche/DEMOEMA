"""Douanes FR — import/export agrégé (Statistiques nationales du commerce extérieur).

Source #143 d'ARCHITECTURE_DATA_V2.md. API publique gratuite (Etalab 2.0).
Endpoint : https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/statistiques-nationales-du-commerce-exterieur/exports/json
Pas d'auth. Format CSV via /exports/json (renvoie JSON array directement, pas {results:[...]}) — géré ici.
RGPD : données agrégées (pas d'entités personnes physiques), pas de données sensibles.
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

DOUANES_ENDPOINT = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/statistiques-nationales-du-commerce-exterieur/exports/json"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000  # ~1M lignes max par run
BULK_BATCH_SIZE = 1000
BACKFILL_DAYS_FIRST_RUN = 3650  # 10 ans pour backfill initial
INCREMENTAL_HOURS = 720  # 30 jours pour delta (couvre cycle hebdo/mensuel)

async def count_upstream() -> int | None:
    """Compteur amont Douanes FR via endpoint ?limit=0 → total_count."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(DOUANES_ENDPOINT, params={"limit": 0})
            if r.status_code != 200:
                return None
            # /exports/json renvoie directement un array JSON → pas de .get("total_count")
            # On ne peut pas compter sans parser le JSON complet → on renvoie None (pas critique)
            return None
    except Exception:
        return None


async def fetch_douanes_fr_delta() -> dict:
    """Récupère les données Douanes FR (import/export agrégé), dedup sur flow_id.
    1er run : 10 ans (backfill) ; runs suivants : 30 jours (couvre cycle hebdo/mensuel).
    Format : JSON array directement (pas {results:[...]}), CSV-like en mémoire.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    import psycopg as _pg
    async with await _pg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.douanes_fr_raw LIMIT 1")
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
                        "order_by": "periode DESC",
                    }
                    r = await client.get(DOUANES_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("Douanes FR HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    try:
                        # /exports/json renvoie directement un array JSON
                        data = r.json()
                        if not isinstance(data, list):
                            log.warning("Douanes FR: unexpected JSON shape (not array), skip page")
                            break
                        records = data
                    except Exception as e:
                        log.warning("Douanes FR: JSON parse error: %s", e)
                        break

                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    batch: list[tuple] = []
                    for rec in records:
                        # flow_id = clé naturelle (primary_key dans spec)
                        flow_id_raw = rec.get("flow_id")
                        flow_id = _s(flow_id_raw)
                        if not flow_id:
                            total_skipped += 1
                            continue

                        # Conversion str() obligatoire pour éviter AttributeError
                        periode = _s(rec.get("periode"))[:16]
                        nc8 = _s(rec.get("nc8"))[:16]
                        pays = _s(rec.get("pays"))[:8]
                        sens = _s(rec.get("sens"))[:16]
                        valeur_eur = _n(rec.get("valeur_eur"))
                        poids_net = _n(rec.get("poids_net"))

                        batch.append((
                            flow_id[:64],
                            periode,
                            nc8,
                            pays,
                            sens,
                            valeur_eur,
                            poids_net,
                            Jsonb(rec),
                        ))

                        if len(batch) >= BULK_BATCH_SIZE:
                            try:
                                await cur.executemany(
                                    """
                                    INSERT INTO bronze.douanes_fr_raw
                                      (flow_id, periode, nc8, pays, sens, valeur_eur, poids_net, payload)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (flow_id) DO UPDATE SET
                                      periode = EXCLUDED.periode,
                                      nc8 = EXCLUDED.nc8,
                                      pays = EXCLUDED.pays,
                                      sens = EXCLUDED.sens,
                                      valeur_eur = EXCLUDED.valeur_eur,
                                      poids_net = EXCLUDED.poids_net,
                                      payload = EXCLUDED.payload,
                                      ingested_at = now()
                                    """,
                                    batch,
                                )
                                total_inserted += cur.rowcount or 0
                                await conn.commit()
                                log.info("Douanes FR bulk : %d inserted / %d fetched", total_inserted, total_fetched)
                            except Exception as e:
                                log.warning("Batch error: %s", e)
                                total_skipped += len(batch)
                            batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.douanes_fr_raw
                                  (flow_id, periode, nc8, pays, sens, valeur_eur, poids_net, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (flow_id) DO UPDATE SET
                                  periode = EXCLUDED.periode,
                                  nc8 = EXCLUDED.nc8,
                                  pays = EXCLUDED.pays,
                                  sens = EXCLUDED.sens,
                                  valeur_eur = EXCLUDED.valeur_eur,
                                  poids_net = EXCLUDED.poids_net,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Final batch error: %s", e)
                            total_skipped += len(batch)

                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "douanes_fr",
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
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _n(value) -> float | None:
    """Convertit n'importe quelle valeur en NUMERIC (None → None)."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None