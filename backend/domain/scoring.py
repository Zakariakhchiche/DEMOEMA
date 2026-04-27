"""Domain scoring — règles métier EdRCF.

Extrait de `main.py` (audit ARCH-5). Pure logique : pas de FastAPI, pas
d'I/O. Testable isolément. Les seuils business 65/45/25 sont des constantes
nommées (audit QA-8) plutôt que magic numbers.
"""
from __future__ import annotations

import copy
from typing import Any

# Catalog importé depuis demo_data conservé temporairement (la PR-2 le
# re-localisera dans `domain/scoring_config.py`).
from demo_data import DEFAULT_SCORING_WEIGHTS, SIGNAL_CATALOG

# Seuils priorité — extraits de main.py:72-79 et test_scoring.py:77 où
# ils étaient dupliqués (audit QA-8). Une seule source de vérité.
SCORE_THRESHOLD_PRIORITAIRE = 65    # >= → "Action Prioritaire"
SCORE_THRESHOLD_QUALIFICATION = 45   # >= → "Qualification"
SCORE_THRESHOLD_MONITORING = 25      # >= → "Monitoring", < → "Veille Passive"

# Singleton runtime-mutable (POST /api/scoring/config peut le modifier).
# Le snapshot des poids par défaut reste accessible pour reset.
scoring_config: dict[str, Any] = copy.deepcopy(DEFAULT_SCORING_WEIGHTS)


def calculate_score(
    company: dict[str, Any],
    weights: dict[str, Any] | None = None,
) -> tuple[float, str, dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Calcule le score d'une cible à partir de ses signaux actifs.

    Returns:
        (total, priority_label, scored_dimensions, signals_detail)
    """
    if weights is None:
        weights = scoring_config
    dimensions: dict[str, int] = {k: 0 for k in weights}
    signals_detail: list[dict[str, Any]] = []
    for sig_id in company.get("active_signals", []):
        sig = SIGNAL_CATALOG.get(sig_id)
        if sig:
            dimensions[sig["dimension"]] += sig["points"]
            signals_detail.append({**sig, "id": sig_id})

    scored: dict[str, dict[str, Any]] = {}
    total = 0
    for dim, raw in dimensions.items():
        mx = weights[dim]["max"]
        capped = min(raw, mx)
        scored[dim] = {
            "score": capped,
            "raw": raw,
            "max": mx,
            "label": weights[dim]["label"],
        }
        total += capped

    if total >= SCORE_THRESHOLD_PRIORITAIRE:
        priority = "Action Prioritaire"
    elif total >= SCORE_THRESHOLD_QUALIFICATION:
        priority = "Qualification"
    elif total >= SCORE_THRESHOLD_MONITORING:
        priority = "Monitoring"
    else:
        priority = "Veille Passive"

    return round(total, 1), priority, scored, signals_detail


def enrich_target(company: dict[str, Any]) -> dict[str, Any]:
    """Applique le scoring et retourne le dict cible enrichi."""
    score, priority, scored_dims, signals = calculate_score(company)
    return {
        **company,
        "globalScore": score,
        "priorityLevel": priority,
        "scoring_details": scored_dims,
        "topSignals": signals,
    }
