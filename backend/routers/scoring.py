"""Routes scoring config — extraites de main.py:1216-1234.

GET retourne la config courante, POST permet de la muter (audit SEC-5 :
endpoint actuellement non authentifié — à protéger une fois qu'on aura
ajouté un middleware d'auth applicative).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from domain.scoring import enrich_target, scoring_config

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


@router.get("/config")
def get_scoring_config():
    return {"data": scoring_config}


@router.post("/config")
def update_scoring_config(config: dict[str, Any]):
    """Met à jour la config scoring runtime + recalcule les targets enrichies.

    Audit SEC-5 (HIGH) : endpoint non-authentifié + payload Dict[str, Any]
    accepté tel quel. À protéger / valider via Pydantic dans une PR future.
    """
    import main  # lazy import (cycle main↔router)
    for key, val in config.items():
        if key in scoring_config:
            scoring_config[key].update(val)
    main.enriched_targets[:] = [enrich_target(c) for c in main.raw_targets]
    return {"data": scoring_config, "n_targets_rescored": len(main.enriched_targets)}
