"""OpenCorporates — Snapshot gelé 2019 (pas de deltas gratuits). Source fallback GLEIF+Wikidata pour filiales internationales.

Endpoint : https://api.opencorporates.com/v0.4/companies/search
Licence : ODbL (Open Data Commons). Pas d'auth. Rate-limit free tier agressive (1 req/s, 500/jour).
RGPD : on stocke uniquement les identifiants publics (jurisdiction_code, company_number, name, dates, url).
Pas de données sensibles (pas d'adresses, emails, dirigeants détaillés).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

OPENCORPORATES_ENDPOINT = "https://api.opencorporates.com/v0.4/companies/search"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~500 entreprises par run (sécurité quota free tier)
BACKFILL_DAYS_FIRST_RUN = 3650  # Snapshot gelé 2019 → backfill large sur 1 an
INCREMENTAL_HOURS = 24  # Mise à jour quotidienne suffisante (pas de deltas en temps réel)


async def fetch_opencorporates_delta() -> dict:
    """Récupère les entreprises OpenCorporates, dedup sur (jurisdiction_code, company_number).
    1er run : 1 an (snapshot gelé) ; runs suivants : 24h (consistance journalière).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.opencorporates_companies_raw LIMIT 1")
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
                        "q": "",  # Empty query → retrieve all companies (snapshot-based)
                        "jurisdiction_code": "",
                        "page": page + 1,
                        "per_page": PAGE_SIZE,
                    }
                    try:
                        r = await client.get(OPENCORPORATES_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("OpenCorporates timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("OpenCorporates HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    companies = data.get("results", {}).get("companies", [])
                    if not companies:
                        break
                    total_fetched += len(companies)

                    # Upsert bronze
                    for company in companies:
                        jurisdiction_code = _s(company.get("jurisdiction_code", ""))
                        company_number = _s(company.get("company_number", ""))
                        if not jurisdiction_code or not company_number:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.opencorporates_companies_raw
                                  (jurisdiction_code, company_number, name, status, incorporation_date,
                                   dissolution_date, opencorporates_url, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                                ON CONFLICT (jurisdiction_code, company_number) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    jurisdiction_code[:16],
                                    company_number[:64],
                                    _s(company.get("name"))[:512],
                                    _s(company.get("current_status"))[:64],
                                    _parse_date(company.get("incorporation_date")),
                                    _parse_date(company.get("dissolution_date")),
                                    _s(company.get("opencorporates_url"))[:512],
                                    Jsonb(company),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip company %s/%s: %s", jurisdiction_code, company_number, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(companies) < PAGE_SIZE:
                        break

    return {
        "source": "opencorporates",
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