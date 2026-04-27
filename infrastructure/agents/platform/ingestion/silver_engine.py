"""Silver engine — scheduler des refresh MATERIALIZED VIEW + maintainer staleness.

Flow :
- Au boot : charge tous les YAML de silver_specs/ → register 1 job cron par silver
- Chaque job : REFRESH MATERIALIZED VIEW + log audit.silver_runs + update silver_freshness
- Maintainer (toutes les 30 min) : détecte staleness, échecs consécutifs, regen via silver_codegen
  avec feedback de l'erreur précédente.
"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
import yaml
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import settings

log = logging.getLogger("demoema.silver_engine")

SILVER_SPECS_DIR = Path(__file__).parent / "silver_specs"

# Registre runtime des silvers chargés
SILVERS: dict[str, dict] = {}

# ═══════════ Lifecycle ═══════════

def load_all_specs() -> dict[str, dict]:
    """Load every YAML in silver_specs/ (skip files starting with _)."""
    out: dict[str, dict] = {}
    for p in SILVER_SPECS_DIR.glob("*.yaml"):
        if p.stem.startswith("_"):
            continue
        try:
            with p.open(encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}
            name = spec.get("silver_name") or f"silver.{p.stem}"
            if not name.startswith("silver."):
                name = f"silver.{name}"
            spec["silver_name"] = name
            out[name] = spec
        except Exception as e:
            log.warning("spec load failed %s: %s", p, e)
    return out


def _build_trigger(spec: dict):
    """Accept either cron='..' or interval_hours=N or interval_minutes=N in spec.refresh_trigger."""
    cfg = spec.get("refresh_trigger") or "interval_hours=24"
    if isinstance(cfg, dict):
        if "cron" in cfg:
            return CronTrigger.from_crontab(cfg["cron"])
        if "interval_hours" in cfg:
            return IntervalTrigger(hours=int(cfg["interval_hours"]))
        if "interval_minutes" in cfg:
            return IntervalTrigger(minutes=int(cfg["interval_minutes"]))
    if isinstance(cfg, str) and "=" in cfg:
        k, v = cfg.split("=", 1)
        if k.strip() == "interval_hours":
            return IntervalTrigger(hours=int(v))
        if k.strip() == "interval_minutes":
            return IntervalTrigger(minutes=int(v))
        if k.strip() == "cron":
            return CronTrigger.from_crontab(v.strip())
    return IntervalTrigger(hours=24)


def start_silver_scheduler(scheduler) -> int:
    """Register all silver refresh jobs on the passed AsyncIOScheduler.

    Schedules a one-shot bootstrap (5s after boot) that fills in any silver
    spec whose MV is missing or empty. This is what makes the migration
    scenario work end-to-end: drop a fresh Postgres in, ingest Bronze, start
    the engine, and silver builds itself from YAML specs without any manual
    SQL. Refresh jobs and the maintainer follow.
    """
    global SILVERS
    SILVERS = load_all_specs()

    scheduler.add_job(
        run_silver_bootstrap, trigger="date",
        run_date=datetime.now(tz=timezone.utc).replace(microsecond=0),
        id="silver_bootstrap", name="Silver bootstrap missing/empty MVs",
        max_instances=1, coalesce=True, replace_existing=True,
        misfire_grace_time=300,
    )
    for name, spec in SILVERS.items():
        trigger = _build_trigger(spec)
        job_id = f"silver_refresh_{name.replace('silver.', '')}"
        scheduler.add_job(
            run_silver_refresh, trigger=trigger, args=[name, "scheduler"],
            id=job_id, name=f"Silver refresh {name}",
            max_instances=1, coalesce=True, replace_existing=True,
        )
        log.info("[silver] registered refresh %s (trigger=%s)", name, spec.get("refresh_trigger"))
    scheduler.add_job(
        run_silver_maintainer, trigger=IntervalTrigger(minutes=30),
        id="silver_maintainer", name="Silver maintainer staleness",
        max_instances=1, coalesce=True, replace_existing=True,
    )
    log.info("[silver] scheduler registered bootstrap + %d silvers + 1 maintainer", len(SILVERS))
    return len(SILVERS)


async def run_silver_bootstrap() -> dict:
    """Wrapper around silver_codegen.bootstrap_missing_silvers (cron-friendly)."""
    try:
        from ingestion.silver_codegen import bootstrap_missing_silvers
    except ImportError as e:
        return {"error": f"silver_codegen unavailable: {e}"}
    return await bootstrap_missing_silvers(force_empty=True)


# ═══════════ Refresh runner ═══════════

def _run_uid(silver_name: str, when: datetime) -> str:
    raw = f"{silver_name}|{when.isoformat()}"
    return hashlib.sha1(raw.encode()).hexdigest()[:40]


async def run_silver_refresh(silver_name: str, trigger_source: str = "scheduler") -> dict:
    """REFRESH MATERIALIZED VIEW + log audit, sérialisé par silver_name.

    Concurrency model :
    - advisory lock SESSION-level par silver_name : 2 workers Uvicorn ne
      peuvent pas refresh le même silver concurremment (gaspillage CPU/IO,
      double count(*)). Un skip-on-locked retourne `lock_skipped: True`
      sans incrémenter consecutive_fails.
    - Autres silvers en parallèle = autorisés, on ne sérialise pas tout.

    Performance :
    - 2 connexions au lieu de 3 : conn#1 (autocommit) pour heartbeat
      INSERT 'running' + lock acquisition + pré-count. conn#2 (autocommit
      mais BEGIN/COMMIT explicite) pour REFRESH + post-count + UPDATE
      audit + UPSERT freshness DANS LA MÊME TX (ferme la fenêtre de
      désync où la MV était refreshed mais audit pas mis à jour).
    - Pré-count via reltuples (rapide), post-count via count(*) exact
      (utilisé pour delta_pct précis dans la détection anomalie).
    - ANALYZE après le REFRESH pour rafraîchir les stats (sinon le
      bootstrap suivant pense que la MV est vide via reltuples=-1).
    """
    if not settings.database_url:
        return {"error": "no db"}

    start_dt = datetime.now(tz=timezone.utc)
    run_uid = _run_uid(silver_name, start_dt)
    lock_id = _refresh_lock_id_for(silver_name)

    # ─── Conn 1 : lock acquisition + heartbeat 'running' ─────────────
    schema, table = silver_name.split(".", 1) if "." in silver_name else ("silver", silver_name)
    rows_before: int | None = None
    lock_conn = psycopg.connect(settings.database_url, autocommit=True)
    try:
        with lock_conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
            if not cur.fetchone()[0]:
                log.info("[silver] %s : refresh skipped (another worker holds the lock)", silver_name)
                return {
                    "silver_name": silver_name, "status": "skipped",
                    "lock_skipped": True, "duration_ms": 0,
                }
            # Pré-count rapide via reltuples (estimation suffisante avant refresh)
            try:
                cur.execute(
                    "SELECT c.reltuples::bigint FROM pg_class c JOIN pg_namespace n "
                    "ON n.oid = c.relnamespace WHERE n.nspname=%s AND c.relname=%s",
                    (schema, table),
                )
                row = cur.fetchone()
                rows_before = row[0] if row and row[0] is not None and row[0] >= 0 else None
            except Exception:
                rows_before = None
            cur.execute(
                """
                INSERT INTO audit.silver_runs (run_uid, silver_name, refresh_start, rows_before, status, trigger_source)
                VALUES (%s, %s, %s, %s, 'running', %s)
                ON CONFLICT (run_uid) DO NOTHING
                """,
                (run_uid, silver_name, start_dt, rows_before, trigger_source),
            )

        # ─── Conn 2 : REFRESH + post-count exact + audit/freshness atomic ───
        t0 = time.time()
        error_msg: str | None = None
        rows_after: int | None = None
        status = "failed"
        try:
            with psycopg.connect(settings.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET statement_timeout = 0")
                    cur.execute(f"REFRESH MATERIALIZED VIEW {silver_name}")
                    cur.execute(f"SELECT count(*) FROM {silver_name}")
                    rows_after = (cur.fetchone() or [None])[0]
                conn.commit()
            status = "ok"
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            log.exception("[silver] refresh failed %s", silver_name)

        duration_ms = int((time.time() - t0) * 1000)
        end_dt = datetime.now(tz=timezone.utc)
        delta_rows = (rows_after or 0) - (rows_before or 0) if (rows_before is not None and rows_after is not None) else None
        delta_pct = (100.0 * delta_rows / rows_before) if (delta_rows is not None and rows_before) else None

        # Audit UPDATE + freshness UPSERT dans une seule tx, et ANALYZE post-refresh
        spec = SILVERS.get(silver_name) or {}
        sla = int(spec.get("sla_minutes", 1440))
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE audit.silver_runs
                    SET refresh_end=%s, duration_ms=%s, rows_after=%s, delta_rows=%s, delta_pct=%s,
                        status=%s, error=%s
                    WHERE run_uid=%s
                    """,
                    (end_dt, duration_ms, rows_after, delta_rows, delta_pct, status, error_msg, run_uid),
                )
                cur.execute(
                    """
                    INSERT INTO audit.silver_freshness (silver_name, last_refresh_at, last_status, current_rows,
                                                         sla_minutes, is_stale, last_delta_pct, consecutive_fails, updated_at)
                    VALUES (%s, %s, %s, %s, %s, false, %s, CASE WHEN %s='ok' THEN 0 ELSE 1 END, now())
                    ON CONFLICT (silver_name) DO UPDATE SET
                      last_refresh_at = EXCLUDED.last_refresh_at,
                      last_status     = EXCLUDED.last_status,
                      current_rows    = EXCLUDED.current_rows,
                      sla_minutes     = EXCLUDED.sla_minutes,
                      is_stale        = false,
                      last_delta_pct  = EXCLUDED.last_delta_pct,
                      consecutive_fails = CASE
                        WHEN EXCLUDED.last_status = 'ok' THEN 0
                        ELSE audit.silver_freshness.consecutive_fails + 1
                      END,
                      updated_at      = now()
                    """,
                    (silver_name, end_dt, status, rows_after, sla, delta_pct, status),
                )
            conn.commit()

        # ANALYZE post-refresh (autocommit, hors tx audit) — rafraîchit reltuples
        # pour que le bootstrap bronze_sources_all_empty et _silver_state ne
        # voient pas une vue "vide" alors qu'elle vient d'être refreshed.
        if status == "ok":
            try:
                with psycopg.connect(settings.database_url, autocommit=True) as conn, conn.cursor() as cur:
                    cur.execute(f"ANALYZE {silver_name}")
            except Exception:
                log.warning("[silver] ANALYZE failed for %s (non-fatal)", silver_name)

        return {
            "silver_name": silver_name,
            "status": status,
            "duration_ms": duration_ms,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "delta_pct": delta_pct,
            "error": error_msg,
        }
    finally:
        try:
            lock_conn.close()  # auto-release du advisory lock SESSION-level
        except Exception:
            pass


