"""RÉFÉRENCE PARQUET — pattern pour sources livrant un fichier .parquet.

CE FICHIER N'EST PAS EXECUTE — il sert de modèle au codegen pour générer des
fetchers de type "URL HTTP renvoie un fichier Parquet, batch-stream lecture".

Exemples typiques :
- data.gouv.fr (datasets parquet)
- INSEE Sirene Parquet (parfois)
- AWS Open Data (Common Crawl, etc.)

Pattern clé :
  1. Download .parquet via httpx.stream → bytes
  2. pyarrow.parquet.ParquetFile(BytesIO(data))
  3. iter_batches(batch_size=10000) → itère par row_group
  4. Convert chaque batch en list of dicts via batch.to_pylist()
  5. Batch INSERT en SQL — 1 statement par batch (executemany)
  6. ON CONFLICT key DO NOTHING/UPDATE selon usage

Variables clés :
- ENDPOINT_URL : URL du .parquet
- KEY_FIELD_IN_PARQUET : nom de la colonne servant de clé (mapped vers KEY_COLUMN PG)
- TABLE_NAME, KEY_COLUMN
- BATCH_SIZE (souvent égal au row_group naturel)
"""
from __future__ import annotations

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
ENDPOINT_URL = "https://example.gouv.fr/data/dataset.parquet"
KEY_FIELD_IN_PARQUET = "id"
TABLE_NAME = "bronze.example_raw"
KEY_COLUMN = "record_id"
BATCH_SIZE = 10_000
MAX_ROWS = 5_000_000


async def count_upstream() -> int | None:
    """Read parquet metadata pour récupérer num_rows total."""
    try:
        import pyarrow.parquet as pq
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
            # Range GET les premiers 64K bytes — header parquet est en début ou fin
            r = await c.head(ENDPOINT_URL)
            if r.status_code != 200:
                return None
            size = r.headers.get("content-length")
            if size is None:
                return None
            # Téléchargement complet pour compter — simplification ; pour gros fichiers
            # utiliser un Range GET sur les derniers bytes (parquet footer)
            full = await c.get(ENDPOINT_URL)
            if full.status_code != 200:
                return None
            pf = pq.ParquetFile(io.BytesIO(full.content))
            return int(pf.metadata.num_rows)
    except Exception:
        return None


async def fetch_example_delta() -> dict:
    """Download .parquet → iter_batches → batch INSERT."""
    if not settings.database_url:
        return {"source": "example", "rows": 0, "error": "no DB"}

    try:
        import pyarrow.parquet as pq
    except ImportError:
        return {"source": "example", "rows": 0, "error": "pyarrow not installed"}

    log.info("[example] downloading parquet from %s", ENDPOINT_URL)
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

    try:
        pf = pq.ParquetFile(io.BytesIO(data))
    except Exception as e:
        return {"source": "example", "rows": 0, "error": f"parquet: {e}"}

    n_processed = 0
    n_inserted = 0

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            for batch in pf.iter_batches(batch_size=BATCH_SIZE):
                if MAX_ROWS and n_processed >= MAX_ROWS:
                    break
                rows = batch.to_pylist()
                tuples = []
                for row in rows:
                    if MAX_ROWS and n_processed >= MAX_ROWS:
                        break
                    key = row.get(KEY_FIELD_IN_PARQUET)
                    if key is None or key == "":
                        # Fallback : SHA1 du row JSON
                        key = hashlib.sha1(
                            json.dumps(row, sort_keys=True, default=str).encode()
                        ).hexdigest()[:32]
                    tuples.append((str(key)[:128], Jsonb(row),
                                   datetime.now(tz=timezone.utc)))
                    n_processed += 1

                if not tuples:
                    continue
                try:
                    await cur.executemany(
                        f"INSERT INTO {TABLE_NAME} ({KEY_COLUMN}, payload, ingested_at) "
                        f"VALUES (%s, %s, %s) "
                        f"ON CONFLICT ({KEY_COLUMN}) DO NOTHING",
                        tuples,
                    )
                    n_inserted += cur.rowcount or 0
                    await conn.commit()
                except Exception as e:
                    log.warning("batch fail: %s", str(e)[:120])

    return {
        "source": "example",
        "rows": n_inserted,
        "processed": n_processed,
        "mode": "parquet",
    }
