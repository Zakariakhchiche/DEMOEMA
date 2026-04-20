"""ICPE — Installations Classées Protection Environnement (Géorisques).

Source #89 d'ARCHITECTURE_DATA_V2.md. API publique gratuite (Etalab 2.0).
Endpoint : https://www.georisques.gouv.fr/api/v1/installations_classees
Pas d'auth. Rate-limit : 5 req/s. SLA : 7j (168h rafraîchissement).
RGPD : pas de données sensibles (seulement code_aiot, raison_sociale, siret, regime, statut, code_commune, nature_exploitation).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ICPE_ENDPOINT = "https://www.georisques.gouv.fr/api/v1/installations_classees"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 168


async def fetch_icpe_delta() -> dict:
    """Récupère les installations ICPE récentes, upsert sur code_aiot.
    1er run : 365 jours ; runs suivants : 168h (hebdomadaire).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.icpe_installations_raw LIMIT 1")
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
                    }
                    r = await client.get(ICPE_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("ICPE HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("data", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        code_aiot_raw = rec.get("code_aiot")
                        code_aiot = _s(code_aiot_raw)[:32]
                        if not code_aiot:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.icpe_installations_raw
                                  (code_aiot, raison_sociale, siret, regime, statut, code_commune,
                                   nature_exploitation, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (code_aiot) DO UPDATE SET
                                  raison_sociale = EXCLUDED.raison_sociale,
                                  siret = EXCLUDED.siret,
                                  regime = EXCLUDED.regime,
                                  statut = EXCLUDED.statut,
                                  code_commune = EXCLUDED.code_commune,
                                  nature_exploitation = EXCLUDED.nature_exploitation,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    code_aiot,
                                    _s(rec.get("raison_sociale"))[:512],
                                    _s(rec.get("siret"))[:14],
                                    _s(rec.get("regime"))[:64],
                                    _s(rec.get("statut"))[:64],
                                    _s(rec.get("code_commune"))[:8],
                                    _s(rec.get("nature_exploitation")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip code_aiot %s: %s", code_aiot, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "icpe",
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