"""APEC Open Data — offres cadres.

Source #67 d'ARCHITECTURE_DATA_V2.md. API publique gratuite via Opendatasoft.
Endpoint : https://data.apec.fr/api/records/1.0/search
Licence Etalab 2.0. Pas d'auth. RGPD : données anonymisées (pas d'infos personnelles).
Pas de parsing métier ici — uniquement ingestion bronze.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

APEC_ENDPOINT = "https://data.apec.fr/api/records/1.0/search"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_apec_delta() -> dict:
    """Récupère les offres d'emploi cadres APEC récentes, dedup sur offre_id.
    1er run : 14 jours ; runs suivants : 48h (couvre délai publication).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.apec_offres_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    where = f"date_publication >= date'{since}'"
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    params = {
                        "q": "",
                        "rows": PAGE_SIZE,
                        "start": offset,
                        "sort": "date_publication desc",
                        "refine.date_publication": f"[{since} TO *]",
                    }
                    r = await client.get(APEC_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("APEC HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("records", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        fields = rec.get("fields", {})
                        offre_id_raw = fields.get("offre_id")
                        offre_id = _s(offre_id_raw)
                        if not offre_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.apec_offres_raw
                                  (offre_id, intitule, entreprise, siren, lieu, date_publication,
                                   type_contrat, fonction, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (offre_id) DO NOTHING
                                """,
                                (
                                    offre_id[:64],
                                    _s(fields.get("intitule"))[:512],
                                    _s(fields.get("entreprise"))[:512],
                                    _s(fields.get("siren"))[:9] if fields.get("siren") else None,
                                    _s(fields.get("lieu"))[:255],
                                    _parse_date(fields.get("date_publication")),
                                    _s(fields.get("type_contrat"))[:32],
                                    _s(fields.get("fonction"))[:128],
                                    Jsonb(fields),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip offre %s: %s", offre_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "apec",
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