"""RPPS — Répertoire Partagé Professionnels Santé.

Source #130 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://annuaire.sante.fr/api/v1/professionnels
Licence Etalab 2.0. RGPD : on stocke nom/prenom/rpps/siret/specialite, pas d'adresse/tel/email.
Pas de date_naissance brute → stockage annuel uniquement via transformation gold.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

RPPS_ENDPOINT = "https://annuaire.sante.fr/api/v1/professionnels"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~10k professionnels par run — couvre 700k en <70 runs
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 720  # 30 jours (spec: refresh_trigger=720h)


async def fetch_rpps_delta() -> dict:
    """Récupère les professionnels de santé RPPS récents, upsert sur rpps.
    1er run : 365 jours ; runs suivants : 720h (couvre refresh hebdo + marge).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.rpps_professionnels_raw LIMIT 1")
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
                        "order_by": "date_modification DESC",
                    }
                    # Note: l'API RPPS ne supporte pas de filtre date natif → on filtre en post-traitement
                    r = await client.get(RPPS_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("RPPS HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("data", [])
                    if not records:
                        break

                    # Filtrage sur date_modification (format ISO 8601)
                    filtered_records = []
                    for rec in records:
                        modif_date = rec.get("date_modification")
                        if not modif_date:
                            continue
                        try:
                            modif_dt = datetime.fromisoformat(modif_date.replace("Z", "+00:00"))
                            if modif_dt >= (datetime.now(tz=timezone.utc) - window):
                                filtered_records.append(rec)
                        except Exception:
                            continue

                    total_fetched += len(filtered_records)

                    # Upsert bronze
                    for rec in filtered_records:
                        rpps_raw = rec.get("rpps")
                        rpps = _s(rpps_raw)
                        if not rpps:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.rpps_professionnels_raw
                                  (rpps, nom, prenom, profession, specialite, siret_etab, commune, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (rpps) DO UPDATE SET
                                  nom = EXCLUDED.nom,
                                  prenom = EXCLUDED.prenom,
                                  profession = EXCLUDED.profession,
                                  specialite = EXCLUDED.specialite,
                                  siret_etab = EXCLUDED.siret_etab,
                                  commune = EXCLUDED.commune,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    rpps[:16],
                                    _s(rec.get("nom"))[:255],
                                    _s(rec.get("prenom"))[:255],
                                    _s(rec.get("profession"))[:128],
                                    _s(rec.get("specialite"))[:128],
                                    _s(rec.get("siret_etab"))[:14],
                                    _s(rec.get("commune"))[:255],
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip rpps %s: %s", rpps, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "rpps",
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