"""Annuaire des Entreprises — API publique officielle (data.gouv.fr).

Source #5 d'ARCHITECTURE_DATA_V2.md. API REST publique gratuite.
Endpoint : https://recherche-entreprises.api.gouv.fr/search
Pas d'auth. License Etalab 2.0. RGPD : données publiques, pas d'info sensible (pas de SIRET seul, pas de contact).
Fusion INSEE + INPI + RNE. Format très proche de recherche_entreprises mais portail officiel.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

ANNUAIRE_ENDPOINT = "https://recherche-entreprises.api.gouv.fr/search"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~5000 entreprises par run (sécurité quota)
# Fenêtre de backfill initial large (données mises à jour hebdo, délai typique ~15j)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 72


async def fetch_annuaire_entreprises_delta() -> dict:
    """Récupère les entreprises récentes de l'annuaire, upsert sur siren.
    1er run : 30 jours ; runs suivants : 72h (couvre délai mise à jour hebdo + week-end)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    import psycopg as _pg
    async with await _pg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.annuaire_entreprises_raw LIMIT 1")
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
                        "q": "",
                        "fields": "siren,nom_complet,activite_principale,siege,etat_administratif",
                        "per_page": PAGE_SIZE,
                        "page": page + 1,
                        "date_mise_a_jour": since,
                    }
                    r = await client.get(ANNUAIRE_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("Annuaire-Entreprises HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        siren_raw = rec.get("siren")
                        siren = _s(siren_raw)[:9] if siren_raw else ""
                        if not siren or len(siren) != 9 or not siren.isdigit():
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.annuaire_entreprises_raw
                                  (siren, nom_complet, naf, siege_commune, etat, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (siren) DO UPDATE SET
                                  nom_complet = EXCLUDED.nom_complet,
                                  naf = EXCLUDED.naf,
                                  siege_commune = EXCLUDED.siege_commune,
                                  etat = EXCLUDED.etat,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    siren,
                                    _s(rec.get("nom_complet"))[:512],
                                    _s(rec.get("activite_principale"))[:8],
                                    _s((rec.get("siege") or {}).get("libelle_commune"))[:255],
                                    _s(rec.get("etat_administratif"))[:32],
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip siren %s: %s", siren, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "annuaire_entreprises",
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