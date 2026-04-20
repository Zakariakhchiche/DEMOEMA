"""OpenSanctions — consolidated sanctions list (source #12).

Dataset statements : https://data.opensanctions.org/datasets/latest/default/statements.json
Ou export JSON : https://data.opensanctions.org/datasets/latest/default/entities.ftm.json
Pour MVP : on utilise l'API REST publique avec pagination.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

# Endpoint statements légers : 1 ligne = 1 entité
OPENSANCTIONS_URL = "https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv"
ENTITIES_JSON_URL = "https://data.opensanctions.org/datasets/latest/sanctions/entities.ftm.json"
# FULL snapshot : 200K entités sanctions mondiales (module compliance KYC)
MAX_ROWS_PER_RUN = 1000000


async def fetch_opensanctions_delta() -> dict:
    """Download entities JSON (paginé par ligne), insert bronze dedup par entity_id."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    inserted = 0
    processed = 0

    async with httpx.AsyncClient(timeout=120, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with client.stream("GET", ENTITIES_JSON_URL) as resp:
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}", "rows": 0}

            async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
                async with conn.cursor() as cur:
                    batch: list[tuple] = []
                    BATCH_SIZE = 500
                    async for line in resp.aiter_lines():
                        if not line or processed >= MAX_ROWS_PER_RUN:
                            break
                        try:
                            import json
                            rec = json.loads(line)
                        except Exception:
                            continue
                        entity_id = rec.get("id") or rec.get("caption", "")
                        if not entity_id:
                            continue
                        props = rec.get("properties", {})
                        batch.append(
                            (
                                entity_id[:128],
                                (rec.get("caption") or "")[:512],
                                (rec.get("schema") or "")[:64],
                                props.get("country") or [],
                                props.get("program") or [],
                                _parse_dt(rec.get("first_seen")),
                                _parse_dt(rec.get("last_seen")),
                                Jsonb(rec),
                            )
                        )
                        processed += 1
                        if len(batch) >= BATCH_SIZE:
                            inserted += await _flush_batch(cur, batch)
                            batch.clear()
                            await conn.commit()
                    if batch:
                        inserted += await _flush_batch(cur, batch)
                        await conn.commit()

    return {"source": "opensanctions", "rows": inserted, "processed": processed}


async def _flush_batch(cur, batch: list[tuple]) -> int:
    await cur.executemany(
        """
        INSERT INTO bronze.opensanctions_entities_raw
          (entity_id, name, schema_type, countries, programs, first_seen, last_seen, payload)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (entity_id) DO UPDATE SET
          name = EXCLUDED.name,
          last_seen = EXCLUDED.last_seen,
          payload = EXCLUDED.payload,
          ingested_at = now()
        """,
        batch,
    )
    return cur.rowcount or 0


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
