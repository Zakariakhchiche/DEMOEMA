"""Bronze bootstrap — code-generates missing fetchers from spec YAMLs.

Le maintainer existant (engine.run_maintainer_check) ne touche QUE les sources
qui ont déjà tourné au moins une fois (rows dans audit.source_freshness). Une
spec YAML toute neuve sans fetcher .py n'est donc jamais visible — d'où le
gap entre 96 specs YAML et ~68 sources schedulées.

Ce module ajoute un job périodique qui pioche N specs orphelines par tick et
lance discover_and_generate (LLM + endpoint probing + dry-run) en parallèle
via asyncio.gather + Semaphore. Verrou advisory anti-race entre workers
Uvicorn pour qu'un seul tick soit actif à la fois cluster-wide.

Parallélisme : `settings.bronze_codegen_parallelism` (default 4) — calé sur
les rate limits Ollama Cloud (10 req/s) et DeepSeek (50 req/min). Pour 21
specs orphelines : 1 spec/tick séquentiel = ~2h, 4 // = ~30 min. Une fois
toutes les specs couvertes, le tick devient un no-op O(1).
"""
from __future__ import annotations

import asyncio
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


async def _generate_one(sid: str, sem: asyncio.Semaphore) -> dict:
    """Coroutine codegen pour UNE spec orpheline — utilisée par gather.

    Encapsule l'appel à discover_and_generate + try/except + le sémaphore qui
    cap le parallélisme effectif (rate limit LLM).
    """
    # Lazy import à l'intérieur de la coroutine pour éviter de payer le coût
    # d'init des clients LLM si pending est vide.
    from ingestion.codegen import discover_and_generate

    async with sem:
        log.info("[bronze_bootstrap] generating %s", sid)
        try:
            result = await discover_and_generate(sid, max_iterations=2)
            status = result.get("status") or ("error" if "error" in result else "unknown")
            log.info("[bronze_bootstrap] %s → %s", sid, status)
            return {"source_id": sid, "status": status, "result": result}
        except Exception as e:
            log.exception("[bronze_bootstrap] %s raised", sid)
            return {"source_id": sid, "status": "exception", "error": str(e)}


async def run_bronze_bootstrap_tick() -> dict:
    """Pick UP TO N missing fetchers and generate them in parallel.

    Parallélisme : `settings.bronze_codegen_parallelism` (default 4). Tous les
    missing du tick sont schedulés en gather, le Semaphore cap le concurrent
    effectif aux rate limits LLM. Un seul tick actif à la fois cluster-wide
    via advisory lock — la session lock est releasée quand la connexion ferme,
    Postgres nettoie automatiquement si le worker crash.

    Bénéfice vs séquentiel : 21 specs en 1 tick parallèle (~30 min)
    au lieu de 21 ticks séquentiels (~2h). Une fois toutes générées, le tick
    devient un no-op O(1) (list_missing_fetchers renvoie [] → return immédiat).
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

        parallelism = max(1, int(settings.bronze_codegen_parallelism))
        sem = asyncio.Semaphore(parallelism)
        log.info(
            "[bronze_bootstrap] %d specs orphelines, parallelism=%d — gather start",
            len(missing), parallelism,
        )
        results = await asyncio.gather(*[_generate_one(sid, sem) for sid in missing])

        ok = sum(1 for r in results if r["status"] in ("success", "degraded_no_data"))
        fail = len(results) - ok
        log.info(
            "[bronze_bootstrap] tick done : %d ok / %d fail / %d total (parallelism=%d)",
            ok, fail, len(results), parallelism,
        )
        return {
            "ok": ok, "fail": fail, "total": len(results),
            "parallelism": parallelism,
            "remaining_after": fail,  # ceux qui ont fail restent à régénérer au tick suivant
            "results": results,
        }
    finally:
        try:
            lock_conn.close()
        except Exception:
            pass
