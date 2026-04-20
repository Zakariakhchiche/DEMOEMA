"""OpenAlex — Publications scientifiques mondiales (250M articles).

Source #60 d'ARCHITECTURE_DATA_V2.md. API publique REST JSON gratuite (CC0).
Endpoint : https://api.openalex.org/works
Pas d'auth. Rate-limit : 10 req/s. Filtrage par défaut : institutions françaises.
RGPD : pas de données personnelles sensibles (seulement noms d'auteurs anonymisés,
institutions publiques). Aucune donnée de contact personnel (email/tél/adresse) stockée.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

OPENALEX_ENDPOINT = "https://api.openalex.org/works"
PAGE_SIZE = 50
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 720  # 30 jours → 720h (cf. spec refresh_trigger=720h)


async def fetch_openalex_delta() -> dict:
    """Récupère les articles OpenAlex récents, dedup sur openalex_id.
    1er run : 365 jours ; runs suivants : 720h (couvre refresh_trigger=720h).
    Filtre par défaut : authorships.institutions.country_code:FR
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.openalex_works_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    # Query filter selon spec
    query_filter = "authorships.institutions.country_code:FR"
    params_base = {
        "filter": f"publication_date:>={since},{query_filter}",
        "per-page": PAGE_SIZE,
        "sort": "publication_date:desc",
    }

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    params = params_base.copy()
                    params["page"] = f"page={page + 1}"
                    r = await client.get(OPENALEX_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("OpenAlex HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    results = data.get("results", [])
                    if not results:
                        break
                    total_fetched += len(results)

                    for rec in results:
                        openalex_id_raw = rec.get("id") or ""
                        openalex_id = _s(openalex_id_raw).split("/")[-1] if openalex_id_raw else ""
                        if not openalex_id:
                            total_skipped += 1
                            continue

                        # Extraction des champs selon spec
                        title = _s(rec.get("title"))[:1024]
                        publication_year_raw = rec.get("publication_year")
                        publication_year = int(publication_year_raw) if isinstance(publication_year_raw, (int, float)) else None
                        publication_date_raw = rec.get("publication_date")
                        publication_date = _parse_date(publication_date_raw)
                        cited_by_count_raw = rec.get("cited_by_count")
                        cited_by_count = int(cited_by_count_raw) if isinstance(cited_by_count_raw, (int, float)) else None

                        # Auteurs + institutions : on garde JSONB complet + liste institutions (TEXT[])
                        authorships = rec.get("authorships") or []
                        institutions_list = []
                        for a in authorships:
                            insts = a.get("institutions") or []
                            for inst in insts:
                                inst_id = _s(inst.get("id") or "").split("/")[-1] if inst.get("id") else ""
                                if inst_id:
                                    institutions_list.append(inst_id)
                        institutions = list(set(institutions_list)) if institutions_list else []

                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.openalex_works_raw
                                  (openalex_id, title, publication_year, publication_date,
                                   cited_by_count, authorships, institutions, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (openalex_id) DO UPDATE SET
                                  title = EXCLUDED.title,
                                  publication_year = EXCLUDED.publication_year,
                                  publication_date = EXCLUDED.publication_date,
                                  cited_by_count = EXCLUDED.cited_by_count,
                                  authorships = EXCLUDED.authorships,
                                  institutions = EXCLUDED.institutions,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    openalex_id[:64],
                                    title,
                                    publication_year,
                                    publication_date,
                                    cited_by_count,
                                    Jsonb(authorships),
                                    institutions,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip openalex_id %s: %s", openalex_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(results) < PAGE_SIZE:
                        break

    return {
        "source": "openalex",
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
        # Format ISO 8601 attendu (ex: "2023-06-15")
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        # Tentative fallback
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None