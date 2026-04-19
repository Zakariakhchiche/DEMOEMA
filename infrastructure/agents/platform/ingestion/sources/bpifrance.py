"""Bpifrance Open Data — prêts, garanties publiées.

Source #103 d'ARCHITECTURE_DATA_V2.md. API publique gratuite via OpenDataSoft.
Endpoint : https://data.bpifrance.fr/api/records/1.0/search
Licence Etalab 2.0. Aucune donnée personnelle sensible (pas d'email/tél/adresse).
RGPD : on stocke siren_beneficiaire (entité juridique), pas de données sensibles.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

BPIFRANCE_ENDPOINT = "https://data.bpifrance.fr/api/records/1.0/search"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 168  # 168h = 7 jours (hebdomadaire)


async def fetch_bpifrance_delta() -> dict:
    """Récupère les prêts/garanties Bpifrance récentes, dedup sur aide_id.
    1er run : 180 jours ; runs suivants : 168h (hebdo).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.bpifrance_aides_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    where = f"date_decision >= date'{since}'"
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
                        "refine.date_decision": since,
                        "rows": PAGE_SIZE,
                        "start": offset,
                        "sort": "date_decision desc",
                    }
                    r = await client.get(BPIFRANCE_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("Bpifrance HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("records", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        fields = rec.get("fields", {})
                        aide_id_raw = fields.get("aide_id")
                        aide_id = _s(aide_id_raw)[:64]
                        if not aide_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.bpifrance_aides_raw
                                  (aide_id, siren_beneficiaire, raison_sociale, programme, type_aide,
                                   montant, date_decision, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (aide_id) DO NOTHING
                                """,
                                (
                                    aide_id,
                                    _extract_siren(fields),
                                    _s(fields.get("raison_sociale"))[:512],
                                    _s(fields.get("programme"))[:128],
                                    _s(fields.get("type_aide"))[:64],
                                    _parse_numeric(fields.get("montant")),
                                    _parse_date(fields.get("date_decision")),
                                    Jsonb(fields),
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
        "source": "bpifrance",
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
    """Parse NUMERIC (montant) → float, None si invalide."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


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


def _extract_siren(fields: dict) -> str | None:
    """Extrait SIREN depuis les champs disponibles (siren_beneficiaire ou autre)."""
    # Priorité au champ direct
    siren = fields.get("siren_beneficiaire")
    if siren:
        s = str(siren)
        if len(s) >= 9 and s[:9].isdigit():
            return s[:9]

    # Fallback sur siren dans fields
    siren2 = fields.get("siren")
    if siren2:
        s = str(siren2)
        if len(s) >= 9 and s[:9].isdigit():
            return s[:9]

    return None