# ═══════════ Maintainer ═══════════

ANOMALY_DROP_PCT = -15.0     # if rows drop more than 15 %, treat as anomaly
MAX_CONSECUTIVE_FAILS = 3
PARK_AFTER_REGEN_FAILS = 5   # après N régen LLM successives qui restent applied=false → parked
                              # (au-delà = gaspillage budget LLM, intervention humaine requise)

# Postgres advisory lock IDs — DISTINCTS du bootstrap (0x51EA77B05) pour ne
# pas bloquer mutuellement bootstrap ↔ maintainer ↔ refresh. Chaque sémantique
# son lock. _MAINTAINER_LOCK_ID est constant (1 maintainer cluster-wide) ;
# _REFRESH_LOCK_BASE est combiné avec hashtext(silver_name) pour locker
# par-silver (parallélisme légitime entre silvers, sérialisation par silver).
_MAINTAINER_LOCK_ID = 0x51EA77B06       # "SILVA77BO6" — incrément du bootstrap
_REFRESH_LOCK_BASE = 0x51EA77B07         # XOR avec hashtext(silver_name) pour ID unique


def _refresh_lock_id_for(silver_name: str) -> int:
    """ID advisory lock par silver — XOR base + sha1 short pour rester dans int64."""
    h = int.from_bytes(hashlib.sha1(silver_name.encode()).digest()[:6], "big")
    return _REFRESH_LOCK_BASE ^ h


