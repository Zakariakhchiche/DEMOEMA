"""Ingestion engine — orchestrateur APScheduler + audit + completeness.

- Chaque source définit son schedule + fetcher
- Résultats loggés dans audit.agent_actions + audit.source_freshness
- Job completeness quotidien : compare local vs amont (si count_upstream dispo)
- Maintainer : régénère sources failed/incomplete/ok-stagnantes avec backoff + parking
- Anomalies → audit.alerts (future hook Slack via agent Superviseur)
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

import psycopg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from ingestion.sources.bodacc import fetch_bodacc_delta
from ingestion.sources.opensanctions import fetch_opensanctions_delta
from ingestion.sources.gels_avoirs import fetch_gels_avoirs_full

log = logging.getLogger("demoema.ingestion")

scheduler: AsyncIOScheduler | None = None

# ─── Garde-fous anti-boucle ────────────────────────────────────────────────
MAX_RETRY_COUNT = 3            # au-delà → status='parked'
MAINTAINER_BATCH = 5           # nombre max de sources régénérées par run
OK_STAGNANT_HOURS = 24         # seuil de "ok mais 0 rows depuis trop longtemps"
# Backoff : heures entre 2 tentatives en fonction de retry_count
BACKOFF_HOURS = {0: 1, 1: 6, 2: 36}

# Registry des sources
SOURCES: dict[str, dict] = {
    "bodacc": {
        "fetcher": fetch_bodacc_delta,
        "trigger": IntervalTrigger(hours=1),
        "sla_minutes": 90,
        "description": "BODACC — 48M annonces, delta horaire",
    },
    "opensanctions": {
        "fetcher": fetch_opensanctions_delta,
        "trigger": IntervalTrigger(hours=6),
        "sla_minutes": 720,
        "description": "OpenSanctions — 200k entities, delta 6h",
    },
    "gels_avoirs": {
        "fetcher": fetch_gels_avoirs_full,
        "trigger": CronTrigger(hour=3, minute=30, timezone="Europe/Paris"),
        "sla_minutes": 1500,
        "description": "DGTrésor gels — full refresh nuit 03:30 Paris",
    },
}


async def _audit_action(
    agent_role: str,
    source_id: str | None,
    action: str,
    status: str,
    duration_ms: int,
    payload_out: dict,
) -> None:
    """Insertion dans audit.agent_actions — jamais bloquante."""
    if not settings.database_url:
        return
    try:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO audit.agent_actions
                      (agent_role, task_id, source_id, action, status, duration_ms, payload_out)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (agent_role, str(uuid.uuid4()), source_id, action, status,
                     duration_ms, psycopg.types.json.Jsonb(payload_out)),
                )
    except Exception:
        log.exception("audit.agent_actions insert failed (non-fatal)")


async def _audit_log(
    source_id: str,
    action: str,
    status: str,
    duration_ms: int,
    payload_out: dict,
) -> None:
    """Log résultat d'un fetcher + met à jour source_freshness avec la logique anti-boucle."""
    if not settings.database_url:
        log.warning("DATABASE_URL non configuré, skip audit log")
        return
    try:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO audit.agent_actions
                      (agent_role, task_id, source_id, action, status, duration_ms, payload_out)
                    VALUES ('worker', %s, %s, %s, %s, %s, %s)
                    """,
                    (str(uuid.uuid4()), source_id, action, status, duration_ms,
                     psycopg.types.json.Jsonb(payload_out)),
                )
                rows = int(payload_out.get("rows") or 0)
                sla = SOURCES.get(source_id, {}).get("sla_minutes", 1440)

                if status == "success":
                    # Reset retry_count si on a remonté des lignes cette fois
                    new_status = "ok" if rows > 0 else "ok"  # base status (complet recalculé par completeness check)
                    await cur.execute(
                        """
                        INSERT INTO audit.source_freshness
                          (source_id, last_success_at, rows_last_run, total_rows, sla_minutes, status, retry_count)
                        VALUES (%s, now(), %s, %s, %s, %s, 0)
                        ON CONFLICT (source_id) DO UPDATE SET
                          last_success_at = EXCLUDED.last_success_at,
                          rows_last_run   = EXCLUDED.rows_last_run,
                          total_rows      = audit.source_freshness.total_rows + EXCLUDED.rows_last_run,
                          retry_count     = CASE WHEN EXCLUDED.rows_last_run > 0
                                                 THEN 0
                                                 ELSE audit.source_freshness.retry_count END,
                          status          = CASE
                              WHEN audit.source_freshness.status IN ('parked','ok_empty') THEN audit.source_freshness.status
                              ELSE 'ok'
                          END
                        """,
                        (source_id, rows, rows, sla, new_status),
                    )
                else:
                    await cur.execute(
                        """
                        INSERT INTO audit.source_freshness
                          (source_id, last_failure_at, sla_minutes, status, retry_count)
                        VALUES (%s, now(), %s, 'failed', 0)
                        ON CONFLICT (source_id) DO UPDATE SET
                          last_failure_at = EXCLUDED.last_failure_at,
                          status          = CASE
                              WHEN audit.source_freshness.status = 'parked' THEN 'parked'
                              ELSE 'failed'
                          END
                        """,
                        (source_id, sla),
                    )
    except Exception:
        log.exception("Audit log failure (non-fatal)")


async def run_source(source_id: str) -> dict:
    """Execute l'ingestion d'une source + log audit. Appelable via endpoint manuel ou cron."""
    if source_id not in SOURCES:
        return {"error": f"source inconnue : {source_id}"}

    fetcher = SOURCES[source_id]["fetcher"]
    log.info("Ingestion start : %s", source_id)
    t0 = time.time()
    try:
        result = await fetcher()
        duration_ms = int((time.time() - t0) * 1000)
        result["duration_ms"] = duration_ms
        result["started_at"] = datetime.fromtimestamp(t0, tz=timezone.utc).isoformat()
        log.info("Ingestion done : %s rows=%d in %dms", source_id, result.get("rows", 0), duration_ms)
        await _audit_log(source_id, "fetch+insert", "success", duration_ms, result)
        return result
    except Exception as e:
        duration_ms = int((time.time() - t0) * 1000)
        log.exception("Ingestion failed : %s", source_id)
        err = {"error": str(e), "type": type(e).__name__, "duration_ms": duration_ms}
        await _audit_log(source_id, "fetch+insert", "failed", duration_ms, err)
        return err


def _discover_agent_generated_sources() -> None:
    """Auto-discovery : scan specs/*.yaml + import sources/*.py au boot pour populer SOURCES.
    Permet aux fetchers générés par agent de survivre aux restarts container."""
    import importlib
    import yaml
    from pathlib import Path
    specs_dir = Path(__file__).parent / "specs"
    sources_dir = Path(__file__).parent / "sources"
    if not specs_dir.exists():
        return
    for spec_path in specs_dir.glob("*.yaml"):
        try:
            spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
            sid = spec.get("source_id")
            if not sid or sid in SOURCES:
                continue  # déjà hardcoded
            if not (sources_dir / f"{sid}.py").exists():
                continue
            mod = importlib.import_module(f"ingestion.sources.{sid}")
            fetcher = getattr(mod, f"fetch_{sid}_delta", None) or getattr(mod, f"fetch_{sid}_full", None)
            if not fetcher:
                log.warning("Auto-discovery : fetch_%s_delta/full introuvable dans %s.py", sid, sid)
                continue
            from ingestion.codegen import _build_trigger
            SOURCES[sid] = {
                "fetcher": fetcher,
                "trigger": _build_trigger(spec.get("refresh_trigger", "interval_hours=24")),
                "sla_minutes": spec.get("sla_minutes", 1440),
                "description": spec.get("name", sid),
            }
            log.info("Auto-discovered source : %s", sid)
        except Exception as e:
            log.warning("Discovery fail %s: %s", spec_path.name, e)


def start_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        return
    _discover_agent_generated_sources()
    scheduler = AsyncIOScheduler(timezone="Europe/Paris")
    for source_id, cfg in SOURCES.items():
        scheduler.add_job(
            run_source,
            trigger=cfg["trigger"],
            args=[source_id],
            id=f"ingest_{source_id}",
            name=f"Ingestion {source_id}",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
    # Supervisor daily report 08:00 Paris
    scheduler.add_job(
        run_daily_supervisor_report,
        trigger=CronTrigger(hour=8, minute=0, timezone="Europe/Paris"),
        id="supervisor_daily",
        name="Supervisor daily report 08:00 Paris",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    # Maintainer : regenerate failed/incomplete fetchers every 6h
    scheduler.add_job(
        run_maintainer_check,
        trigger=IntervalTrigger(hours=6),
        id="maintainer_6h",
        name="Maintainer regenerate failed sources",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    # Completeness check : compare local vs amont tous les jours à 04:00 Paris
    scheduler.add_job(
        run_completeness_check,
        trigger=CronTrigger(hour=4, minute=0, timezone="Europe/Paris"),
        id="completeness_daily",
        name="Completeness check (upstream vs local)",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    # Silver layer: register refresh jobs + silver maintainer
    try:
        from ingestion.silver_engine import start_silver_scheduler
        n_silvers = start_silver_scheduler(scheduler)
    except Exception as e:
        log.warning("Silver engine init skipped: %s", e)
        n_silvers = 0

    # Neo4j graph rebuild (daily 04:00 Paris)
    try:
        from ingestion.neo4j_sync import run_neo4j_rebuild
        scheduler.add_job(
            run_neo4j_rebuild,
            trigger=CronTrigger(hour=4, minute=0, timezone="Europe/Paris"),
            id="neo4j_rebuild_daily",
            name="Neo4j graph rebuild (dirigeants multi-mandats)",
            max_instances=1, coalesce=True, replace_existing=True,
        )
        log.info("Neo4j rebuild job registered (04:00 daily Paris)")
    except Exception as e:
        log.warning("Neo4j rebuild init skipped: %s", e)

    scheduler.start()
    log.info(
        "Scheduler démarré — %d sources + %d silvers + 5 managers "
        "(supervisor+maintainer+completeness+silver_maintainer+neo4j_rebuild)",
        len(SOURCES), n_silvers,
    )


def stop_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None


def list_jobs() -> list[dict]:
    if scheduler is None:
        return []
    return [
        {
            "id": j.id,
            "name": j.name,
            "next_run": j.next_run_time.isoformat() if j.next_run_time else None,
            "trigger": str(j.trigger),
        }
        for j in scheduler.get_jobs()
    ]


async def run_daily_supervisor_report() -> dict:
    """Rapport quotidien — synthèse freshness de toutes les sources + Slack."""
    if not settings.database_url:
        return {"error": "no DB"}
    report = await freshness_report()
    now = datetime.now(tz=timezone.utc)
    ok = [r for r in report if r.get("status") == "ok"]
    failed = [r for r in report if r.get("status") == "failed"]
    incomplete = [r for r in report if r.get("status") == "incomplete"]
    parked = [r for r in report if r.get("status") == "parked"]
    ok_empty = [r for r in report if r.get("status") == "ok_empty"]
    total_rows = sum(r.get("total_rows") or 0 for r in report)

    lines = [
        f"# 📊 DEMOEMA — Rapport ingestion {now.strftime('%Y-%m-%d')}",
        f"_généré à {now.strftime('%H:%M UTC')}_",
        "",
        f"**Total**: {len(report)} sources tracked · **{total_rows:,} rows** bronze cumulés",
        f"**Santé**: ✅ {len(ok)} OK · ⚠️ {len(incomplete)} incomplet · ❌ {len(failed)} échec · 🅿️ {len(parked)} parked · ∅ {len(ok_empty)} vide amont",
        "",
    ]
    if failed:
        lines.append("## ❌ Sources en échec")
        for r in failed:
            lines.append(f"- `{r['source_id']}` — last failure {r.get('last_failure_at','?')}")
        lines.append("")
    if incomplete:
        lines.append("## ⚠️ Sources incomplètes")
        for r in incomplete:
            pct = r.get("completeness_pct")
            lines.append(f"- `{r['source_id']}` — {r.get('total_rows') or 0:,}/{r.get('upstream_row_count') or '?'} ({pct}%)")
        lines.append("")
    if parked:
        lines.append("## 🅿️ Sources parkées (intervention humaine requise)")
        for r in parked:
            lines.append(f"- `{r['source_id']}` — {r.get('parked_reason','?')}")
        lines.append("")
    if ok:
        lines.append("## ✅ Sources OK (top 10 par volume)")
        for r in sorted(ok, key=lambda x: -(x.get("total_rows") or 0))[:10]:
            lines.append(f"- `{r['source_id']}` — {(r.get('total_rows') or 0):,} rows · last {r.get('last_success_at','?')}")
    md = "\n".join(lines)
    log.info("[Supervisor] %d OK, %d incomplet, %d failed, %d parked, %d total rows",
             len(ok), len(incomplete), len(failed), len(parked), total_rows)

    if settings.slack_webhook_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as c:
                await c.post(settings.slack_webhook_url, json={"text": md})
        except Exception:
            log.exception("Slack supervisor notif failed")

    return {
        "ok": len(ok), "incomplete": len(incomplete), "failed": len(failed),
        "parked": len(parked), "ok_empty": len(ok_empty),
        "total_rows": total_rows, "report": md,
    }


async def run_completeness_check() -> dict:
    """Quotidien : appelle count_upstream() pour chaque source, met à jour freshness.

    Logique :
    - upstream = None          → skip (inconnu, pas de changement de status)
    - upstream = 0             → status='ok_empty' (source légitimement vide, JAMAIS retentée)
    - local/upstream >= 99%    → status='ok'
    - local/upstream <  99%    → status='incomplete'
    Toujours idempotent : pas de side-effect au-delà de la mise à jour freshness.
    """
    if not settings.database_url:
        return {"error": "no DB"}
    try:
        from ingestion.counters import get_upstream_count
    except ImportError:
        return {"error": "counters module unavailable"}

    t0 = time.time()
    results: list[dict] = []
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT source_id, total_rows, status FROM audit.source_freshness"
            )
            rows = await cur.fetchall()

            for source_id, total_rows, current_status in rows:
                # On ne touche jamais une source parkée
                if current_status == "parked":
                    continue
                try:
                    upstream = await get_upstream_count(source_id)
                except Exception as e:
                    log.warning("count_upstream crashed for %s: %s", source_id, e)
                    upstream = None

                if upstream is None:
                    results.append({"source": source_id, "upstream": None, "skipped": True})
                    continue

                total_rows = total_rows or 0
                if upstream == 0:
                    new_status = "ok_empty"
                    pct = None
                else:
                    pct = round((total_rows / upstream) * 100, 2) if upstream else None
                    new_status = "ok" if total_rows >= upstream * 0.99 else "incomplete"

                # Ne dégrade pas 'failed' en 'incomplete' (priorité à l'info échec)
                if current_status == "failed" and new_status == "incomplete":
                    new_status = "failed"

                await cur.execute(
                    """
                    UPDATE audit.source_freshness
                    SET upstream_row_count  = %s,
                        upstream_checked_at = now(),
                        completeness_pct    = %s,
                        status              = CASE
                            WHEN status = 'parked' THEN 'parked'
                            ELSE %s
                        END
                    WHERE source_id = %s
                    """,
                    (upstream, pct, new_status, source_id),
                )
                results.append({
                    "source": source_id, "upstream": upstream,
                    "local": total_rows, "pct": pct, "status": new_status,
                })
            await conn.commit()

    duration_ms = int((time.time() - t0) * 1000)
    await _audit_action(
        "completeness", None, "completeness_check", "success", duration_ms,
        {"checked": len(results), "with_upstream": sum(1 for r in results if not r.get("skipped"))},
    )
    log.info("[Completeness] checked=%d with_upstream=%d in %dms",
             len(results), sum(1 for r in results if not r.get("skipped")), duration_ms)
    return {"checked": len(results), "details": results, "duration_ms": duration_ms}


async def run_maintainer_check() -> dict:
    """Toutes les 6h — régénère les fetchers en échec, incomplets, ou ok-stagnants.

    Anti-boucle :
    - Skip sources en 'parked' ou 'ok_empty' (jamais retentées auto)
    - Backoff exponentiel : 1h → 6h → 36h entre tentatives
    - Max 3 retries consécutifs → passage en 'parked' (intervention humaine)
    - LIMIT 5 par run pour lisser la charge
    """
    if not settings.database_url:
        return {"error": "no DB"}
    try:
        import psycopg as _pg
        from ingestion.codegen import generate_fetcher
    except ImportError:
        return {"error": "codegen unavailable"}

    t0 = time.time()
    async with await _pg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            # Candidats : failed, incomplete, degraded, ou ok-stagnant
            # Filtrés par backoff (last_regen_attempt_at assez ancien vs retry_count)
            await cur.execute(
                f"""
                SELECT source_id, status, retry_count
                FROM audit.source_freshness
                WHERE status NOT IN ('parked','ok_empty')
                  AND retry_count < {MAX_RETRY_COUNT}
                  AND (
                        status IN ('failed','incomplete','degraded')
                     OR (status = 'ok' AND (rows_last_run IS NULL OR rows_last_run = 0)
                         AND (total_rows IS NULL OR total_rows = 0)
                         AND last_success_at < now() - interval '{OK_STAGNANT_HOURS} hours')
                  )
                  AND (last_regen_attempt_at IS NULL
                       OR last_regen_attempt_at < now() - (
                           CASE retry_count
                               WHEN 0 THEN interval '{BACKOFF_HOURS[0]} hours'
                               WHEN 1 THEN interval '{BACKOFF_HOURS[1]} hours'
                               ELSE interval '{BACKOFF_HOURS[2]} hours'
                           END))
                ORDER BY
                    CASE status WHEN 'failed' THEN 1 WHEN 'incomplete' THEN 2 ELSE 3 END,
                    last_regen_attempt_at NULLS FIRST
                LIMIT {MAINTAINER_BATCH}
                """
            )
            candidates = await cur.fetchall()

    regen_results = []
    for sid, current_status, retry_count in candidates:
        log.info("[Maintainer] regen candidate: %s (status=%s retry=%d)",
                 sid, current_status, retry_count)
        attempt_t0 = time.time()

        # Fetch last error from audit.agent_actions → feedback for LLM-corrective regen.
        # Without this, codegen takes the deterministic template path and produces the
        # exact same broken code each cycle (Sisyphus loop).
        feedback = None
        try:
            async with await _pg.AsyncConnection.connect(settings.database_url) as _fconn:
                async with _fconn.cursor() as _fcur:
                    await _fcur.execute(
                        """
                        SELECT payload_out->>'type' AS err_type,
                               payload_out->>'error' AS err_msg,
                               action,
                               created_at
                        FROM audit.agent_actions
                        WHERE source_id = %s
                          AND status = 'failed'
                          AND created_at > now() - interval '30 days'
                          AND payload_out ? 'error'
                        ORDER BY created_at DESC
                        LIMIT 3
                        """,
                        (sid,),
                    )
                    rows = await _fcur.fetchall()
            if rows:
                parts = []
                for err_type, err_msg, action, created_at in rows:
                    parts.append(f"- [{action}] {err_type or 'Error'}: {err_msg or '(no message)'}")
                feedback = (
                    f"The previous generated fetcher for `{sid}` failed with these errors "
                    f"(most recent first):\n" + "\n".join(parts) +
                    "\n\nFix the root cause. Common patterns to check:\n"
                    "- /exports/json endpoints return a JSON array directly, not {results:[...]} — "
                    "handle both shapes.\n"
                    "- .csv.gz endpoints return gzipped CSV bytes, not JSON — gunzip + csv.DictReader.\n"
                    "- data-fair /raw endpoints return CSV — check content-type before r.json().\n"
                    "- ODS v1 /api/records/1.0/search requires `dataset=` in params (httpx strips URL query "
                    "when params= is passed)."
                )
                log.info("[Maintainer] %s: passing feedback (%d prior errors) to codegen", sid, len(rows))
        except Exception:
            log.exception("[Maintainer] failed fetching prior errors for %s — regen without feedback", sid)

        try:
            r = await generate_fetcher(sid, feedback=feedback)
            regen_status = "regen_success" if r.get("file") else "regen_failed"
            regen_results.append({"source": sid, "status": regen_status,
                                  "details": r, "prev_retry": retry_count})
        except Exception as e:
            r = {"error": str(e), "type": type(e).__name__}
            regen_status = "regen_exception"
            regen_results.append({"source": sid, "status": regen_status,
                                  "error": str(e), "prev_retry": retry_count})

        # Update source_freshness : incrémenter retry, parker si dépassement
        new_retry = retry_count + 1
        park = new_retry >= MAX_RETRY_COUNT and regen_status != "regen_success"
        try:
            async with await _pg.AsyncConnection.connect(settings.database_url) as conn:
                async with conn.cursor() as cur:
                    if park:
                        await cur.execute(
                            """
                            UPDATE audit.source_freshness
                            SET retry_count           = %s,
                                last_regen_attempt_at = now(),
                                parked_at             = now(),
                                parked_reason         = %s,
                                status                = 'parked'
                            WHERE source_id = %s
                            """,
                            (new_retry,
                             f"max_retries_exceeded ({MAX_RETRY_COUNT} tentatives, dernière: {regen_status})",
                             sid),
                        )
                        regen_results[-1]["parked"] = True
                        log.warning("[Maintainer] PARKED %s après %d tentatives", sid, new_retry)
                    else:
                        await cur.execute(
                            """
                            UPDATE audit.source_freshness
                            SET retry_count           = %s,
                                last_regen_attempt_at = now()
                            WHERE source_id = %s
                            """,
                            (new_retry, sid),
                        )
                    await conn.commit()
        except Exception:
            log.exception("Failed updating source_freshness retry for %s", sid)

        attempt_dur = int((time.time() - attempt_t0) * 1000)
        await _audit_action(
            "maintainer", sid, "regenerate_fetcher", regen_status, attempt_dur,
            {"retry_count_new": new_retry, "prev_status": current_status,
             "parked": park, "details": r},
        )

    total_dur = int((time.time() - t0) * 1000)
    log.info("[Maintainer] regenerated %d sources in %dms", len(regen_results), total_dur)
    await _audit_action(
        "maintainer", None, "maintainer_run", "success", total_dur,
        {"candidates": len(candidates), "regenerated": len(regen_results),
         "parked": sum(1 for r in regen_results if r.get("parked"))},
    )

    if regen_results and settings.slack_webhook_url:
        try:
            import httpx
            parked_count = sum(1 for r in regen_results if r.get("parked"))
            msg = (f"🔧 Maintainer: {len(regen_results)} fetchers régénérés"
                   + (f", ⚠️ {parked_count} parkés" if parked_count else "")
                   + ": " + ", ".join(r["source"] for r in regen_results))
            async with httpx.AsyncClient(timeout=10) as c:
                await c.post(settings.slack_webhook_url, json={"text": msg})
        except Exception:
            pass

    return {"regenerated_count": len(regen_results), "candidates": len(candidates),
            "details": regen_results}


async def freshness_report() -> list[dict]:
    if not settings.database_url:
        return []
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT source_id, last_success_at, last_failure_at, rows_last_run,
                       total_rows, upstream_row_count, completeness_pct, retry_count,
                       last_regen_attempt_at, parked_at, parked_reason,
                       sla_minutes, status
                FROM audit.source_freshness ORDER BY source_id
                """
            )
            rows = await cur.fetchall()
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
