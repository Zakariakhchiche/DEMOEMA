"""Aides-entreprises.fr — Catalogue des aides publiques disponibles aux entreprises.

Source #104 d'ARCHITECTURE_DATA_V2.md. API publique gratuite sous licence Etalab 2.0.
Endpoint : https://aides-entreprises.fr/api/aides
Pas d'auth. Rate-limit : 3 req/s. Fenêtre incrémentale par défaut : 48h.
RGPD : données agrégées (pas d'individus), pas de traitement automatisé.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

AIDES_ENDPOINT = "https://aides-entreprises.fr/api/aides"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~10 000 aides par run (sécurité quota)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


async def fetch_aides_entreprises_delta() -> dict:
    """Récupère les aides récentes depuis aides-entreprises.fr, upsert sur aide_id.
    1er run : 30 jours ; runs suivants : 48h (couvre délai publication typique).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.aides_entreprises_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    where = f"dateDebut >= date'{since}'"
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
                        "order_by": "dateDebut DESC",
                    }
                    r = await client.get(AIDES_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("Aides-entreprises HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        aide_id_raw = rec.get("id") or ""
                        aide_id = _s(aide_id_raw)[:64]
                        if not aide_id:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.aides_entreprises_raw
                                  (aide_id, nom, operateur, type_aide, montant_min, montant_max, taux_max,
                                   date_debut, date_fin, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (aide_id) DO UPDATE SET payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    aide_id,
                                    _s(rec.get("nom"))[:512],
                                    _s(rec.get("operateur"))[:255],
                                    _s(rec.get("type"))[:64],
                                    _parse_numeric(rec.get("montantMin")),
                                    _parse_numeric(rec.get("montantMax")),
                                    _parse_numeric(rec.get("tauxMax")),
                                    _parse_date(rec.get("dateDebut")),
                                    _parse_date(rec.get("dateFin")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip aide %s: %s", aide_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "aides_entreprises",
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


def _parse_numeric(value):
    """Convertit une valeur numérique (int/float/str) en Decimal ou None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None