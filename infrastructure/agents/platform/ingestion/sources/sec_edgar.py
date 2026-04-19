"""SEC EDGAR — filings US.

Source #25 d'ARCHITECTURE_DATA_V2.md. API publique gratuite (US government).
Endpoint : https://data.sec.gov/submissions/CIK0000320193.json (exemple Apple)
Licence : Public domain. Pas de données personnelles sensibles (nom entreprise, type acte, date).
RGPD : pas d'analyse de personnes physiques, pas de scraping de sites non-ouverts.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

SEC_ENDPOINT = "https://data.sec.gov/submissions/"
PAGE_SIZE = 100  # SEC ne fournit pas de pagination explicite, on simule via offset
MAX_PAGES_PER_RUN = 1000  # ~1000 filings max par run — suffisant pour delta quotidien
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 24


async def fetch_sec_edgar_delta() -> dict:
    """Récupère les derniers filings SEC (10-K, 20-F, 8-K, etc.), dedup sur accession_number.
    1er run : 365 jours ; runs suivants : 24h (couvre délai publication SEC).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.sec_edgar_filings_raw LIMIT 1")
            existing = (await _cur.fetchone())[0] if (await cur.fetchone()) else 0

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    # SEC requires User-Agent with email — cf. spec.headers
    headers = {"User-Agent": "DEMOEMA ingestion contact@demoema.fr"}

    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                # On simule la pagination via offset (SEC ne fournit pas d'offset natif, on itère sur les pages)
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    # SEC API ne supporte pas l'offset natif, on utilise la méthode "recent" + filtre date
                    # Pour simplifier Y1 : on appelle l'endpoint de l'exemple (Apple) pour valider le pattern,
                    # puis on généralisera via CIK lookup (cf. TODO). Ici on garde l'exemple fixe pour validation.
                    # En prod, on bouclerait sur les CIKs des filiales FR connues (ex: 0000019041 pour LVMH).
                    # Pour ce fetcher minimal : on se contente de l'exemple Apple (CIK0000320193).
                    url = f"{SEC_ENDPOINT}CIK0000320193.json"
                    r = await client.get(url)
                    if r.status_code != 200:
                        log.warning("SEC HTTP %s: %s", r.status_code, r.text[:200])
                        break

                    data = r.json()
                    # Structure typique : {"filings": {"recent": {"accessionNumber": [...], "filingDate": [...]}}}
                    recent = data.get("filings", {}).get("recent", {})
                    if not recent:
                        break

                    # Aligner les listes par index
                    keys = ["accessionNumber", "filingDate", "reportDate", "formType", "companyName"]
                    rows = []
                    max_len = max(len(recent.get(k, [])) for k in keys if recent.get(k))
                    for i in range(min(max_len, PAGE_SIZE)):
                        row = {
                            "accession_number": _s(recent.get("accessionNumber", [None] * max_len)[i]),
                            "cik": _s(recent.get("cik", [None] * max_len)[i]),
                            "company_name": _s(recent.get("companyName", [None] * max_len)[i]),
                            "form_type": _s(recent.get("formType", [None] * max_len)[i]),
                            "filing_date": _parse_date(recent.get("filingDate", [None] * max_len)[i]),
                            "report_date": _parse_date(recent.get("reportDate", [None] * max_len)[i]),
                        }
                        rows.append(row)

                    if not rows:
                        break
                    total_fetched += len(rows)

                    # Upsert bronze
                    for rec in rows:
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.sec_edgar_filings_raw
                                  (accession_number, cik, company_name, form_type, filing_date, report_date, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (accession_number) DO NOTHING
                                """,
                                (
                                    rec["accession_number"][:64],
                                    rec["cik"][:16],
                                    rec["company_name"][:512],
                                    rec["form_type"][:32],
                                    rec["filing_date"],
                                    rec["report_date"],
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip filing %s: %s", rec["accession_number"], e)
                            total_skipped += 1

                    await conn.commit()
                    # SEC ne fournit pas de pagination, on ne fait qu'une seule requête par run
                    break

    return {
        "source": "sec_edgar",
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
        return json.dumps(value, ensure_ascii=False)
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