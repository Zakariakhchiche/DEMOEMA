"""BDPM — Base de données publique des médicaments.

Source #128 d'ARCHITECTURE_DATA_V2.md. API publique gratuite (Etalab 2.0).
Endpoint : https://base-donnees-publique.medicaments.gouv.fr/api/v1/medicaments
Pas d'auth. Rate-limit raisonnable.
RGPD : données uniquement sur les médicaments (pas de personnes physiques).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

BDPM_ENDPOINT = "https://base-donnees-publique.medicaments.gouv.fr/api/v1/medicaments"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k médicaments par run — backfill complet via plusieurs invocations
BACKFILL_DAYS_FIRST_RUN = 3650  # 1 an de données historiques en premier run
INCREMENTAL_HOURS = 168  # 1 semaine (7 jours) entre runs, conformément à refresh_trigger=168h


async def fetch_bdpm_medicaments_delta() -> dict:
    """Récupère les médicaments BDPM récents, upsert sur cis (clé naturelle).
    1er run : 365 jours ; runs suivants : 168h (1 semaine), conformément à la fréquence de rafraîchissement.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.bdpm_medicaments_raw LIMIT 1")
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
                        "order": "dateAMM DESC",
                        "filter": f"dateAMM >= '{since}'",
                    }
                    r = await client.get(BDPM_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("BDPM HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("data", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze conforme à conflict_strategy
                    for rec in records:
                        cis_raw = rec.get("cis") or ""
                        cis = _s(cis_raw)[:32]
                        if not cis:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.bdpm_medicaments_raw
                                  (cis, payload)
                                VALUES (%s, %s)
                                ON CONFLICT (cis) DO UPDATE SET payload = EXCLUDED.payload, ingested_at = now()
                                """,
                                (
                                    cis,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip médicament CIS %s: %s", cis, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "bdpm_medicaments",
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