"""CNIL sanctions — Amendes RGPD.

Source #36 d'ARCHITECTURE_DATA_V2.md. API publique JSON.
Endpoint : https://www.cnil.fr/fr/la-cnil-sanctionne/json
Pas d'auth. Licence Etalab 2.0 par défaut.
RGPD : données publiques (sanctions prononcées), pas de données sensibles.
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

CNIL_ENDPOINT = "https://www.cnil.fr/fr/la-cnil-sanctionne/json"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
# FULL historique par pagination (API ne fournit pas de bulk export)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 168  # 1 semaine (refresh_trigger=168h)
BULK_BATCH_SIZE = 1000


async def fetch_cnil_sanctions_delta() -> dict:
    """Récupère les sanctions CNIL récentes, dedup sur sanction_id.
    1er run : 365 jours ; runs suivants : 168h (1 semaine, correspond à la fréquence de rafraîchissement).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.cnil_sanctions_raw LIMIT 1")
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
                        "order_by": "date_sanction DESC",
                    }
                    # L'API CNIL ne supporte pas de filtre sur date via query params → on filtre en post-traitement
                    r = await client.get(CNIL_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("CNIL HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Filtrer les enregistrements trop anciens
                    filtered_records = []
                    for rec in records:
                        rec_date = _parse_date(rec.get("date_sanction"))
                        if rec_date and rec_date >= (datetime.now(tz=timezone.utc) - window).date():
                            filtered_records.append(rec)
                        elif existing == 0:
                            # Backfill : on garde tout (pas de filtre)
                            filtered_records.append(rec)
                        else:
                            # Pas de backfill et date trop ancienne → stop early
                            break

                    if not filtered_records:
                        break

                    # Upsert bronze
                    batch = []
                    for rec in filtered_records:
                        sanction_id = _s(rec.get("sanction_id"))
                        if not sanction_id:
                            total_skipped += 1
                            continue
                        try:
                            batch.append((
                                sanction_id[:64],
                                _s(rec.get("entite"))[:512],
                                _s(rec.get("siren"))[:9] if rec.get("siren") else None,
                                _parse_date(rec.get("date_sanction")),
                                _parse_numeric(rec.get("montant")),
                                _s(rec.get("motif")),
                                Jsonb(rec),
                            ))
                        except Exception as e:
                            log.warning("Skip record %s: %s", sanction_id, e)
                            total_skipped += 1
                            continue

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.cnil_sanctions_raw
                                  (sanction_id, entite, siren, date_sanction, montant, motif, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (sanction_id) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Batch error: %s", e)
                            total_skipped += len(batch)
                        batch.clear()

                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "cnil_sanctions",
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


def _parse_numeric(s: str | int | float | None):
    if s is None:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None