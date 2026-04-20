"""INSEE Sirene V3 — dump officiel files.data.gouv StockEtablissement (31M).

Téléchargement streaming ZIP → disque, puis streaming CSV depuis le ZIP, batch INSERT 1000.
~2.8GB ZIP compressé, ~15GB CSV, 31M rows. ETA 2-4h.

Ne PAS charger en RAM (8GB VPS). Tout est streamé.
"""
from __future__ import annotations

import csv
import io
import logging
import os
import tempfile
import zipfile
from datetime import datetime, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

STOCK_ETABLISSEMENT_URL = (
    "https://object.files.data.gouv.fr/data-pipeline-open/"
    "siren/stock/StockEtablissement_utf8.zip"
)
TMP_ZIP_PATH = "/tmp/sirene_stock_etab.zip"
BATCH_SIZE = 1000
COMMIT_EVERY = 10_000     # commit cumulatif toutes les 10k rows
LOG_EVERY = 100_000       # log progression toutes les 100k rows
MAX_ROWS = 50_000_000     # safety cap


async def fetch_insee_sirene_v3_delta() -> dict:
    if not settings.database_url:
        return {"source": "insee_sirene_v3", "rows": 0, "error": "no DB"}

    # ──────────── 1. Download ZIP streaming → disk ────────────
    log.info("Sirene: download %s → %s", STOCK_ETABLISSEMENT_URL, TMP_ZIP_PATH)
    try:
        async with httpx.AsyncClient(timeout=7200, follow_redirects=True,
                                      headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
            async with client.stream("GET", STOCK_ETABLISSEMENT_URL) as resp:
                if resp.status_code != 200:
                    return {"source": "insee_sirene_v3", "rows": 0,
                            "error": f"HTTP {resp.status_code}"}
                written = 0
                with open(TMP_ZIP_PATH, "wb") as f:
                    async for chunk in resp.aiter_bytes(4 * 1024 * 1024):  # 4 MB chunks
                        f.write(chunk)
                        written += len(chunk)
                        if written % (100 * 1024 * 1024) < 4 * 1024 * 1024:  # log every ~100 MB
                            log.info("Sirene ZIP download: %d MB", written // (1024 * 1024))
                log.info("Sirene ZIP download complete: %d MB", written // (1024 * 1024))
    except Exception as e:
        log.exception("Sirene download failed")
        return {"source": "insee_sirene_v3", "rows": 0,
                "error": f"download: {type(e).__name__}: {e}"}

    # ──────────── 2. Extract + stream CSV rows ────────────
    total_inserted = 0
    total_processed = 0
    errors = 0

    try:
        zf = zipfile.ZipFile(TMP_ZIP_PATH)
    except zipfile.BadZipFile as e:
        return {"source": "insee_sirene_v3", "rows": 0, "error": f"BadZip: {e}"}

    csv_members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not csv_members:
        return {"source": "insee_sirene_v3", "rows": 0, "error": "no CSV in ZIP"}
    log.info("Sirene CSV members: %s", csv_members)

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            for member in csv_members:
                log.info("Sirene: processing CSV %s", member)
                with zf.open(member) as fh:
                    # Stream line-by-line : pas de read() complet en RAM
                    text_fh = io.TextIOWrapper(fh, encoding="utf-8", newline="")
                    reader = csv.DictReader(text_fh, delimiter=",")
                    batch = []
                    for row in reader:
                        total_processed += 1
                        if total_processed > MAX_ROWS:
                            break
                        # La colonne clé dans StockEtablissement_utf8.csv
                        key_val = row.get("siret") or row.get("SIRET")
                        if not key_val or len(str(key_val)) < 14:
                            errors += 1
                            continue
                        siret = str(key_val)[:14]
                        batch.append((
                            siret,
                            row.get("siren", "")[:9] if row.get("siren") else None,
                            (row.get("activitePrincipaleEtablissement") or "")[:8] or None,
                            (row.get("denominationUsuelleEtablissement") or "")[:512] or None,
                            (row.get("codePostalEtablissement") or "")[:8] or None,
                            (row.get("libelleCommuneEtablissement") or "")[:255] or None,
                            row.get("dateCreationEtablissement") or None,
                            (row.get("etatAdministratifEtablissement") or "")[:32] or None,
                            Jsonb(row),
                            datetime.now(tz=timezone.utc),
                        ))
                        if len(batch) >= BATCH_SIZE:
                            try:
                                await cur.executemany(
                                    """
                                    INSERT INTO bronze.insee_sirene_siret_raw
                                      (siret, siren, naf, denomination, code_postal,
                                       commune, date_creation, etat, payload, ingested_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (siret) DO NOTHING
                                    """,
                                    batch,
                                )
                                total_inserted += cur.rowcount or 0
                                if total_processed % COMMIT_EVERY < BATCH_SIZE:
                                    await conn.commit()
                                if total_processed % LOG_EVERY < BATCH_SIZE:
                                    log.info("Sirene: %d processed, %d inserted, %d errors",
                                             total_processed, total_inserted, errors)
                            except Exception as e:
                                log.warning("Sirene batch fail: %s", e)
                                errors += len(batch)
                            batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.insee_sirene_siret_raw
                                  (siret, siren, naf, denomination, code_postal,
                                   commune, date_creation, etat, payload, ingested_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (siret) DO NOTHING
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            errors += len(batch)
            await conn.commit()

    # Cleanup temp file
    try:
        os.unlink(TMP_ZIP_PATH)
    except Exception:
        pass

    return {
        "source": "insee_sirene_v3",
        "rows": total_inserted,
        "fetched": total_processed,
        "errors": errors,
        "mode": "zip_stream_csv",
    }
