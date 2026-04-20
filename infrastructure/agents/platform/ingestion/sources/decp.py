"""DECP — Données Essentielles des Contrats Publics FR.

Source #47 d'ARCHITECTURE_DATA_V2.md. API publique gratuite via OpenDataSoft.
Endpoint : https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-v3-marches-valides/records
Licence Etalab 2.0. Pas d'auth. Rate-limit ~5 req/s.
RGPD : données publiques, pas de données sensibles. On stocke uniquement SIRET (pas SIREN seul).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

DECP_ENDPOINT = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-v3-marches-valides/records"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~5000 marchés par run (sécurité quota)
# Fenêtre de backfill initial large (DECP publie avec 1-3j de délai typique)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 180


async def fetch_decp_delta() -> dict:
    """Récupère les marchés publics DECP récents, dedup sur marche_id.
    1er run : 90 jours ; runs suivants : 180h (couvre délai publication + week-end)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.decp_marches_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    where = f"datenotification >= date'{since}'"
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
                        "order_by": "datenotification DESC",
                    }
                    r = await client.get(DECP_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("DECP HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        marche_id_raw = rec.get("id") or ""
                        marche_id = _s(marche_id_raw)
                        if not marche_id:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.decp_marches_raw
                                  (marche_id, acheteur_siret, acheteur_nom, titulaire_siret, titulaire_nom,
                                   montant_ht, date_notification, cpv, objet, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (marche_id) DO NOTHING
                                """,
                                (
                                    marche_id[:128],
                                    _extract_siret(rec.get("acheteur", {})),
                                    _s(rec.get("acheteur", {}).get("nom"))[:512],
                                    _extract_siret(rec.get("titulaires", [{}])[0] if rec.get("titulaires") else {}),
                                    _s(_get_titulaire_denomination(rec))[:512],
                                    _parse_numeric(rec.get("montant")),
                                    _parse_date(rec.get("datenotification")),
                                    _s(rec.get("codecpv"))[:16],
                                    _s(rec.get("objet"))[:10000],
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip marché %s: %s", marche_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "decp",
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
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_siret(obj: dict) -> str | None:
    """Extrait le SIRET depuis un objet (acheteur/titulaire)."""
    if not isinstance(obj, dict):
        return None
    siret = obj.get("id")
    if siret and isinstance(siret, str) and len(siret) == 14 and siret.isdigit():
        return siret
    return None


def _get_titulaire_denomination(rec: dict) -> str | None:
    """Extrait la denomination sociale du premier titulaire."""
    titulaires = rec.get("titulaires", [])
    if not isinstance(titulaires, list) or not titulaires:
        return None
    titulaire = titulaires[0]
    if isinstance(titulaire, dict):
        denom = titulaire.get("denominationsociale")
        if denom:
            return denom
        # Fallback : concaténation nom + prénom si personne physique
        nom = titulaire.get("nom")
        prenom = titulaire.get("prenom")
        if nom:
            return f"{prenom or ''} {nom}".strip() if prenom else nom
    return None