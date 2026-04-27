"""Bronze bootstrap — code-generates missing fetchers from spec YAMLs.

Le maintainer existant (engine.run_maintainer_check) ne touche QUE les sources
qui ont déjà tourné au moins une fois (rows dans audit.source_freshness). Une
spec YAML toute neuve sans fetcher .py n'est donc jamais visible — d'où le
gap entre 96 specs YAML et ~68 sources schedulées.

Ce module ajoute un job périodique qui pioche UNE spec orpheline à chaque
tick et lance discover_and_generate (3 itérations LLM + endpoint probing +
dry-run). Une fois toutes les specs couvertes, le tick devient un no-op.
Verrou advisory anti-race entre workers Uvicorn.

Design intentionnellement lent : un spec à la fois, 5 min entre tentatives,
pour ne pas saturer Ollama Cloud ni Postgres. Pour 28 specs orphelines, ça
fait ~2-3h de bootstrap full — non-bloquant pour le démarrage du container.
"""
from __future__ import annotations

import logging
from pathlib import Path

import psycopg
import yaml

from config import settings

log = logging.getLogger("demoema.bronze_bootstrap")

# Postgres advisory lock id, distinct du silver bootstrap (0x51EA77B05).
_BRONZE_BOOTSTRAP_LOCK_ID = 0xB202E80057BAB

INGESTION_DIR = Path(__file__).parent
SPECS_DIR = INGESTION_DIR / "specs"
SOURCES_DIR = INGESTION_DIR / "sources"


def list_missing_fetchers() -> list[str]:
    """Return source_ids whose spec exists but whose `sources/{sid}.py` doesn't.

    Skips specs without a `source_id` field, files starting with `_`, and any
    spec whose Python module fails to import (= treated as already present
    but broken — that's the maintainer's job, not ours)."""
    if not SPECS_DIR.exists() or not SOURCES_DIR.exists():
        return []
    missing: list[str] = []
    for spec_path in sorted(SPECS_DIR.glob("*.yaml")):
        if spec_path.name.startswith("_"):
            continue
        try:
            spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            log.warning("[bronze_bootstrap] spec parse fail %s: %s", spec_path.name, e)
            continue
        sid = spec.get("source_id")
        if not sid:
            continue
        if not (SOURCES_DIR / f"{sid}.py").exists():
            missing.append(sid)
    return missing


async def run_bronze_bootstrap_tick() -> dict:
    """Pick ONE missing fetcher and try to generate it. Returns the run summary.

    Uses a session-level advisory lock so multiple Uvicorn workers don't fight
    over the same generation slot. The lock is released when the connection
    closes — Postgres takes care of cleanup if the worker crashes.
    """
    if not settings.database_url:
        return {"error": "no database_url"}

    missing = list_missing_fetchers()
    if not missing:
        return {"done": True, "remaining": 0}

    # Hold the lock for the whole tick. Multiple workers will see the same
    # `missing` list but only one acquires the lock and progresses.
    try:
        lock_conn = psycopg.connect(settings.database_url, autocommit=True)
    except Exception as e:
        return {"error": f"lock_conn: {e}"}

    try:
        with lock_conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (_BRONZE_BOOTSTRAP_LOCK_ID,))
            got_lock = cur.fetchone()[0]
        if not got_lock:
            log.info("[bronze_bootstrap] another worker holds the lock — skipping tick")
            return {"skipped_due_to_lock": True, "remaining": len(missing)}

        # Lazy import to avoid pulling in heavy LLM clients at module load.
        try:
            from ingestion.codegen import discover_and_generate
        except ImportError as e:
            return {"error": f"codegen unavailable: {e}"}

        # Process the first candidate alphabetically — deterministic ordering
        # across ticks so the operator can predict what will be tried next.
        sid = missing[0]
        log.info(
            "[bronze_bootstrap] generating %s (%d remaining including this one)",
            sid, len(missing),
        )
        try:
            result = await discover_and_generate(sid, max_iterations=2)
            status = result.get("status") or ("error" if "error" in result else "unknown")
            log.info("[bronze_bootstrap] %s → %s", sid, status)
            return {
                "source_id": sid,
                "status": status,
                "remaining_after": len(missing) - 1 if status in ("success", "degraded_no_data") else len(missing),
                "result": result,
            }
        except Exception as e:
            log.exception("[bronze_bootstrap] %s raised", sid)
            return {"source_id": sid, "status": "exception", "error": str(e),
                    "remaining_after": len(missing)}
    finally:
        try:
            lock_conn.close()
        except Exception:
            pass
