"""RÉFÉRENCE ZIP-CSV — pattern pour sources livrées en ZIP contenant des CSV.

CE FICHIER N'EST PAS EXECUTE — il sert de modèle au codegen (lead-data-engineer)
pour générer des fetchers de type ZIP-of-CSV.

Exemples de sources qui suivent ce pattern : DVF, BAN, SIRENE Stock, cadastre.

Pattern clé :
  1. httpx.AsyncClient().stream("GET", url) → download ZIP complet en mémoire
  2. zipfile.ZipFile(BytesIO(data)) → itère les .csv / .txt membres
  3. Pour chaque membre : csv.reader ligne par ligne
  4. Batch INSERT ... ON CONFLICT (key) DO NOTHING toutes les 1000 lignes
  5. Commit régulier
"""
from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import datetime, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

# À SURCHARGER dans le fetcher concret
ZIP_URL = "https://example.gouv.fr/data/dataset.zip"
TABLE_NAME = "bronze.example_raw"   # à remplacer
KEY_COLUMN = "record_id"
MAX_MEMBERS = 10          # combien de CSV par ZIP traiter max
BATCH_SIZE = 1000
MAX_RECORDS_PER_RUN = 500_000  # safety cap


async def fetch_example_delta() -> dict:
    """Pattern générique ZIP-of-CSV : télécharge, itère, upsert."""
    if not settings.database_url:
        return {"error": "DATABASE_URL absent", "rows": 0}

    total_inserted = 0
    total_processed = 0
    errors = 0
    members_done = []

    async with httpx.AsyncClient(timeout=3600, follow_redirects=True,
                                  headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        # Download ZIP en mémoire — pour fichiers <500MB. Sinon, écrire en /tmp.
        log.info("ZIP download start : %s", ZIP_URL)
        r = await client.get(ZIP_URL)
        if r.status_code != 200:
            return {"error": f"ZIP HTTP {r.status_code}", "rows": 0}
        zip_bytes = r.content
        log.info("ZIP downloaded: %d bytes", len(zip_bytes))

        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                try:
                    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
                except zipfile.BadZipFile as e:
                    return {"error": f"BadZipFile: {e}", "rows": 0}

                # Itérer les membres CSV/TXT
                csv_members = [n for n in zf.namelist()
                               if n.lower().endswith((".csv", ".txt"))][:MAX_MEMBERS]
                log.info("Processing %d CSV members", len(csv_members))

                for member in csv_members:
                    try:
                        with zf.open(member) as fh:
                            # Détecter l'encoding (souvent utf-8 ou latin-1 pour open data FR)
                            raw = fh.read()
                            try:
                                text = raw.decode("utf-8")
                            except UnicodeDecodeError:
                                text = raw.decode("latin-1", errors="replace")

                            # Détecter le séparateur (virgule, pointvirgule, tab)
                            sample = text[:4096]
                            delim = csv.Sniffer().sniff(sample,
                                delimiters=",;|\t").delimiter if "\n" in sample else ","

                            reader = csv.DictReader(io.StringIO(text), delimiter=delim)
                            batch = []
                            for row in reader:
                                total_processed += 1
                                if total_processed >= MAX_RECORDS_PER_RUN:
                                    break
                                # À PERSONNALISER : extraire clés + colonnes selon spec
                                key = row.get(KEY_COLUMN) or row.get("id") or f"{member}_{total_processed}"
                                batch.append((
                                    str(key)[:128],
                                    Jsonb(row),
                                    datetime.now(tz=timezone.utc),
                                ))
                                if len(batch) >= BATCH_SIZE:
                                    try:
                                        await cur.executemany(
                                            f"""
                                            INSERT INTO {TABLE_NAME}
                                              ({KEY_COLUMN}, payload, ingested_at)
                                            VALUES (%s, %s, %s)
                                            ON CONFLICT ({KEY_COLUMN}) DO NOTHING
                                            """,
                                            batch,
                                        )
                                        total_inserted += cur.rowcount or 0
                                        await conn.commit()
                                    except Exception as e:
                                        log.warning("batch fail %s: %s", member, e)
                                        errors += len(batch)
                                    batch.clear()
                            # Flush final
                            if batch:
                                try:
                                    await cur.executemany(
                                        f"""
                                        INSERT INTO {TABLE_NAME}
                                          ({KEY_COLUMN}, payload, ingested_at)
                                        VALUES (%s, %s, %s)
                                        ON CONFLICT ({KEY_COLUMN}) DO NOTHING
                                        """,
                                        batch,
                                    )
                                    total_inserted += cur.rowcount or 0
                                    await conn.commit()
                                except Exception as e:
                                    errors += len(batch)
                        members_done.append(member)
                    except Exception as e:
                        log.warning("member %s skipped: %s", member, e)
                        errors += 1

                    if total_processed >= MAX_RECORDS_PER_RUN:
                        break

    return {
        "source": "example_zip_csv",
        "rows": total_inserted,
        "fetched": total_processed,
        "errors": errors,
        "members_done": len(members_done),
        "mode": "zip_of_csv_batch",
    }
