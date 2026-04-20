"""
EdRCF 6.0 — routers/admin.py
Endpoints admin pipeline Bronze/Silver/BODACC/RNE/Pappers.
Extraits de main.py pour garder ce dernier lisible.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

router = APIRouter(prefix="/api/admin", tags=["admin-pipeline"])


def _check_secret(secret: str) -> None:
    cron = os.getenv("CRON_SECRET", "")
    if cron and secret != cron:
        raise HTTPException(status_code=401, detail="Unauthorized")


# =============================================================================
# Stats
# =============================================================================

@router.get("/bronze-stats")
async def bronze_stats(secret: str = Query(default="")):
    """Stats Bronze / Silver / BODACC / Pappers sur MotherDuck."""
    _check_secret(secret)
    try:
        import bronze_pipeline as bp
        return await bp.api_bronze_stats()
    except Exception as e:
        raise HTTPException(500, f"Erreur bronze-stats: {e}")


# =============================================================================
# Bronze + Silver
# =============================================================================

@router.get("/load-bronze")
async def load_bronze(
    background_tasks: BackgroundTasks,
    secret: str = Query(default=""),
):
    """Lance le pipeline Bronze SIRENE + Silver en arrière-plan (~20-40 min)."""
    _check_secret(secret)

    async def _run():
        import bronze_pipeline as bp
        bp._PIPELINE_STATUS.update({
            "running": True, "step": "setup", "error": None,
            "started_at": datetime.utcnow().isoformat(), "finished_at": None,
        })
        try:
            bp.setup_tables()
            bp._PIPELINE_STATUS["step"] = "bronze_load"
            await asyncio.to_thread(bp.load_bronze)
            bp._PIPELINE_STATUS["step"] = "silver_build"
            await asyncio.to_thread(bp.build_silver)
            bp._PIPELINE_STATUS["step"] = "sync_supabase"
            await bp.sync_silver_to_supabase(top_n=5000, priority="score")
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "done",
                "finished_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "error",
                "error": str(e), "finished_at": datetime.utcnow().isoformat(),
            })
            print(f"[ADMIN] Erreur load-bronze: {e}")

    background_tasks.add_task(_run)
    return {"status": "started", "message": "Pipeline Bronze/Silver lancé (~20-40 min). Voir /api/admin/bronze-stats"}


# =============================================================================
# Gold (M&A scoring + KPIs)
# =============================================================================

@router.get("/build-gold")
async def build_gold_endpoint(
    background_tasks: BackgroundTasks,
    secret: str = Query(default=""),
):
    """Construit la couche Gold depuis Silver (M&A scoring + enrichissement + KPIs)."""
    _check_secret(secret)

    async def _run():
        import bronze_pipeline as bp
        bp._PIPELINE_STATUS.update({
            "running": True, "step": "gold_build", "error": None,
            "started_at": datetime.utcnow().isoformat(), "finished_at": None,
        })
        try:
            await asyncio.to_thread(bp.build_gold)
            bp._PIPELINE_STATUS["step"] = "sync_supabase"
            await bp.sync_silver_to_supabase(top_n=5000, priority="score")
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "done",
                "finished_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "error",
                "error": str(e), "finished_at": datetime.utcnow().isoformat(),
            })
            print(f"[ADMIN] Erreur build-gold: {e}")

    background_tasks.add_task(_run)
    return {"status": "started", "message": "Gold build lancé (~5-15 min). Voir /api/admin/bronze-stats"}


# =============================================================================
# BODACC
# =============================================================================

@router.get("/load-bodacc")
async def load_bodacc(
    background_tasks: BackgroundTasks,
    secret: str = Query(default=""),
    since: str = Query(default="2023-01-01"),
):
    """Charge les annonces BODACC (DILA tar.gz → fallback ODS) + flag Silver."""
    _check_secret(secret)

    async def _run():
        import bronze_pipeline as bp
        bp._PIPELINE_STATUS.update({
            "running": True, "step": "bodacc_load", "error": None,
            "started_at": datetime.utcnow().isoformat(), "finished_at": None,
        })
        try:
            bp.setup_tables()
            total = await asyncio.to_thread(bp.load_bodacc_dila, since)
            if total == 0:
                print("[ADMIN] DILA vide — fallback ODS JSON paginé…")
                total = await bp._load_bodacc_ods(since)
            print(f"[ADMIN] BODACC chargé: {total:,} lignes")
            bp._PIPELINE_STATUS["step"] = "bodacc_flag"
            await asyncio.to_thread(bp.flag_bodacc_silver)
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "done",
                "finished_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "error",
                "error": str(e), "finished_at": datetime.utcnow().isoformat(),
            })
            print(f"[ADMIN] Erreur load-bodacc: {e}")

    background_tasks.add_task(_run)
    return {"status": "started", "message": f"BODACC lancé (since={since}). Voir /api/admin/bronze-stats"}


# =============================================================================
# INPI RNE
# =============================================================================

@router.get("/load-rne")
async def load_rne(
    background_tasks: BackgroundTasks,
    secret: str = Query(default=""),
    n: int = Query(default=500, ge=50, le=2000),
):
    """Enrichit Silver avec INPI RNE (dirigeants + capital). Requiert INPI_USER + INPI_PASSWORD."""
    _check_secret(secret)

    async def _run():
        import bronze_pipeline as bp
        import financials_pipeline as fp
        bp._PIPELINE_STATUS.update({
            "running": True, "step": "rne_setup", "error": None,
            "started_at": datetime.utcnow().isoformat(), "finished_at": None,
        })
        try:
            fp.setup_rne_table()
            bp._PIPELINE_STATUS["step"] = "rne_load"
            rows_in = await fp.load_rne_batch(top_n=n)
            bp._PIPELINE_STATUS["step"] = "rne_enrich"
            rows_en = await asyncio.to_thread(fp.enrich_silver_rne)
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "done",
                "rows_loaded": rows_in,
                "finished_at": datetime.utcnow().isoformat(),
            })
            print(f"[ADMIN] RNE terminé — {rows_in} insérés, {rows_en} enrichis.")
        except Exception as e:
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "error",
                "error": str(e), "finished_at": datetime.utcnow().isoformat(),
            })
            print(f"[ADMIN] Erreur load-rne: {e}")

    background_tasks.add_task(_run)
    return {"status": "started", "message": f"INPI RNE lancé (top_n={n}). Voir /api/admin/bronze-stats"}


# =============================================================================
# Contact (site web, téléphone, LinkedIn)
# =============================================================================

@router.get("/load-contact")
async def load_contact(
    background_tasks: BackgroundTasks,
    secret: str = Query(default=""),
    n: int = Query(default=3000, ge=100, le=10000),
):
    """
    Enrichit les top-n Silver avec site_web, téléphone, adresse, LinkedIn URL.
    Source : recherche-entreprises.api.gouv.fr (gratuit, sans clé, ~17 req/s).
    Durée estimée : ~3-10 min pour 3000 entreprises.
    """
    _check_secret(secret)

    async def _run():
        import bronze_pipeline as bp
        import contact_pipeline as cp
        bp._PIPELINE_STATUS.update({
            "running": True, "step": "contact_enrich", "error": None,
            "started_at": datetime.utcnow().isoformat(), "finished_at": None,
        })
        try:
            cp.setup_contact_columns()
            updated = await cp.enrich_contact_batch(top_n=n)
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "done",
                "rows_loaded": updated,
                "finished_at": datetime.utcnow().isoformat(),
            })
            print(f"[ADMIN] Contact terminé — {updated} fiches enrichies.")
        except Exception as e:
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "error",
                "error": str(e), "finished_at": datetime.utcnow().isoformat(),
            })
            print(f"[ADMIN] Erreur load-contact: {e}")

    background_tasks.add_task(_run)
    return {"status": "started", "message": f"Enrichissement contact lancé (top_n={n}). Voir /api/admin/bronze-stats"}


# =============================================================================
# Pappers data.gouv.fr
# =============================================================================

@router.get("/load-pappers")
async def load_pappers(
    background_tasks: BackgroundTasks,
    secret: str = Query(default=""),
):
    """Charge le dataset Pappers open data (data.gouv.fr) + enrichit Silver."""
    _check_secret(secret)

    async def _run():
        import bronze_pipeline as bp
        bp._PIPELINE_STATUS.update({
            "running": True, "step": "pappers_load", "error": None,
            "started_at": datetime.utcnow().isoformat(), "finished_at": None,
        })
        try:
            bp.setup_tables()
            await asyncio.to_thread(bp.load_pappers_bronze)
            bp._PIPELINE_STATUS["step"] = "pappers_enrich"
            await asyncio.to_thread(bp.enrich_silver_pappers)
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "done",
                "finished_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "error",
                "error": str(e), "finished_at": datetime.utcnow().isoformat(),
            })
            print(f"[ADMIN] Erreur load-pappers: {e}")

    background_tasks.add_task(_run)
    return {"status": "started", "message": "Pappers data.gouv.fr lancé. Voir /api/admin/bronze-stats"}


# =============================================================================
# Pipeline overnight complet
# =============================================================================

@router.get("/run-all")
async def run_all(
    background_tasks: BackgroundTasks,
    secret: str = Query(default=""),
    since_bodacc: str = Query(default="2023-01-01"),
    rne_n: int = Query(default=500, ge=100, le=2000),
    skip_bronze: bool = Query(default=False, description="Saute le reload SIRENE si déjà chargé"),
):
    """
    Pipeline overnight complet (30-90 min) :
    1. Bronze SIRENE + Silver
    2. BODACC DILA (archives annuelles) + flag Silver
    3. INPI RNE enrichissement top-rne_n
    4. Pappers data.gouv.fr + enrich Silver
    5. Sync top-5000 Silver → Supabase
    """
    _check_secret(secret)

    async def _run():
        import bronze_pipeline as bp
        import financials_pipeline as fp

        bp._PIPELINE_STATUS.update({
            "running": True, "step": "setup", "error": None,
            "started_at": datetime.utcnow().isoformat(), "finished_at": None,
        })
        try:
            bp.setup_tables()
            fp.setup_rne_table()

            if not skip_bronze:
                bp._PIPELINE_STATUS["step"] = "bronze_load"
                print("[ADMIN] run-all étape 2 — bronze load…")
                await asyncio.to_thread(bp.load_bronze)

                bp._PIPELINE_STATUS["step"] = "silver_build"
                print("[ADMIN] run-all étape 3 — silver build…")
                await asyncio.to_thread(bp.build_silver)

                bp._PIPELINE_STATUS["step"] = "gold_build"
                print("[ADMIN] run-all étape 3b — gold build (M&A scoring)…")
                await asyncio.to_thread(bp.build_gold)
            else:
                print("[ADMIN] run-all — bronze/silver/gold skippés (skip_bronze=true)")

            bp._PIPELINE_STATUS["step"] = "bodacc_load"
            print(f"[ADMIN] run-all étape 4 — BODACC DILA (since={since_bodacc})…")
            await asyncio.to_thread(bp.load_bodacc, since_bodacc)

            bp._PIPELINE_STATUS["step"] = "bodacc_flag"
            print("[ADMIN] run-all étape 5 — flag BODACC Silver…")
            await asyncio.to_thread(bp.flag_bodacc_silver)

            bp._PIPELINE_STATUS["step"] = "rne_load"
            print(f"[ADMIN] run-all étape 6 — INPI RNE (top_n={rne_n})…")
            await fp.load_rne_batch(top_n=rne_n)
            bp._PIPELINE_STATUS["step"] = "rne_enrich"
            await asyncio.to_thread(fp.enrich_silver_rne)

            bp._PIPELINE_STATUS["step"] = "pappers_load"
            print("[ADMIN] run-all étape 7 — Pappers/financier…")
            await asyncio.to_thread(bp.load_pappers_bronze)
            await asyncio.to_thread(bp.enrich_silver_pappers)

            bp._PIPELINE_STATUS["step"] = "contact_enrich"
            print("[ADMIN] run-all étape 8 — Contact (site web, téléphone, LinkedIn)…")
            import contact_pipeline as cp
            cp.setup_contact_columns()
            await cp.enrich_contact_batch(top_n=3000)

            bp._PIPELINE_STATUS["step"] = "sync_supabase"
            print("[ADMIN] run-all étape 8 — sync Silver → Supabase…")
            await bp.sync_silver_to_supabase(top_n=5000, priority="bodacc")

            bp._PIPELINE_STATUS.update({
                "running": False, "step": "done",
                "finished_at": datetime.utcnow().isoformat(),
            })
            print("[ADMIN] run-all : pipeline overnight terminé.")

        except Exception as e:
            bp._PIPELINE_STATUS.update({
                "running": False, "step": "error",
                "error": str(e), "finished_at": datetime.utcnow().isoformat(),
            })
            print(f"[ADMIN] Erreur run-all: {e}")

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "message": (
            f"Pipeline overnight lancé (since_bodacc={since_bodacc}, rne_n={rne_n}, "
            f"skip_bronze={skip_bronze}). Voir /api/admin/bronze-stats"
        ),
    }


# =============================================================================
# Migration Supabase (DDL via connexion PostgreSQL directe)
# =============================================================================

@router.get("/migrate-supabase")
async def migrate_supabase(secret: str = Query(default="")):
    """
    Exécute la migration 001 sur la base Supabase (ADD COLUMN IF NOT EXISTS).
    Nécessite DATABASE_URL dans les variables d'environnement Render.
    """
    _check_secret(secret)

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise HTTPException(400, "DATABASE_URL non configuré — ajoutez-le dans Render > Environment")

    migration_file = Path(__file__).parent.parent / "migrations" / "001_sirene_index_enrich.sql"
    sql = migration_file.read_text(encoding="utf-8")
    # Filtre les commentaires et lignes vides
    statements = [
        s.strip() for s in sql.split(";")
        if s.strip() and not s.strip().startswith("--")
    ]

    try:
        import psycopg2
    except ImportError:
        raise HTTPException(500, "psycopg2 non installé — redéployez Render")

    results = []
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()
        for stmt in statements:
            if not stmt:
                continue
            try:
                cur.execute(stmt)
                results.append({"sql": stmt[:80] + "…", "status": "ok"})
            except Exception as e:
                results.append({"sql": stmt[:80] + "…", "status": "error", "detail": str(e)})
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(500, f"Connexion PostgreSQL échouée : {e}")

    errors = [r for r in results if r["status"] == "error"]
    return {
        "status": "done" if not errors else "partial",
        "statements_run": len(results),
        "errors": errors,
        "results": results,
    }
