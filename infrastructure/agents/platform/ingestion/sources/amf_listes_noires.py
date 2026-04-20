"""AMF listes noires — entités non autorisées.

Source #81 d'ARCHITECTURE_DATA_V2.md. API publique via data.gouv.fr.
Endpoint : https://www.data.gouv.fr/api/1/datasets/liste-noire-amf/
Licence : Etalab 2.0 (Public). Aucune auth.
RGPD : données uniquement sur entités (personnes morales), pas de personnes physiques.
Pas de parsing métier ici — juste ingestion bronze.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

AMF_ENDPOINT = "https://www.data.gouv.fr/api/1/datasets/liste-noire-amf/"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~10k entités max — source petite (typiquement <5k entités)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 168  # 1 semaine (7j) → refresh_trigger=168h


async def fetch_amf_listes_noires_delta() -> dict:
    """Récupère les entités de la liste noire AMF, upsert sur entite_id.
    1er run : 365 jours de fenêtre (backfill historique) ; runs suivants : 168h (1 semaine).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.amf_listes_noires_raw LIMIT 1")
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
                # Récupération via l'API data.gouv.fr (JSON-LD + records via /records)
                # Endpoint réel : https://www.data.gouv.fr/api/1/datasets/liste-noire-amf/records
                # Note : data.gouv.fr expose souvent un endpoint /records en GET sans pagination
                # On tente d'abord un GET direct, puis fallback sur pagination si nécessaire
                params = {
                    "limit": PAGE_SIZE,
                    "offset": 0,
                }
                while True:
                    r = await client.get(f"{AMF_ENDPOINT}records", params=params)
                    if r.status_code != 200:
                        log.warning("AMF HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("records", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        try:
                            entite_id = _s(rec.get("id") or rec.get("entite_id") or "")
                            if not entite_id:
                                total_skipped += 1
                                continue

                            # Extraction des champs obligatoires
                            denomination = _s(rec.get("denomination") or "")
                            type_alerte = _s(rec.get("type_alerte") or rec.get("type") or "")
                            date_alerte = _parse_date(rec.get("date_alerte") or rec.get("date") or "")

                            # Upsert conforme à la spec : ON CONFLICT (entite_id) DO UPDATE SET payload = ..., ingested_at = now()
                            await cur.execute(
                                """
                                INSERT INTO bronze.amf_listes_noires_raw
                                  (entite_id, denomination, type_alerte, date_alerte, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, now())
                                ON CONFLICT (entite_id) DO UPDATE SET
                                  denomination = EXCLUDED.denomination,
                                  type_alerte = EXCLUDED.type_alerte,
                                  date_alerte = EXCLUDED.date_alerte,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    entite_id[:64],
                                    denomination[:512],
                                    type_alerte[:64],
                                    date_alerte,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip entité %s: %s", entite_id, e)
                            total_skipped += 1

                    # data.gouv.fr ne pagine pas toujours — on vérifie la présence de next offset
                    next_offset = data.get("next_offset")
                    if not next_offset:
                        break
                    params["offset"] = next_offset
                    if params["offset"] >= PAGE_SIZE * MAX_PAGES_PER_RUN:
                        break

                await conn.commit()

    return {
        "source": "amf_listes_noires",
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


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None