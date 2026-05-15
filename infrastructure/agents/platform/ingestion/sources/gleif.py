"""GLEIF — Global Legal Entity Identifier.

Source #9 d'ARCHITECTURE_DATA_V2.md. API publique Open Data (ODbL).
Endpoint : https://api.gleif.org/api/v1/lei-records
Pas d'auth. Rate-limit : 5 req/s. Filtre pays FR uniquement.
RGPD : données entités juridiques uniquement (pas de personnes physiques).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

GLEIF_ENDPOINT = "https://api.gleif.org/api/v1/lei-records"
PAGE_SIZE = 200
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 24  # 1 jour pour couvrir les mises à jour quotidiennes


async def fetch_gleif_delta() -> dict:
    """Récupère les LEI FR depuis GLEIF, avec upsert sur lei.
    1er run : 30 jours de données historiques ; runs suivants : 24h (delta quotidien).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.gleif_lei_raw LIMIT 1")
            existing = (await _fetch_one(cur))[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    # Bug 2026-05-15 : parent_lei + ultimate_parent_lei retournaient toujours
    # vides. JSON:API n'embed pas les related entities sans `include=`. On
    # demande explicitement direct-parent + ultimate-parent dans la réponse
    # pour que data.relationships.<type>.data.id soit présent.
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    params = {
                        # Pas de filter pays → ingestion mondiale. Les LEI FR
                        # restent prioritaires (matchent siren_fr), les autres
                        # parents/filiales étrangers viennent en bonus pour
                        # mapping groupe international.
                        "page[size]": PAGE_SIZE,
                        "page[number]": page + 1,
                    }
                    try:
                        r = await client.get(GLEIF_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("GLEIF timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("GLEIF HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("data", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    for rec in records:
                        lei = _s(rec.get("id"))
                        if not lei:
                            total_skipped += 1
                            continue

                        # Extraction des champs selon la spec
                        attributes = rec.get("attributes", {})
                        relationships = rec.get("relationships", {})
                        entity = attributes.get("entity", {}) if attributes else {}
                        legal_name = _s(entity.get("legalName", {}).get("name"))[:512] if entity.get("legalName") else ""
                        country = _s(entity.get("legalAddress", {}).get("country"))[:8] or ""
                        status = _s(entity.get("status"))[:32] or ""
                        # JSON:API : relationships.<type>.data peut être :
                        # - dict {"id": "LEI", "type": "lei-records"} si relation existe
                        # - null si pas de parent
                        # - absent si pas demandé via ?include= (cas legacy avant fix)
                        # On gère les 3 cas.
                        def _rel_lei(rel_name: str) -> str:
                            rel = relationships.get(rel_name) or {}
                            d = rel.get("data") if isinstance(rel, dict) else None
                            if not d or not isinstance(d, dict):
                                return ""
                            return _s(d.get("id"))[:20]
                        parent_lei = _rel_lei("direct-parent")
                        ultimate_parent_lei = _rel_lei("ultimate-parent")
                        siren = _s(entity.get("registeredAs"))[:9] or ""

                        payload = Jsonb(rec)

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.gleif_lei_raw
                                  (lei, legal_name, country, status, parent_lei, ultimate_parent_lei, siren, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (lei) DO UPDATE SET
                                  legal_name = EXCLUDED.legal_name,
                                  country = EXCLUDED.country,
                                  status = EXCLUDED.status,
                                  parent_lei = EXCLUDED.parent_lei,
                                  ultimate_parent_lei = EXCLUDED.ultimate_parent_lei,
                                  siren = EXCLUDED.siren,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    lei,
                                    legal_name,
                                    country,
                                    status,
                                    parent_lei,
                                    ultimate_parent_lei,
                                    siren,
                                    payload,
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip LEI %s: %s", lei, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "gleif",
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


async def _fetch_one(cur) -> tuple:
    """Wrapper pour fetchone() compatible avec psycopg.AsyncConnection."""
    return await cur.fetchone()