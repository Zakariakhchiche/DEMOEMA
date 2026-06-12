"""Maintenance one-shot — rebuild cascade de silver.inpi_comptes.

Contexte : le fix d'extraction du passif (codes DL/DR/DU/EE lus en m1 et non m3,
cf. silver_transforms/inpi_comptes.sql) change la définition de silver.inpi_comptes.
Comme c'est une table fondamentale, l'appliquer fait un DROP ... CASCADE qui
emporte ses 8 dépendantes. Ce script les reconstruit dans l'ordre topologique,
SANS LLM :
  - hand_authored (silver_transforms/*.sql) : inpi_comptes, sci_master,
    entreprises_signals, dirigeants_360
  - cache audit (applied=true)              : amf_signals, cnil_sanctions,
    dgccrf_sanctions, sanctions

Tout passe par generate_silver_sql(apply_immediately=True), qui route
automatiquement vers le fichier hand_authored ou le SQL en cache.

Usage (depuis le container agents-platform, cwd=/app) :
    docker exec -d -w /app demomea-agents-platform python cascade_rebuild.py
Progression : /app/cascade_status.log
"""
from __future__ import annotations

import asyncio
import datetime
import sys

# Permet de lancer le script sans `-w /app` (cwd quelconque) : on garantit que
# le package `ingestion` est importable.
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

from ingestion.silver_codegen import generate_silver_sql

LOG = "/app/cascade_status.log"

# Ordre topologique : inpi_comptes (L0) d'abord — son apply DROP CASCADE les 8 —
# puis les dépendantes directes (L1), puis sanctions (L2).
REBUILD_ORDER = [
    "silver.inpi_comptes",
    "silver.sci_master",
    "silver.entreprises_signals",
    "silver.dirigeants_360",
    "silver.amf_signals",
    "silver.cnil_sanctions",
    "silver.dgccrf_sanctions",
    "silver.sanctions",
]


def log(message: str) -> None:
    line = f"{datetime.datetime.now().isoformat()} {message}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


async def build(name: str) -> bool:
    try:
        r = await generate_silver_sql(name, apply_immediately=True)
        log(f"{name} source={r.get('source')} applied={r.get('applied')} "
            f"err={str(r.get('error'))[:150]}")
        return bool(r.get("applied"))
    except Exception as e:  # noqa: BLE001 — on loggue et on continue
        log(f"{name} EXC {type(e).__name__}: {str(e)[:150]}")
        return False


async def main() -> None:
    log("START cascade rebuild inpi_comptes")
    for name in REBUILD_ORDER:
        await build(name)
    log("DONE cascade rebuild")


if __name__ == "__main__":
    asyncio.run(main())
