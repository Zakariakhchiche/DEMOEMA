"""ADEME Base Carbone — facteurs émission.

Source #85 d'ARCHITECTURE_DATA_V2.md. API publique gratuite (Etalab 2.0).
Endpoint : https://data.ademe.fr/api/records/1.0/search
Pas d'auth. Données ouvertes — pas d'information personnelle → pas d'impact RGPD.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ADEME_ENDPOINT = "https://data.ademe.fr/api/records/1.0/search"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 1000  # ~20k facteurs max (source petite : ~15k facteurs en 2026)
BACKFILL_DAYS_FIRST_RUN = 3650  # backfill complet si bronze vide
INCREMENTAL_HOURS = 8760  # 1 an → delta journalier suffisant (source mise à jour annuellement)


async def fetch_ademe_base_carbone_delta() -> dict:
    """Récupère les facteurs émission ADEME Base Carbone, upsert sur facteur_id.
    1er run : backfill 1 an ; runs suivants : delta 1 an (source mise à jour annuelle).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.ademe_facteurs_raw LIMIT 1")
            existing = (await conn.fetchone())[0]

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
                        "dataset": "facteurs-emission",
                        "rows": PAGE_SIZE,
                        "start": offset,
                        "where": f"date_mise_a_jour >= '{since}'",
                        "sort": "date_mise_a_jour DESC",
                    }
                    r = await client.get(ADEME_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("ADEME HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("records", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        fields = rec.get("fields", {})
                        facteur_id_raw = fields.get("id") or fields.get("code")
                        facteur_id = _s(facteur_id_raw)
                        if not facteur_id:
                            total_skipped += 1
                            continue

                        # Extraction des champs requis
                        nom_base = _s(fields.get("nom_base"))[:512]
                        valeur = _parse_numeric(fields.get("valeur"))
                        unite = _s(fields.get("unite"))[:64]
                        source = _s(fields.get("source"))[:255]

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.ademe_facteurs_raw
                                  (facteur_id, nom_base, valeur, unite, source, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (facteur_id) DO UPDATE SET
                                  nom_base = EXCLUDED.nom_base,
                                  valeur = EXCLUDED.valeur,
                                  unite = EXCLUDED.unite,
                                  source = EXCLUDED.source,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    facteur_id[:64],
                                    nom_base,
                                    valeur,
                                    unite,
                                    source,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip facteur %s: %s", facteur_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "ademe_base_carbone",
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


def _parse_numeric(value) -> float | None:
    """Parse NUMERIC (float) avec gestion des erreurs."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None