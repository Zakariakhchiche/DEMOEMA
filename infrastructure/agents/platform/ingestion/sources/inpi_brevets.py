"""INPI Brevets — dépôts FR depuis 1902.

Source #51 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://data.inpi.fr/api/brevets/search
Licence : Etalab 2.0 — pas de RGPD spécifique (données anonymisées : pas d'email/tel/nom complet, pas de date de naissance précise).
Pas d'auth. Rate-limit : 5 req/s.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

INPI_BREVETS_ENDPOINT = "https://data.inpi.fr/api/brevets/search"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 200


async def fetch_inpi_brevets_delta() -> dict:
    """Récupère les dépôts de brevets INPI récents, dedup sur numero_publication.
    1er run : 90 jours ; runs suivants : 200h (couvre délai traitement INPI).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    import psycopg as _pg
    async with await _pg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.inpi_brevets_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

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
                        "q": f"dateDepot:[{since} TO *]",
                        "rows": PAGE_SIZE,
                        "start": offset,
                        "sort": "dateDepot desc",
                    }
                    r = await client.get(INPI_BREVETS_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("INPI BREVETS HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("response", {}).get("docs", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        numero_publication_raw = rec.get("numeroPublication") or ""
                        numero_publication = _s(numero_publication_raw)
                        if not numero_publication:
                            total_skipped += 1
                            continue

                        # Parse fields safely
                        titre = _s(rec.get("titre"))[:1024]
                        siren_deposant_raw = rec.get("sirenDeposant") or ""
                        siren_deposant = _s(siren_deposant_raw)[:9] if len(_s(siren_deposant_raw)) >= 9 else ""
                        nom_deposant = _s(rec.get("nomDeposant"))[:512]
                        date_depot = _parse_date(rec.get("dateDepot"))
                        ipc_classes_raw = rec.get("ipcClasses") or []
                        ipc_classes = [_s(x) for x in ipc_classes_raw] if isinstance(ipc_classes_raw, list) else []

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.inpi_brevets_raw
                                  (numero_publication, titre, siren_deposant, nom_deposant, date_depot, ipc_classes, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (numero_publication) DO NOTHING
                                """,
                                (
                                    numero_publication,
                                    titre,
                                    siren_deposant,
                                    nom_deposant,
                                    date_depot,
                                    ipc_classes,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip brevet %s: %s", numero_publication, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "inpi_brevets",
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
        # Format INPI : YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SSZ
        s_clean = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s_clean)
        return dt.date()
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None