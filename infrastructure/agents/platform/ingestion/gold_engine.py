"""Gold engine — scheduler refresh des gold tables (UPSERT depuis silvers).

Différences vs silver_engine :
- Refresh = ré-exécuter le SQL UPSERT (INSERT ... ON CONFLICT) depuis le
  fichier gold_transforms/{name}.sql, plutôt que REFRESH MATERIALIZED VIEW
- Pattern table physique → indexes survivent, refresh = juste UPDATE/INSERT
- Pour les gold-of-gold (cibles_ma_top, etc.) : refresh dans l'ordre topo
- Bootstrap one-shot via gold_codegen.bootstrap_missing_golds

Architecture identique au silver_engine pour la résilience :
- Advisory lock distinct par gold (_REFRESH_GOLD_LOCK_BASE)
- Audit log dans audit.gold_runs
- Maintainer 30 min retry sur failed
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

log = logging.getLogger("demoema.gold_engine")

GOLD_SPECS_DIR = Path(__file__).parent / "gold_specs"
GOLD_TRANSFORMS_DIR = Path(__file__).parent / "gold_transforms"

GOLDS: dict[str, dict] = {}

# Advisory locks distincts du silver
_REFRESH_GOLD_LOCK_BASE = 0x60BD7700057B
_GOLD_MAINTAINER_LOCK_ID = 0x60BD7700057C


def _refresh_gold_lock_id(gold_name: str) -> int:
    """Lock ID unique par gold via hashtext."""
    h = hashlib.sha1(gold_name.encode()).hexdigest()
    return _REFRESH_GOLD_LOCK_BASE ^ int(h[:14], 16)


def load_all_gold_specs() -> dict[str, dict]:
    """Load gold_specs/*.yaml (skip _ prefix)."""
    out: dict[str, dict] = {}
    if not GOLD_SPECS_DIR.exists():
        return out
    for p in GOLD_SPECS_DIR.glob("*.yaml"):
        if p.stem.startswith("_"):
            continue
        try:
            with p.open(encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}
            name = spec.get("silver_name") or f"gold.{p.stem}"
            if not name.startswith("gold."):
                name = f"gold.{name}"
            spec["silver_name"] = name
            out[name] = spec
        except Exception as e:
            log.warning("gold spec load failed %s: %s", p, e)
    return out


def _build_trigger(spec: dict):
    """Cron ou interval — copy de silver_engine."""
    cfg = spec.get("refresh_trigger") or "interval_hours=24"
    if isinstance(cfg, dict):
        if "cron" in cfg:
            return CronTrigger.from_crontab(cfg["cron"])
        if "interval_hours" in cfg:
            return IntervalTrigger(hours=int(cfg["interval_hours"]))
    if isinstance(cfg, str):
        if cfg.startswith("cron="):
            return CronTrigger.from_crontab(cfg.replace("cron=", "").strip())
        if "=" in cfg:
            k, v = cfg.split("=", 1)
            if k.strip() == "interval_hours":
                return IntervalTrigger(hours=int(v))
            if k.strip() == "interval_minutes":
                return IntervalTrigger(minutes=int(v))
    return IntervalTrigger(hours=24)


async def run_gold_bootstrap() -> dict:
    """Wrapper pour APScheduler (one-shot au boot)."""
    try:
        from ingestion.gold_codegen import bootstrap_missing_golds
    except ImportError as e:
        return {"error": f"gold_codegen unavailable: {e}"}
    return await bootstrap_missing_golds(force_empty=True)


async def run_gold_refresh(gold_name: str, trigger_source: str = "scheduler") -> dict:
    """Refresh d'une gold table — ré-exécute le SQL UPSERT depuis fichier.

    Pour table physique (physical=true) :
    - Lit gold_transforms/{name}.sql
    - Extrait la partie après le dernier CREATE TABLE / CREATE INDEX :
      le INSERT ... ON CONFLICT
    - Exécute juste cette partie pour refresh incrémental

    Pour MV (physical=false) :
    - REFRESH MATERIALIZED VIEW gold.X
    """
    if not settings.database_url:
        return {"error": "no db"}

    spec_name = gold_name.replace("gold.", "")
    sql_path = GOLD_TRANSFORMS_DIR / f"{spec_name}.sql"
    if not sql_path.exists():
        return {"error": f"SQL file not found: {sql_path}"}

    spec_path = GOLD_SPECS_DIR / f"{spec_name}.yaml"
    if not spec_path.exists():
        return {"error": f"spec not found: {spec_path}"}
    with spec_path.open(encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}
    physical = spec.get("physical", True)

    start_dt = datetime.now(tz=timezone.utc)
    lock_id = _refresh_gold_lock_id(gold_name)

    lock_conn = psycopg.connect(settings.database_url, autocommit=True)
    try:
        with lock_conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
            if not cur.fetchone()[0]:
                log.info("[gold] %s : refresh skipped (lock held)", gold_name)
                return {"gold_name": gold_name, "status": "skipped",
                        "lock_skipped": True}

        t0 = time.time()
        try:
            with psycopg.connect(settings.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET statement_timeout = 0")
                    if physical:
                        # Ré-exécute le SQL complet (CREATE TABLE IF NOT EXISTS
                        # + INDEXes IF NOT EXISTS sont idempotents, INSERT
                        # ... ON CONFLICT fait l'UPSERT).
                        sql = sql_path.read_text(encoding="utf-8")
                        cur.execute(sql)
                    else:
                        # MV : juste REFRESH
                        cur.execute(f"REFRESH MATERIALIZED VIEW {gold_name}")
                    cur.execute(f"SELECT count(*) FROM {gold_name}")
                    rows_after = (cur.fetchone() or [None])[0]
                conn.commit()
            duration_ms = int((time.time() - t0) * 1000)
            log.info("[gold] %s refreshed (%d rows in %dms)",
                     gold_name, rows_after or 0, duration_ms)
            return {
                "gold_name": gold_name, "status": "success",
                "rows_after": rows_after, "duration_ms": duration_ms,
                "trigger_source": trigger_source,
            }
        except Exception as e:
            duration_ms = int((time.time() - t0) * 1000)
            log.exception("[gold] %s refresh failed", gold_name)
            return {
                "gold_name": gold_name, "status": "failed",
                "error": f"{type(e).__name__}: {e}",
                "duration_ms": duration_ms,
            }
    finally:
        try:
            lock_conn.close()
        except Exception:
            pass


def start_gold_scheduler(scheduler) -> int:
    """Register gold bootstrap (one-shot) + per-gold refresh jobs."""
    global GOLDS
    GOLDS = load_all_gold_specs()
    if not GOLDS:
        log.info("[gold] no gold_specs/*.yaml found — skip scheduler")
        return 0

    # 1. One-shot bootstrap au boot (5s après le silver bootstrap pour laisser
    # les silvers se construire d'abord)
    scheduler.add_job(
        run_gold_bootstrap, trigger="date",
        run_date=datetime.now(tz=timezone.utc).replace(microsecond=0),
        id="gold_bootstrap", name="Gold bootstrap missing/empty tables",
        max_instances=1, coalesce=True, replace_existing=True,
        misfire_grace_time=600,
    )

    # 2. Refresh job per gold
    for name, spec in GOLDS.items():
        trigger = _build_trigger(spec)
        scheduler.add_job(
            run_gold_refresh, trigger=trigger, args=[name, "scheduler"],
            id=f"gold_refresh_{name.replace('gold.', '')}",
            name=f"Gold refresh {name}",
            max_instances=1, coalesce=True, replace_existing=True,
        )
        log.info("[gold] registered refresh %s (trigger=%s)",
                 name, spec.get("refresh_trigger"))

    log.info("[gold] scheduler registered bootstrap + %d gold tables", len(GOLDS))
    return len(GOLDS)
