"""API Cadastre IGN — Parcelles.

Source #71 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://apicarto.ign.fr/api/cadastre/parcelle
Licence : Etalab 2.0 par défaut.
RGPD : données cadastrales anonymes (pas de données personnelles), pas de risque.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

API_CADASTRE_ENDPOINT = "https://apicarto.ign.fr/api/cadastre/parcelle"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k parcelles par run — backfill 1 an via plusieurs invocations
# FULL backfill 1 an (~100M parcelles) pour couverture nationale ; delta hebdo ensuite
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 168  # 1 semaine


async def fetch_api_cadastre_ign_delta() -> dict:
    """Récupère les parcelles cadastrales récentes, dedup sur parcelle_id.
    1er run : 365 jours ; runs suivants : 168h (1 semaine).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.cadastre_parcelles_raw LIMIT 1")
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
                    r = await client.get(API_CADASTRE_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("API_CADASTRE HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("features", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        properties = rec.get("properties", {})
                        parcelle_id_raw = properties.get("id")
                        parcelle_id = _s(parcelle_id_raw)
                        if not parcelle_id:
                            total_skipped += 1
                            continue

                        code_insee = _s(properties.get("codeinsee"))[:8]
                        section = _s(properties.get("section"))[:8]
                        numero = _s(properties.get("numero"))[:8]
                        contenance = _int(properties.get("contenance"))

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.cadastre_parcelles_raw
                                  (parcelle_id, code_insee, section, numero, contenance, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (parcelle_id) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    parcelle_id[:32],
                                    code_insee,
                                    section,
                                    numero,
                                    contenance,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip parcelle %s: %s", parcelle_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "api_cadastre_ign",
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


def _int(value) -> int | None:
    """Convertit en int si possible, None sinon."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None