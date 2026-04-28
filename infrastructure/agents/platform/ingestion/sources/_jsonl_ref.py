"""RÉFÉRENCE JSONL — pattern pour sources livrant un fichier JSON Lines.

CE FICHIER N'EST PAS EXECUTE — il sert de modèle au codegen pour générer des
fetchers de type "1 objet JSON par ligne" (jsonl/ndjson).

Exemples typiques :
- OpenSanctions entities export
- OpenAlex works dump
- Common Crawl indexes
- HuggingFace datasets

Pattern clé :
  1. httpx.AsyncClient().stream("GET", url) → aiter_lines()
     (ou aiter_bytes pour gz, decompress avec gzip.GzipFile)
  2. Pour chaque ligne : json.loads(line) → row dict
  3. Batch INSERT toutes les BATCH_SIZE lignes
  4. ON CONFLICT (key) DO UPDATE OU DO NOTHING

Format gz : si l'URL finit en .jsonl.gz ou .ndjson.gz, décompresser :
  - gzip.GzipFile(fileobj=BytesIO(bytes), mode='rb')
  - Lire ligne par ligne via TextIOWrapper

Variables clés :
- ENDPOINT_URL : URL du .jsonl ou .jsonl.gz
- KEY_FIELD : nom du champ JSON servant de clé
- TABLE_NAME, KEY_COLUMN
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
from datetime import datetime, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

# À SURCHARGER
ENDPOINT_URL = "https://example.gouv.fr/data/dataset.jsonl.gz"
KEY_FIELD = "id"
TABLE_NAME = "bronze.example_raw"
KEY_COLUMN = "record_id"
BATCH_SIZE = 1000
MAX_ROWS = 1_000_000


async def count_upstream() -> int | None:
    """Pas de count direct — le fichier doit être streamé. None = OK."""
    return None


async def fetch_example_delta() -> dict:
    """Stream .jsonl(.gz) → ligne par ligne → batch INSERT."""
    if not settings.database_url:
        return {"source": "example", "rows": 0, "error": "no DB"}

    is_gz = ENDPOINT_URL.lower().split("?")[0].endswith((".gz", ".gzip"))
    log.info("[example] streaming %s (gz=%s)", ENDPOINT_URL, is_gz)

    n_processed = 0
    n_inserted = 0

    async with httpx.AsyncClient(timeout=3600, follow_redirects=True,
                                  headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        try:
            r = await client.get(ENDPOINT_URL)
        except Exception as e:
            return {"source": "example", "rows": 0, "error": f"download: {e}"}
        if r.status_code != 200:
            return {"source": "example", "rows": 0,
                    "error": f"HTTP {r.status_code}"}
        data = r.content

    if is_gz:
        try:
            data = gzip.decompress(data)
        except Exception as e:
            return {"source": "example", "rows": 0, "error": f"gunzip: {e}"}

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            batch = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if MAX_ROWS and n_processed >= MAX_ROWS:
                    break
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = row.get(KEY_FIELD) if isinstance(row, dict) else None
                if not key:
                    key = hashlib.sha1(line.encode()).hexdigest()[:32]
                batch.append((str(key)[:128], Jsonb(row),
                              datetime.now(tz=timezone.utc)))
                n_processed += 1

                if len(batch) >= BATCH_SIZE:
                    try:
                        await cur.executemany(
                            f"INSERT INTO {TABLE_NAME} ({KEY_COLUMN}, payload, ingested_at) "
                            f"VALUES (%s, %s, %s) "
                            f"ON CONFLICT ({KEY_COLUMN}) DO UPDATE "
                            f"SET payload = EXCLUDED.payload, ingested_at = now()",
                            batch,
                        )
                        n_inserted += cur.rowcount or 0
                        await conn.commit()
                    except Exception as e:
                        log.warning("batch fail: %s", str(e)[:120])
                    batch.clear()

            if batch:
                try:
                    await cur.executemany(
                        f"INSERT INTO {TABLE_NAME} ({KEY_COLUMN}, payload, ingested_at) "
                        f"VALUES (%s, %s, %s) "
                        f"ON CONFLICT ({KEY_COLUMN}) DO UPDATE "
                        f"SET payload = EXCLUDED.payload, ingested_at = now()",
                        batch,
                    )
                    n_inserted += cur.rowcount or 0
                    await conn.commit()
                except Exception as e:
                    log.warning("final batch fail: %s", str(e)[:120])

    return {
        "source": "example",
        "rows": n_inserted,
        "processed": n_processed,
        "mode": "jsonl",
    }
