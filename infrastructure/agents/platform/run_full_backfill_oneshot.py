"""One-shot full bronze backfill — use case "post-migration VPS" ou "remplir
tout le datalake en une fois" sans attendre les ticks scheduler.

Pipeline en 3 phases, exécutable via :

    docker exec demomea-agents-platform python -m run_full_backfill_oneshot

Phase 1 : bronze codegen parallèle (génère les .py des specs orphelines)
Phase 2 : re-discover SOURCES dict (les nouveaux fetchers deviennent visibles)
Phase 3 : fetch parallèle de toutes les sources non-press

Le `PRESS_KEYWORDS` filtre les sources de presse RSS (la presse a son propre
pipeline de Phase 2 OSINT — voir docs/OSINT_STRATEGY.md). Editer la liste si
besoin.

Sortie : résumé tabulaire stdout + logs détaillés via logging. Exit code 0
si tout OK ou seulement les press skip ; 1 sinon.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from datetime import datetime, timezone

# Mots-clés pour skipper les sources de presse — la presse a son pipeline
# Phase 2 OSINT séparé (scraping ciblé via openclaw + proxies). Le backfill
# brutal de presse via RSS feeds n'apporte que ~hundredths d'articles vs
# millions via Google search ciblé.
PRESS_KEYWORDS = (
    "press", "news", "tribune", "echos", "mediapart",
    "figaro", "monde", "usine_nouvelle", "rss",
)

log = logging.getLogger("demoema.full_backfill")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _is_press(sid: str) -> bool:
    s = sid.lower()
    return any(k in s for k in PRESS_KEYWORDS)


async def phase_1_codegen() -> dict:
    """Génère tous les fetchers manquants en parallèle.

    Délègue à run_bronze_bootstrap_tick — depuis le commit qui paralllelise
    bronze_bootstrap, un tick traite tous les missing en parallèle (Semaphore
    capé par bronze_codegen_parallelism). Pas besoin de boucler.
    """
    from ingestion.bronze_bootstrap import list_missing_fetchers, run_bronze_bootstrap_tick

    missing_before = list_missing_fetchers()
    if not missing_before:
        log.info("[phase 1] aucune spec orpheline — skip codegen")
        return {"phase": 1, "skipped": True, "missing_before": 0}

    log.info("[phase 1] %d specs orphelines à générer en parallèle", len(missing_before))
    t0 = time.time()
    result = await run_bronze_bootstrap_tick()
    duration = int(time.time() - t0)

    missing_after = list_missing_fetchers()
    n_recovered = len(missing_before) - len(missing_after)
    log.info(
        "[phase 1] codegen done : %d/%d générés en %ds (%d encore manquants)",
        n_recovered, len(missing_before), duration, len(missing_after),
    )
    return {
        "phase": 1,
        "missing_before": len(missing_before),
        "missing_after": len(missing_after),
        "recovered": n_recovered,
        "duration_s": duration,
        "tick_result": result,
    }


async def phase_3_fetch(parallelism: int) -> dict:
    """Lance run_source en parallèle pour toutes les sources non-press."""
    from config import settings
    from ingestion.engine import SOURCES, run_source, _discover_agent_generated_sources

    # Phase 2 implicite : redécouvrir SOURCES au cas où la phase 1 aurait
    # généré des nouveaux fetchers .py. _discover_agent_generated_sources()
    # est idempotent — n'ajoute que les sids absents de SOURCES.
    _discover_agent_generated_sources()

    press = sorted(s for s in SOURCES if _is_press(s))
    targets = sorted(s for s in SOURCES if not _is_press(s))
    log.info(
        "[phase 3] fetch %d sources non-press en parallèle (parallelism=%d) — %d press skip",
        len(targets), parallelism, len(press),
    )
    log.info("[phase 3] press skip: %s", press)

    sem = asyncio.Semaphore(max(1, parallelism))
    n_done = 0
    started = time.time()

    async def _one(sid: str) -> dict:
        nonlocal n_done
        async with sem:
            t0 = time.time()
            try:
                r = await run_source(sid)
                dur = int(time.time() - t0)
                rows = r.get("rows", 0) if isinstance(r, dict) else 0
                err = r.get("error") if isinstance(r, dict) else None
                status = "OK" if not err else "FAIL"
            except Exception as e:
                dur = int(time.time() - t0)
                rows = 0
                err = f"{type(e).__name__}: {e}"
                status = "EXC"
            n_done += 1
            elapsed = int(time.time() - started)
            log.info(
                "[%3d/%d %4ds] %-4s %-35s rows=%s dur=%ds%s",
                n_done, len(targets), elapsed, status, sid, rows, dur,
                f" err={err[:80]}" if err else "",
            )
            return {"source_id": sid, "status": status, "rows": rows,
                    "duration_s": dur, "error": err}

    results = await asyncio.gather(*[_one(s) for s in targets])
    total_duration = int(time.time() - started)
    ok = sum(1 for r in results if r["status"] == "OK")
    fail = len(results) - ok
    total_rows = sum(r["rows"] or 0 for r in results)
    log.info(
        "[phase 3] DONE : %d ok / %d fail / total_rows=%d en %ds",
        ok, fail, total_rows, total_duration,
    )
    return {
        "phase": 3,
        "total": len(targets),
        "ok": ok,
        "fail": fail,
        "total_rows": total_rows,
        "duration_s": total_duration,
        "press_skipped": press,
        "results": results,
    }


async def main() -> int:
    from config import settings

    started_at = datetime.now(timezone.utc)
    log.info("=" * 80)
    log.info("FULL BACKFILL ONE-SHOT — start at %s", started_at.isoformat())
    log.info("=" * 80)

    p1 = await phase_1_codegen()
    p3 = await phase_3_fetch(parallelism=settings.bronze_fetch_parallelism)

    log.info("=" * 80)
    log.info("FULL BACKFILL DONE")
    log.info(
        "  Phase 1 codegen : %d/%d recovered (%ds)",
        p1.get("recovered", 0), p1.get("missing_before", 0), p1.get("duration_s", 0),
    )
    log.info(
        "  Phase 3 fetch   : %d ok / %d fail / %d total rows (%ds)",
        p3["ok"], p3["fail"], p3["total_rows"], p3["duration_s"],
    )
    log.info("=" * 80)

    return 0 if p3["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
