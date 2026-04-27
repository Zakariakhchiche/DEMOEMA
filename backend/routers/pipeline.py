"""Routes pipeline M&A — extraites de main.py:1175-1213.

Les seuils 65/45 sont importés depuis domain.scoring (audit QA-8 : single
source of truth, plus de duplication entre route et tests).
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from domain.scoring import (
    SCORE_THRESHOLD_PRIORITAIRE,
    SCORE_THRESHOLD_QUALIFICATION,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("")
def get_pipeline():
    """5 M&A stages pipeline, peuplé depuis enriched_targets selon score."""
    import main  # lazy import
    pipeline = [
        {"id": "origination", "title": "Origination", "color": "indigo", "cards": []},
        {"id": "qualification", "title": "Qualification", "color": "purple", "cards": []},
        {"id": "pitch", "title": "Pitch", "color": "amber", "cards": []},
        {"id": "execution", "title": "Execution", "color": "emerald", "cards": []},
        {"id": "closing", "title": "Closing", "color": "green", "cards": []},
    ]
    for t in main.enriched_targets:
        card = {
            "id": t["id"],
            "name": t["name"],
            "sector": t["sector"],
            "score": t["globalScore"],
            "priority": t["priorityLevel"],
            "tags": [t["analysis"]["type"]],
            "window": t["analysis"]["window"],
            "ebitda": t["financials"]["ebitda"],
        }
        if t["globalScore"] >= SCORE_THRESHOLD_PRIORITAIRE:
            pipeline[1]["cards"].append(card)  # Qualification (already scored high)
        elif t["globalScore"] >= SCORE_THRESHOLD_QUALIFICATION:
            pipeline[0]["cards"].append(card)  # Origination
    return {"data": pipeline}


@router.post("/move")
def move_pipeline_card(
    card_id: str = Query(...),
    from_stage: str = Query(...),
    to_stage: str = Query(...),
):
    """Stub : pour l'instant, retourne juste le success message côté UI."""
    return {
        "success": True,
        "message": f"Carte {card_id} deplacee de {from_stage} vers {to_stage}",
    }
