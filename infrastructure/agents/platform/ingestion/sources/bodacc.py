"""BODACC — Bulletin Officiel des Annonces Civiles et Commerciales.

Source #30 d'ARCHITECTURE_DATA_V2.md. API publique gratuite.
Endpoint : https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records
Pas d'auth. Rate-limit raisonnable.
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

BODACC_ENDPOINT = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"
BODACC_EXPORT_URL = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/exports/csv?delimiter=%3B&quote=%22"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 100000
# FULL historique par bulk export streamé (48M annonces possible mais long)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 87600
BULK_BATCH_SIZE = 1000  # commit tous les 1000 rows


async def count_upstream() -> int | None:
    """Compteur amont BODACC via OpenDataSoft (endpoint ?limit=0 → total_count)."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(BODACC_ENDPOINT, params={"limit": 0})
            if r.status_code != 200:
                return None
            v = r.json().get("total_count")
            return int(v) if isinstance(v, int) and v >= 0 else None
    except Exception:
        return None


async def fetch_bodacc_full() -> dict:
    """FULL historical BODACC via /exports/csv streaming (48M annonces).
    CSV = stream ligne par ligne, plus reliable que JSON array.
    Temps estimé : 60-120 min, taille 15-30 GB décompressé."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    inserted = 0
    processed = 0
    errors = 0

    async with httpx.AsyncClient(timeout=7200, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with client.stream("GET", BODACC_EXPORT_URL) as resp:
            if resp.status_code != 200:
                return {"error": f"Export HTTP {resp.status_code}", "rows": 0}

            async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
                async with conn.cursor() as cur:
                    batch: list[tuple] = []
                    import csv
                    import io
                    header = None
                    buffer = ""
                    async for chunk in resp.aiter_text(1024 * 1024):  # 1 MB chunks
                        buffer += chunk
                        lines = buffer.split("\n")
                        buffer = lines.pop()  # garder le dernier incomplet
                        if header is None and lines:
                            reader = csv.reader(io.StringIO(lines[0]), delimiter=";", quotechar='"')
                            header = next(reader, None)
                            lines = lines[1:]
                        if not header:
                            continue
                        for line in lines:
                            if not line.strip():
                                continue
                            try:
                                reader = csv.reader(io.StringIO(line), delimiter=";", quotechar='"')
                                row = next(reader, None)
                                if not row or len(row) < len(header):
                                    continue
                                rec = dict(zip(header, row))
                            except Exception:
                                errors += 1
                                continue

                            processed += 1
                            annonce_id = _s(rec.get("id") or f"{rec.get('numeroannonce', '')}-{rec.get('dateparution', '')}")
                            if not annonce_id:
                                continue
                            batch.append((
                                annonce_id[:128],
                                _parse_date(rec.get("dateparution")),
                                _s(rec.get("typeavis"))[:64],
                                _s(rec.get("familleavis_lib"))[:128],
                                (_s(rec.get("departement_nom_officiel")) or _s(rec.get("cp")))[:8],
                                _s(rec.get("ville"))[:255],
                                _s(rec.get("registre"))[:64],
                                _s(rec.get("numeroannonce"))[:64],
                                _s(rec.get("tribunal"))[:255],
                                _extract_siren(rec),
                                Jsonb(rec),
                            ))
                            if len(batch) >= BULK_BATCH_SIZE:
                                try:
                                    await cur.executemany(
                                        """
                                        INSERT INTO bronze.bodacc_annonces_raw
                                          (annonce_id, date_publication, type_avis, familleavis_lib,
                                           departement, ville, registre, numero_annonce, tribunal, siren, payload)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (annonce_id) DO NOTHING
                                        """,
                                        batch,
                                    )
                                    inserted += cur.rowcount or 0
                                    await conn.commit()
                                    log.info("BODACC bulk : %d inserted / %d processed", inserted, processed)
                                except Exception as e:
                                    log.warning("Batch error: %s", e)
                                    errors += len(batch)
                                batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.bodacc_annonces_raw
                                  (annonce_id, date_publication, type_avis, familleavis_lib,
                                   departement, ville, registre, numero_annonce, tribunal, siren, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (annonce_id) DO NOTHING
                                """,
                                batch,
                            )
                            inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Final batch error: %s", e)

    return {"source": "bodacc", "rows": inserted, "processed": processed, "errors": errors, "mode": "bulk_full"}


async def fetch_bodacc_delta() -> dict:
    """Récupère les annonces BODACC récentes, dedup sur annonce_id.
    1er run : 30 jours ; runs suivants : 48h (couvre délai publication)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    import psycopg as _pg
    async with await _pg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.bodacc_annonces_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    where = f"dateparution >= date'{since}'"
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
                        "order_by": "dateparution DESC",
                    }
                    r = await client.get(BODACC_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("BODACC HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        annonce_id_raw = rec.get("id") or f"{rec.get('numeroannonce', '')}-{rec.get('dateparution', '')}"
                        annonce_id = _s(annonce_id_raw)
                        if not annonce_id:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.bodacc_annonces_raw
                                  (annonce_id, date_publication, type_avis, familleavis_lib,
                                   departement, ville, registre, numero_annonce, tribunal, siren, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (annonce_id) DO NOTHING
                                """,
                                (
                                    annonce_id[:128],
                                    _parse_date(rec.get("dateparution")),
                                    _s(rec.get("typeavis"))[:64],
                                    _s(rec.get("familleavis_lib"))[:128],
                                    (_s(rec.get("departement_nom_officiel")) or _s(rec.get("cp")))[:8],
                                    _s(rec.get("ville"))[:255],
                                    _s(rec.get("registre"))[:64],
                                    _s(rec.get("numeroannonce"))[:64],
                                    _s(rec.get("tribunal"))[:255],
                                    _extract_siren(rec),
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip annonce %s: %s", annonce_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "bodacc",
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


def _extract_siren(rec: dict) -> str | None:
    """SIREN peut être dans plusieurs champs selon le type d'avis."""
    for key in ("siren", "registre"):
        v = rec.get(key)
        vs = str(v) if v is not None else ""
        if len(vs) >= 9 and vs[:9].isdigit():
            return vs[:9]
    listep = rec.get("listepersonnes") or {}
    if isinstance(listep, dict):
        persons = listep.get("personne") or []
        if isinstance(persons, list) and persons:
            try:
                num = (persons[0].get("numeroimmatriculation") or {}).get("numeroidentification")
                nums = str(num) if num is not None else ""
                if len(nums) >= 9 and nums[:9].isdigit():
                    return nums[:9]
            except Exception:
                pass
    return None
