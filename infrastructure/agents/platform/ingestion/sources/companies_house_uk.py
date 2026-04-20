"""Companies House UK — registre officiel.

Source #26 d'ARCHITECTURE_DATA_V2.md. API publique gratuite avec clé API.
Endpoint : https://api.company-information.service.gov.uk/search/companies
Authentification : Basic Auth avec `api_key:` prefix (ex: `COMPANIES_HOUSE_UK_KEY: ""`)
Licence : Open Government Licence v3.0
RGPD : Aucune donnée personnelle sensible — seuls les SIREN/LEI sont exploitables via filiation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

COMPANIES_HOUSE_UK_ENDPOINT = "https://api.company-information.service.gov.uk/search/companies"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~1k entreprises par run — delta quotidien suffisant
BACKFILL_DAYS_FIRST_RUN = 3650  # Full backfill 1 an pour couvrir filiales FR
INCREMENTAL_HOURS = 24  # Delta quotidien


async def fetch_companies_house_uk_delta() -> dict:
    """Récupère les entreprises UK récentes via Companies House API, dedup sur company_number.
    1er run : 365 jours ; runs suivants : 24h (couvre délai publication quotidien).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.companies_house_uk_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")

    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    # Auth Basic avec clé API (format : "API_KEY:")
    api_key = settings.COMPANIES_HOUSE_UK_KEY
    if not api_key:
        return {"error": "COMPANIES_HOUSE_UK_KEY non configuré", "rows": 0}

    auth = httpx.Auth("api_key", api_key)

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}, auth=auth) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    params = {
                        "q": "",
                        "items_per_page": PAGE_SIZE,
                        "start_index": offset,
                        "company_status": "active",
                        "date_created_from": since,
                    }
                    r = await client.get(COMPANIES_HOUSE_UK_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("Companies House UK HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    items = data.get("items", [])
                    if not items:
                        break
                    total_fetched += len(items)

                    # Upsert bronze
                    for item in items:
                        company_number_raw = item.get("company_number")
                        company_number = _s(company_number_raw)
                        if not company_number:
                            total_skipped += 1
                            continue

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.companies_house_uk_raw
                                  (company_number, company_name, company_status, date_of_creation,
                                   address, sic_codes, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (company_number) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    company_number[:16],
                                    _s(item.get("title"))[:512],
                                    _s(item.get("company_status"))[:64],
                                    _parse_date(item.get("date_of_creation")),
                                    Jsonb(item.get("address", {})),
                                    _extract_sic_codes(item),
                                    Jsonb(item),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip company %s: %s", company_number, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(items) < PAGE_SIZE:
                        break

    return {
        "source": "companies_house_uk",
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


def _extract_sic_codes(item: dict) -> list[str]:
    """Extrait les codes SIC sous forme de liste de strings."""
    sic_codes = item.get("sic_codes", [])
    if not isinstance(sic_codes, list):
        return []
    return [str(code) for code in sic_codes if code is not None]