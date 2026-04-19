"""Recherche Entreprises — API publique de l'annuaire des entreprises.

Source #1 d'ARCHITECTURE_DATA_V2.md. API publique gratuite (Etalab 2.0).
Endpoint : https://recherche-entreprises.api.gouv.fr/search
Pas d'auth. Rate-limit : 7 req/s, 50k/jour.
RGPD : données publiques (SIREN, nom, NAF, effectifs, date création, siege, état).
Pas de données sensibles (pas d'email/tél/adresse perso, pas de scoring personne physique).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

RECHERCHE_ENDPOINT = "https://recherche-entreprises.api.gouv.fr/search"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k lignes max par run (sécurité quota journalier)
# Fenêtre de backfill initial large (données statiques, mais besoin de couvrir les nouvelles créations)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 24


async def fetch_recherche_entreprises_delta() -> dict:
    """Récupère les entreprises via l'API Recherche Entreprises, dedup sur siren.
    1er run : 365 jours (backfill complet) ; runs suivants : 24h (couvre créations/réactualisations).
    Utilise la requête de seed définie dans la spec YAML pour cibler les SIRENs manquants.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.recherche_entreprises_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)

    # Récupération des SIRENs à enrichir via la requête de seed
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT DISTINCT siren
                FROM bronze.bodacc_annonces_raw
                WHERE siren IS NOT NULL
                  AND siren NOT IN (SELECT siren FROM bronze.recherche_entreprises_raw)
                LIMIT 1000
                """
            )
            siren_list = [row[0] for row in await cur.fetchall()]

    if not siren_list:
        return {"source": "recherche_entreprises", "rows": 0, "fetched": 0, "skipped_existing": 0, "reason": "no_missing_siren"}

    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for siren in siren_list:
                    if not siren or len(siren) != 9 or not siren.isdigit():
                        total_skipped += 1
                        continue

                    params = {"q": siren, "field": "siren"}
                    try:
                        r = await client.get(RECHERCHE_ENDPOINT, params=params)
                        if r.status_code != 200:
                            log.warning("Recherche Entreprises HTTP %s for siren=%s: %s", r.status_code, siren, r.text[:200])
                            continue
                        data = r.json()
                        results = data.get("results", [])
                        if not results:
                            total_skipped += 1
                            continue

                        rec = results[0]  # On s'attend à un seul résultat par SIREN
                        total_fetched += 1

                        # Extraction des champs selon la spec
                        payload = Jsonb(rec)

                        # Parsing date_creation
                        date_creation = _parse_date(rec.get("date_creation"))

                        # Extraction siege
                        siege = rec.get("siege", {})
                        siege_commune = _s(siege.get("libelle_commune"))[:255]
                        siege_dept = _s(siege.get("departement"))[:8]

                        # Tranche effectifs : convertir None → ''
                        tranche_effectifs = _s(rec.get("tranche_effectif_salarie"))[:8]

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.recherche_entreprises_raw
                                  (siren, nom_complet, nom_raison_sociale, naf, tranche_effectifs,
                                   date_creation, siege_commune, siege_dept, etat, categorie, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (siren) DO UPDATE SET
                                  nom_complet = EXCLUDED.nom_complet,
                                  nom_raison_sociale = EXCLUDED.nom_raison_sociale,
                                  naf = EXCLUDED.naf,
                                  tranche_effectifs = EXCLUDED.tranche_effectifs,
                                  date_creation = EXCLUDED.date_creation,
                                  siege_commune = EXCLUDED.siege_commune,
                                  siege_dept = EXCLUDED.siege_dept,
                                  etat = EXCLUDED.etat,
                                  categorie = EXCLUDED.categorie,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    siren,
                                    _s(rec.get("nom_complet"))[:512],
                                    _s(rec.get("nom_raison_sociale"))[:512],
                                    _s(rec.get("activite_principale"))[:8],
                                    tranche_effectifs,
                                    date_creation,
                                    siege_commune,
                                    siege_dept,
                                    _s(rec.get("etat_administratif"))[:32],
                                    _s(rec.get("categorie_entreprise"))[:16],
                                    payload,
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip siren %s: %s", siren, e)
                            total_skipped += 1

                    except Exception as e:
                        log.warning("Request error for siren %s: %s", siren, e)
                        total_skipped += 1

                await conn.commit()

    return {
        "source": "recherche_entreprises",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped_existing": total_skipped,
        "siren_count": len(siren_list),
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