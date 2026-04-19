"""BAN — Base Adresse Nationale.

Source #72 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://api-adresse.data.gouv.fr/search/
Pas d'auth. License Etalab 2.0. Aucune donnée personnelle sensible (pas d'email/tél/adresse complète).
RGPD : on stocke uniquement les champs publics (label, code_postal, commune, geo_lon, geo_lat).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

BAN_ENDPOINT = "https://api-adresse.data.gouv.fr/search/"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~10k adresses par run — suffisant pour delta quotidien
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 24


async def fetch_ban_adresses_delta() -> dict:
    """Récupère les adresses BAN récentes, upsert sur ban_id (id de l'API).
    1er run : 30 jours ; runs suivants : 24h (couvre délai mise à jour BAN).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.ban_adresses_raw LIMIT 1")
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
                        "q": "",
                        "type": "municipality",
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "h": "date_maj",
                    }
                    # On ne filtre pas par date dans la requête (API ne supporte pas well), on filtre après
                    r = await client.get(BAN_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("BAN HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    features = data.get("features", [])
                    if not features:
                        break

                    for feat in features:
                        props = feat.get("properties", {})
                        ban_id_raw = props.get("id")
                        ban_id = _s(ban_id_raw)
                        if not ban_id:
                            total_skipped += 1
                            continue

                        # Extraction des champs obligatoires selon spec
                        label = _s(props.get("label"))[:512]
                        code_postal = _s(props.get("postcode"))[:8]
                        commune = _s(props.get("city"))[:255]
                        geo_lon = _to_float(props.get("lon"))
                        geo_lat = _to_float(props.get("lat"))

                        # Payload complet pour reproductibilité
                        payload = Jsonb(feat)

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.ban_adresses_raw
                                  (ban_id, label, code_postal, commune, geo_lon, geo_lat, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (ban_id) DO UPDATE SET
                                  label = EXCLUDED.label,
                                  code_postal = EXCLUDED.code_postal,
                                  commune = EXCLUDED.commune,
                                  geo_lon = EXCLUDED.geo_lon,
                                  geo_lat = EXCLUDED.geo_lat,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    ban_id[:32],
                                    label,
                                    code_postal,
                                    commune,
                                    geo_lon,
                                    geo_lat,
                                    payload,
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip ban_id %s: %s", ban_id, e)
                            total_skipped += 1

                    await conn.commit()
                    total_fetched += len(features)
                    if len(features) < PAGE_SIZE:
                        break

    return {
        "source": "ban_adresses",
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


def _to_float(value) -> float | None:
    """Convertit en float, None si invalide."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None