async def run_silver_maintainer() -> dict:
    """Find stale / failing / empty / never-run silvers and regen via codegen.

    Catches four kinds of broken silvers :
      1. stale            — last_refresh_at older than sla
      2. failing          — consecutive_fails >= MAX_CONSECUTIVE_FAILS
      3. anomalous drop   — last_delta_pct < ANOMALY_DROP_PCT
      4. empty            — last_status='ok' but current_rows=0 (silent zero)
      5. never run        — spec YAML present but no row in silver_freshness
    """
    if not settings.database_url:
        return {"error": "no db"}
    try:
        from ingestion.silver_codegen import generate_silver_sql
    except ImportError as e:
        return {"error": f"silver_codegen unavailable: {e}"}

    # Advisory lock cluster-wide : un seul maintainer tourne à la fois entre
    # les workers Uvicorn. Distinct du _BOOTSTRAP_LOCK_ID — bootstrap et
    # maintainer peuvent tourner en parallèle car ils gèrent des choses
    # différentes (bootstrap = silvers manquants, maintainer = silvers
    # existants en dérive). Mais 2 maintainers concurrents = double cost LLM.
    lock_conn = psycopg.connect(settings.database_url, autocommit=True)
    try:
        with lock_conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (_MAINTAINER_LOCK_ID,))
            if not cur.fetchone()[0]:
                log.info("[silver_maintainer] another worker holds the lock — skipping tick")
                return {"skipped_due_to_lock": True, "candidates": 0, "regen_results": []}

        return await _run_maintainer_locked(generate_silver_sql)
    finally:
        try:
            lock_conn.close()
        except Exception:
            pass


