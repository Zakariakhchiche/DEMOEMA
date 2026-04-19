"""BOAMP — Bulletin Officiel des Annonces des Marchés Publics.

Source #46 d'ARCHITECTURE_DATA_V2.md. API publique gratuite via Opendatasoft.
Endpoint : https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records
Pas d'auth. License Etalab 2.0. Données publiées avec ~2-3j de délai typique.
RGPD : pas de données sensibles, pas d'identifiants personnes physiques (seulement acheteur/nom).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

BOAMP_ENDPOINT = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~3000 avis par run (sécurité quota)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_boamp_delta() -> dict:
    """Récupère les avis BOAMP récents, dedup sur avis_id.
    1er run : 30 jours ; runs suivants : 48h (couvre délai publication).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.boamp_avis_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    where = f"dateparution >= date'{since}'"
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
                        "order_by": "dateparution DESC",
                    }
                    r = await client.get(BOAMP_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("BOAMP HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        avis_id_raw = rec.get("idweb")
                        avis_id = _s(avis_id_raw)
                        if not avis_id:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.boamp_avis_raw
                                  (avis_id, date_parution, date_limite, objet, acheteur,
                                   cpv, type_avis, lieu_execution, montant_estime, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (avis_id) DO NOTHING
                                """,
                                (
                                    avis_id[:128],
                                    _parse_date(rec.get("dateparution")),
                                    _parse_date(rec.get("datelimitereponse")),
                                    _s(rec.get("objet"))[:10000],  # TEXT, pas de limite stricte mais on sécurise
                                    _s(rec.get("nomacheteur"))[:512],
                                    _s(rec.get("codecpv"))[:16],
                                    _s(rec.get("typeavis"))[:64],
                                    _s(rec.get("lieuexecution"))[:255],
                                    _parse_numeric(rec.get("montantestime")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip avis %s: %s", avis_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "boamp",
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


def _parse_numeric(s: str | int | float | None) -> float | None:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s_clean = _s(s).replace(" ", "").replace("€", "").replace(",", ".").strip()
    if not s_clean:
        return None
    try:
        return float(s_clean)
    except Exception:
        return None