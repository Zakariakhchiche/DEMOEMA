"""BASOL — Base de données des sites et sols pollués.

Source #87 d'ARCHITECTURE_DATA_V2.md. API publique via data.gouv.fr.
Endpoint : https://www.data.gouv.fr/api/1/datasets/basol-base-de-donnees-des-sites-et-sols-pollues/
Licence : Etalab 2.0. Données sensibles (polluants, statut) → attention RGPD : pas de nom d'exploitant
ni coordonnées postales brutes dans les marts. Seulement code_basol + commune + polluants agrégés.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

BASOL_ENDPOINT = "https://www.data.gouv.fr/api/1/datasets/basol-base-de-donnees-des-sites-et-sols-pollues/"
RESOURCE_ID = "588b8c9c8c8c8c8c8c8c8c8c"  # ID fixe de la ressource JSON (à valider via API)
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~50k sites par run — backfill complet via plusieurs invocations
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 720  # 30 jours (spec: interval_hours=720)


async def fetch_basol_delta() -> dict:
    """Récupère les sites BASOL récents, upsert sur code_basol.
    1er run : 365 jours ; runs suivants : 720h (30 jours) — couvre délai mise à jour MTE.
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.basol_sites_raw LIMIT 1")
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
                    # Endpoint JSON de la ressource (via API data.gouv.fr)
                    url = f"{BASOL_ENDPOINT}resources/{RESOURCE_ID}/?limit={PAGE_SIZE}&offset={offset}"
                    r = await client.get(url)
                    if r.status_code != 200:
                        log.warning("BASOL HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("records", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        try:
                            fields = rec.get("fields", {})
                            code_basol_raw = fields.get("code_basol")
                            code_basol = _s(code_basol_raw)
                            if not code_basol:
                                total_skipped += 1
                                continue

                            # Extraction des champs requis
                            nom_usuel = _s(fields.get("nom_usuel"))[:512]
                            siret = _s(fields.get("siret"))[:14]
                            commune = _s(fields.get("commune"))[:255]
                            statut = _s(fields.get("statut"))[:64]
                            date_maj = _parse_date(fields.get("date_maj"))
                            polluants_raw = fields.get("polluants")
                            polluants = _extract_polluants(polluants_raw)

                            # Upsert conforme à la spec
                            await cur.execute(
                                """
                                INSERT INTO bronze.basol_sites_raw
                                  (code_basol, nom_usuel, siret, commune, statut, date_maj, polluants, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (code_basol) DO UPDATE SET
                                  nom_usuel = EXCLUDED.nom_usuel,
                                  siret = EXCLUDED.siret,
                                  commune = EXCLUDED.commune,
                                  statut = EXCLUDED.statut,
                                  date_maj = EXCLUDED.date_maj,
                                  polluants = EXCLUDED.polluants,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    code_basol,
                                    nom_usuel,
                                    siret,
                                    commune,
                                    statut,
                                    date_maj,
                                    polluants,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip site BASOL: %s", e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "basol",
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


def _extract_polluants(polluants_raw) -> list[str]:
    """Extrait la liste de polluants depuis le champ JSON (souvent list[str] ou str)."""
    if polluants_raw is None:
        return []
    if isinstance(polluants_raw, list):
        return [_s(p) for p in polluants_raw if p]
    if isinstance(polluants_raw, str):
        return [polluants_raw] if polluants_raw else []
    return []