async def _run_maintainer_locked(generate_silver_sql) -> dict:
    """Body du maintainer une fois le lock acquis. Extrait pour clarifier
    le scope du lock dans run_silver_maintainer."""
    to_regen: list[dict] = []
    with psycopg.connect(settings.database_url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT silver_name, last_refresh_at, last_status, consecutive_fails,
                   sla_minutes, last_delta_pct, current_rows
            FROM audit.silver_freshness
            WHERE NOT parked
              AND (
                   last_refresh_at < now() - (sla_minutes || ' minutes')::interval
                OR consecutive_fails >= %s
                OR last_delta_pct < %s
                OR (last_status = 'ok' AND COALESCE(current_rows, 0) = 0)
              )
            ORDER BY last_refresh_at NULLS FIRST
            LIMIT 5
            """,
            (MAX_CONSECUTIVE_FAILS, ANOMALY_DROP_PCT),
        )
        for sname, last, status, fails, sla, delta_pct, rows in cur.fetchall():
            reason = []
            if fails and fails >= MAX_CONSECUTIVE_FAILS:
                reason.append(f"consecutive_fails={fails}")
            if delta_pct is not None and delta_pct < ANOMALY_DROP_PCT:
                reason.append(f"anomaly_delta_pct={delta_pct:.1f}")
            if last and (datetime.now(tz=timezone.utc) - last).total_seconds() > sla * 60:
                reason.append("staleness")
            if status == "ok" and (rows is None or rows == 0):
                reason.append("empty_after_ok_refresh")
            to_regen.append({
                "silver_name": sname,
                "last_status": status,
                "reason": ", ".join(reason) or "unknown",
            })

    # Catch silvers that have a YAML but were never refreshed (no freshness row).
    spec_names = set((SILVERS or load_all_specs()).keys())
    if spec_names:
        with psycopg.connect(settings.database_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT silver_name FROM audit.silver_freshness")
            seen = {r[0] for r in cur.fetchall()}
        for sname in sorted(spec_names - seen):
            if len(to_regen) >= 5:
                break
            to_regen.append({
                "silver_name": sname, "last_status": None,
                "reason": "never_run",
            })

    regen_results = []
    for cand in to_regen:
        sname = cand["silver_name"]
        # Le feedback vient de DEUX sources :
        #  1. audit.silver_runs : erreurs de REFRESH MATERIALIZED VIEW (post-build)
        #  2. audit.silver_specs_versions : erreurs de validation/apply au moment
        #     de la génération initiale (bootstrap). Crucial pour les silvers qui
        #     n'ont jamais réussi à exister — leur dernière trace est dans
        #     silver_specs_versions, pas silver_runs.
        feedback_lines = []
        with psycopg.connect(settings.database_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT error FROM audit.silver_runs
                WHERE silver_name = %s AND status != 'ok' AND error IS NOT NULL
                ORDER BY refresh_start DESC LIMIT 1
                """,
                (sname,),
            )
            row = cur.fetchone()
            if row and row[0]:
                feedback_lines.append(f"Refresh error: {row[0]}")
            cur.execute(
                """
                SELECT validation_status, validation_msg, applied
                FROM audit.silver_specs_versions
                WHERE silver_name = %s AND (validation_status != 'ok' OR applied = false)
                ORDER BY generated_at DESC LIMIT 1
                """,
                (sname,),
            )
            row = cur.fetchone()
            if row:
                vstat, vmsg, applied = row
                if vstat != "ok":
                    feedback_lines.append(f"Codegen validation failed: {vmsg}")
                elif applied is False:
                    feedback_lines.append(
                        f"Last codegen produced valid-looking SQL but PG rejected it at execute time. "
                        f"Inspect the previously generated SQL for type mismatches, undefined columns "
                        f"(check that JOIN aliases reference columns that actually exist in the source), "
                        f"or wrong cast operators."
                    )
        feedback_full = (
            "\n".join(feedback_lines) + f"\nReason for regen: {cand['reason']}."
            if feedback_lines else cand["reason"]
        )

        log.info("[silver_maintainer] regen %s (%s)", sname, cand["reason"])
        try:
            r = await generate_silver_sql(sname, feedback=feedback_full, apply_immediately=True)
            regen_results.append({**cand, "regen": r})
        except Exception as e:
            log.exception("[silver_maintainer] regen failed %s", sname)
            regen_results.append({**cand, "regen": {"error": str(e)}})

    # Parking : silvers ayant accumulé PARK_AFTER_REGEN_FAILS échecs codegen
    # consécutifs (validation invalid OU applied=false). Au-delà de ce seuil,
    # le LLM hallucine systématiquement (schéma source incompatible, edge case
    # business non couvert) — intervention humaine requise. Évite cost runaway.
    parked_count = 0
    with psycopg.connect(settings.database_url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            WITH recent_fails AS (
                SELECT silver_name, count(*) AS n_fails
                FROM audit.silver_specs_versions
                WHERE generated_at > now() - interval '7 days'
                  AND (validation_status != 'ok' OR applied = false)
                GROUP BY silver_name
                HAVING count(*) >= %s
            )
            UPDATE audit.silver_freshness f
            SET parked = true,
                parked_reason = 'codegen_fails_' || rf.n_fails::text || '_in_7d',
                updated_at = now()
            FROM recent_fails rf
            WHERE f.silver_name = rf.silver_name
              AND NOT f.parked
            RETURNING f.silver_name
            """,
            (PARK_AFTER_REGEN_FAILS,),
        )
        parked = cur.fetchall()
        parked_count = len(parked)
        for (sname,) in parked:
            log.warning("[silver_maintainer] PARKED %s (≥%d codegen fails in 7d) — manual unpark required",
                        sname, PARK_AFTER_REGEN_FAILS)

    return {
        "candidates": len(to_regen),
        "regen_results": regen_results,
        "parked_now": parked_count,
    }
