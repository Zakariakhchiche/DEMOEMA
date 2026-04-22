"""URSSAF Open Data — données trimestrielles cotisants.

Source #32 d'ARCHITECTURE_DATA_V2.md. API publique gratuite (Etalab 2.0).
Endpoint : https://open.urssaf.fr/api/explore/v2.1/catalog/datasets/effectifs-salaries-et-masse-salariale-du-secteur-prive-par-departement-x-grand-s/records
Pas d'auth. Rate-limit raisonnable.

RGPD : données agrégées (département/trimestre), pas d'information individuelle.
Ne pas stocker d'identifiants personnels ou de données sensibles.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

URSSAF_ENDPOINT = "https://open.urssaf.fr/api/explore/v2.1/catalog/datasets/effectifs-salaries-et-masse-salariale-du-secteur-prive-par-departement-x-grand-s/records"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000
# FULL historique par bulk export non disponible → delta étendu pour backfill
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 87600


async def count_upstream() -> int | None:
    """Compteur amont URSSAF via OpenDataSoft (endpoint ?limit=0 → total_count)."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(URSSAF_ENDPOINT, params={"limit": 0})
            if r.status_code != 200:
                return None
            v = r.json().get("total_count")
            return int(v) if isinstance(v, int) and v >= 0 else None
    except Exception:
        return None


async def fetch_urssaf_opendata_delta() -> dict:
    """Récupère les données URSSAF trimestrielles récentes, dedup sur record_id.
    1er run : 10 ans (backfill complet) ; runs suivants : 10 ans (données trimestrielles stables).
    
    Pattern : loop de pages avec offset+limit, insert par page.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.urssaf_trimestriel_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    where = f"trimestre >= '{since[:4]}'"
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    params = {
                        "where": where,
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "order_by": "trimestre DESC",
                    }
                    r = await client.get(URSSAF_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("URSSAF HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    batch = []
                    for rec in records:
                        # Clé naturelle : concaténation des 4 dimensions
                        record_id = (
                            f"{_s(rec.get('secteur', ''))}__"
                            f"{_s(rec.get('departement', ''))}__"
                            f"{_s(rec.get('trimestre', ''))}__"
                            f"{_s(rec.get('annee', ''))}"
                        )
                        if not record_id or len(record_id) > 64:
                            total_skipped += 1
                            continue

                        # Conversion str() obligatoire avant slicing
                        batch.append((
                            record_id[:64],
                            _s(rec.get("secteur"))[:128],
                            _s(rec.get("departement"))[:8],
                            _s(rec.get("trimestre"))[:16],
                            int(rec.get("nb_cotisants")) if rec.get("nb_cotisants") is not None else None,
                            float(rec.get("masse_salariale")) if rec.get("masse_salariale") is not None else None,
                            Jsonb(rec),
                        ))

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.urssaf_trimestriel_raw
                                  (record_id, secteur, departement, trimestre, nb_cotisants, masse_salariale, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (record_id) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Batch error: %s", e)
                            # Retry en ligne à ligne en cas d'erreur batch
                            for row in batch:
                                try:
                                    await cur.execute(
                                        """
                                        INSERT INTO bronze.urssaf_trimestriel_raw
                                          (record_id, secteur, departement, trimestre, nb_cotisants, masse_salariale, payload)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (record_id) DO UPDATE SET
                                          payload = EXCLUDED.payload,
                                          ingested_at = now()
                                        """,
                                        row,
                                    )
                                    if cur.rowcount > 0:
                                        total_inserted += 1
                                    else:
                                        total_skipped += 1
                                except Exception as e2:
                                    log.warning("Row error: %s", e2)
                                    total_skipped += 1
                            await conn.commit()

                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "urssaf_opendata",
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