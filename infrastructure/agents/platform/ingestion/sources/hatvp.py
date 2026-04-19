"""HATVP — Haute Autorité pour la Transparence de la Vie Publique.

Source #95 d'ARCHITECTURE_DATA_V2.md. API publique gratuite sous licence Etalab 2.0.
Endpoint : https://www.hatvp.fr/open-data/ri/representants-interets.json
Pas d'auth. Données publiprotégées : pas d'information personnelle sensible (seulement SIREN, dénomination, secteur).
RGPD : on stocke uniquement les données déclaratives (pas d'emails/tél/adresses personnelles).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

HATVP_ENDPOINT = "https://www.hatvp.fr/open-data/ri/representants-interets.json"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~5000 représentants max par run (sécurité quota)
BACKFILL_DAYS_FIRST_RUN = 3650  # Premier run : couvrir l'année complète (données historiques)
INCREMENTAL_HOURS = 720  # 30 jours (refresh_trigger=720h → on couvre avec marge)


async def fetch_hatvp_delta() -> dict:
    """Récupère les représentants d'intérêt HATVP, upsert sur representant_id.
    1er run : 365 jours (historique) ; runs suivants : 720h (refresh_trigger).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.hatvp_representants_raw LIMIT 1")
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
                    }
                    r = await client.get(HATVP_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("HATVP HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        representant_id_raw = rec.get("id")
                        representant_id = _s(representant_id_raw)
                        if not representant_id:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.hatvp_representants_raw
                                  (representant_id, denomination, siren, secteur_activite,
                                   date_inscription, adresse_ville, nb_deputes,
                                   chiffre_affaires_lobbying, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (representant_id) DO UPDATE SET
                                  denomination = EXCLUDED.denomination,
                                  siren = EXCLUDED.siren,
                                  secteur_activite = EXCLUDED.secteur_activite,
                                  date_inscription = EXCLUDED.date_inscription,
                                  adresse_ville = EXCLUDED.adresse_ville,
                                  nb_deputes = EXCLUDED.nb_deputes,
                                  chiffre_affaires_lobbying = EXCLUDED.chiffre_affaires_lobbying,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    representant_id[:64],
                                    _s(rec.get("denomination"))[:512],
                                    _s(rec.get("siren"))[:9],
                                    _s(rec.get("secteurActivite"))[:255],
                                    _parse_date(rec.get("dateInscription")),
                                    _s(rec.get("adresseVille"))[:255],
                                    _int(rec.get("nbDeputes")),
                                    _numeric(rec.get("caLobbying")),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip représentant %s: %s", representant_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "hatvp",
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


def _int(value) -> int | None:
    """Convertit en int, None si impossible."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _numeric(value) -> float | None:
    """Convertit en NUMERIC (float), None si impossible."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None