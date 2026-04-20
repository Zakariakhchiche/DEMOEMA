"""ANSSI CERT-FR — alertes cyber.

Source #39 d'ARCHITECTURE_DATA_V2.md. API publique REST JSON.
Endpoint : https://www.cert.ssi.gouv.fr/api/alerte
Licence : Etalab 2.0 (données publiques). Aucune auth.
RGPD : données anonymes (pas d'info personnelle), pas de scraping de contenu.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

CERT_FR_ENDPOINT = "https://www.cert.ssi.gouv.fr/api/alerte"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~1k alertes max par run (source peu volumineuse)
BACKFILL_DAYS_FIRST_RUN = 3650  # 1 an historique pour couvrir les alertes passées
INCREMENTAL_HOURS = 24  # delta quotidien (refresh_trigger=24h)


async def fetch_anssi_cert_fr_delta() -> dict:
    """Récupère les alertes CERT-FR récentes, upsert sur ref (id unique).
    1er run : 365 jours ; runs suivants : 24h (conforme à refresh_trigger).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.anssi_alertes_raw LIMIT 1")
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
                    # Pagination via offset (API ne fournit pas de cursor)
                    offset = page * PAGE_SIZE
                    params = {
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "order": "date_emission DESC",
                    }
                    try:
                        r = await client.get(CERT_FR_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("CERT-FR timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("CERT-FR HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        ref_raw = rec.get("ref") or ""
                        ref = _s(ref_raw)[:64]
                        if not ref:
                            total_skipped += 1
                            continue

                        date_emission = _parse_date(rec.get("date_emission"))
                        niveau = _s(rec.get("niveau"))[:32]
                        titre = _s(rec.get("titre"))[:512]
                        produits_affectes = _extract_produits(rec.get("produits_affectes", []))

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.anssi_alertes_raw
                                  (ref, date_emission, niveau, titre, produits_affectes, payload)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (ref) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    ref,
                                    date_emission,
                                    niveau,
                                    titre,
                                    produits_affectes,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip alerte ref=%s: %s", ref, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "anssi_cert_fr",
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


def _extract_produits(value) -> list[str]:
    """Normalise produits_affectés en list[str] (pour TEXT[] Postgres)."""
    if isinstance(value, list):
        return [_s(v) for v in value if v]
    if isinstance(value, str):
        return [_s(value)] if value else []
    return []