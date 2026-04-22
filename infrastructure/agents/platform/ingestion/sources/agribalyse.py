"""Agribalyse — ACV agricoles (source #92 ARCHITECTURE_DATA_V2.md).

Source publique via data.ademe.fr (API DataFair). Format CSV via /raw endpoint.
Licence : Etalab 2.0. Pas d'auth. RGPD : données agricoles anonymisées (pas de personnes physiques).
Pattern : CSV streamé ligne par ligne (comme bodacc), batch 1000 → executemany.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

AGRIBALYSE_RAW_URL = "https://data.ademe.fr/data-fair/api/v1/datasets/agribalyse-31-synthese/raw"
AGRIBALYSE_COUNT_URL = "https://data.ademe.fr/data-fair/api/v1/datasets/agribalyse-31-synthese"
BATCH_SIZE = 1000
BACKFILL_DAYS_FIRST_RUN = 3650  # 10 ans pour couvrir l'historique complet


async def count_upstream() -> int | None:
    """Compteur amont Agribalyse via DataFair (endpoint ?limit=0 → total_count)."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(AGRIBALYSE_COUNT_URL, params={"limit": 0})
            if r.status_code != 200:
                return None
            data = r.json()
            # DataFair /raw ne retourne pas de total_count, mais on peut estimer via la taille du CSV
            # On renvoie None pour forcer le mode full (cf. spec)
            return None
    except Exception:
        return None


async def fetch_agribalyse_delta() -> dict:
    """FULL historical Agribalyse via /raw CSV streaming (format CSV direct, pas JSON).
    Gestion first-run : si table vide → backfill complet (pas de fenêtre temporelle).
    Temps estimé : <10 min, taille CSV ~200-500 MB."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    inserted = 0
    processed = 0
    errors = 0

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.agribalyse_products_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    # Si table vide, on fait un FULL (pas de delta possible sur CSV statique)
    # Ici on traite tout le CSV (pattern bodacc_full) car pas de filtre temporel possible
    async with httpx.AsyncClient(timeout=7200, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with client.stream("GET", AGRIBALYSE_RAW_URL) as resp:
            if resp.status_code != 200:
                return {"error": f"Export HTTP {resp.status_code}", "rows": 0}

            async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
                async with conn.cursor() as cur:
                    batch: list[tuple] = []
                    buffer = ""
                    header = None
                    async for chunk in resp.aiter_text(1024 * 1024):  # 1 MB chunks
                        buffer += chunk
                        lines = buffer.split("\n")
                        buffer = lines.pop()  # garder le dernier incomplet
                        if not lines:
                            continue
                        if header is None:
                            # Première ligne = header
                            header = lines.pop(0)
                            if not header:
                                continue
                            header = header.split(";")
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
                            # Clé primaire : ciqual_code (VARCHAR(16))
                            ciqual_code = _s(rec.get("ciqual_code", ""))[:16]
                            if not ciqual_code:
                                continue

                            # Payload complet en JSON
                            payload = Jsonb(rec)

                            batch.append((
                                ciqual_code,
                                _s(rec.get("label", ""))[:512],
                                _n(rec.get("gwp100")),
                                _n(rec.get("acidification")),
                                payload,
                            ))
                            if len(batch) >= BATCH_SIZE:
                                try:
                                    await cur.executemany(
                                        """
                                        INSERT INTO bronze.agribalyse_products_raw
                                          (ciqual_code, label, gwp100, acidification, payload)
                                        VALUES (%s, %s, %s, %s, %s)
                                        ON CONFLICT (ciqual_code) DO UPDATE SET
                                          label = EXCLUDED.label,
                                          gwp100 = EXCLUDED.gwp100,
                                          acidification = EXCLUDED.acidification,
                                          payload = EXCLUDED.payload,
                                          ingested_at = now()
                                        """,
                                        batch,
                                    )
                                    inserted += cur.rowcount or 0
                                    await conn.commit()
                                    log.info("Agribalyse bulk : %d inserted / %d processed", inserted, processed)
                                except Exception as e:
                                    log.warning("Batch error: %s", e)
                                    errors += len(batch)
                                batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.agribalyse_products_raw
                                  (ciqual_code, label, gwp100, acidification, payload)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (ciqual_code) DO UPDATE SET
                                  label = EXCLUDED.label,
                                  gwp100 = EXCLUDED.gwp100,
                                  acidification = EXCLUDED.acidification,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Final batch error: %s", e)

    return {
        "source": "agribalyse",
        "rows": inserted,
        "fetched": processed,
        "errors": errors,
        "mode": "full",
    }


def _s(value) -> str:
    """Convertit n'importe quelle valeur en str sûre pour slicing (None → '')."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _n(value) -> float | None:
    """Convertit en NUMERIC (float) ou None. Gère virgule française."""
    if value is None:
        return None
    s = _s(value).strip()
    if not s:
        return None
    try:
        # Remplacer ',' par '.' pour float
        return float(s.replace(",", "."))
    except Exception:
        return None