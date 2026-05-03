"""Property-based tests Hypothesis sur scoring M&A — Sprint QA-1.5.

Cible dim 3 path_coverage du QCS skill qa-audit. Hypothesis génère
1000+ inputs aléatoires pour valider invariants critiques :
- 0 ≤ score ≤ MAX_TOTAL (somme des max dimensions)
- priority cohérent avec total (monotone)
- enrich_target préserve les clés input
- Aucun crash sur signaux invalides ou dimensions absentes

Run :
    cd backend && pytest tests/properties/ -v
    cd backend && pytest tests/properties/ -v --hypothesis-show-statistics
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hypothesis import given, settings, strategies as st  # type: ignore
import pytest

from domain.scoring import (  # type: ignore
    SCORE_THRESHOLD_PRIORITAIRE,
    SCORE_THRESHOLD_QUALIFICATION,
    SCORE_THRESHOLD_MONITORING,
    calculate_score,
    enrich_target,
    scoring_config,
)
from demo_data import SIGNAL_CATALOG  # type: ignore


# Pool des signal_ids existants (anti-hallucination Hypothesis)
VALID_SIGNAL_IDS = list(SIGNAL_CATALOG.keys())
MAX_TOTAL = sum(d["max"] for d in scoring_config.values())


# ────────────────────────────────────────────────────────────────────
# Stratégies Hypothesis
# ────────────────────────────────────────────────────────────────────
def signals_strategy():
    """Génère listes de signal_ids valides (taille 0-20)."""
    if not VALID_SIGNAL_IDS:
        return st.just([])
    return st.lists(st.sampled_from(VALID_SIGNAL_IDS), min_size=0, max_size=20)


def company_strategy():
    """Génère un dict cible avec active_signals + autres champs random."""
    return st.fixed_dictionaries(
        {
            "siren": st.text(alphabet="0123456789", min_size=9, max_size=9),
            "name": st.text(min_size=0, max_size=80),
            "active_signals": signals_strategy(),
        },
        optional={
            "ca": st.floats(min_value=0, max_value=1e10, allow_nan=False, allow_infinity=False),
            "effectif": st.integers(min_value=0, max_value=100_000),
            "naf": st.text(alphabet="0123456789ABCDEFGHIJZ", min_size=4, max_size=5),
        },
    )


# ────────────────────────────────────────────────────────────────────
# Invariants calculate_score
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@given(company=company_strategy())
@settings(max_examples=300, deadline=None)
def test_score_in_valid_range(company: dict) -> None:
    """Le score total doit toujours être dans [0, MAX_TOTAL]."""
    total, priority, scored, signals = calculate_score(company)
    assert 0 <= total <= MAX_TOTAL, f"Score hors range : {total} (max {MAX_TOTAL})"


@pytest.mark.unit
@given(company=company_strategy())
@settings(max_examples=300, deadline=None)
def test_priority_consistent_with_total(company: dict) -> None:
    """priority doit être cohérent avec les seuils."""
    total, priority, _, _ = calculate_score(company)
    if total >= SCORE_THRESHOLD_PRIORITAIRE:
        assert priority == "Action Prioritaire"
    elif total >= SCORE_THRESHOLD_QUALIFICATION:
        assert priority == "Qualification"
    elif total >= SCORE_THRESHOLD_MONITORING:
        assert priority == "Monitoring"
    else:
        assert priority == "Veille Passive"


@pytest.mark.unit
@given(company=company_strategy())
@settings(max_examples=300, deadline=None)
def test_score_monotone_with_signal_count(company: dict) -> None:
    """Ajouter des signaux ne doit JAMAIS faire baisser le score (monotone)."""
    total_base, _, _, _ = calculate_score(company)
    if not VALID_SIGNAL_IDS:
        return
    enriched = {**company, "active_signals": company["active_signals"] + [VALID_SIGNAL_IDS[0]]}
    total_enriched, _, _, _ = calculate_score(enriched)
    assert total_enriched >= total_base, (
        f"Non-monotone: ajout signal a fait baisser score "
        f"({total_base} -> {total_enriched})"
    )


@pytest.mark.unit
@given(company=company_strategy())
@settings(max_examples=200, deadline=None)
def test_scored_dimensions_capped_at_max(company: dict) -> None:
    """Chaque dimension scored doit être cappée à son max (overflow protection)."""
    _, _, scored, _ = calculate_score(company)
    for dim_name, dim_data in scored.items():
        assert dim_data["score"] <= dim_data["max"], (
            f"Dimension {dim_name} dépasse max : {dim_data['score']} > {dim_data['max']}"
        )
        assert dim_data["score"] >= 0, f"Dimension {dim_name} négative : {dim_data['score']}"


@pytest.mark.unit
@given(company=company_strategy())
@settings(max_examples=200, deadline=None)
def test_signals_detail_subset_of_input(company: dict) -> None:
    """signals_detail ne doit contenir que des signaux présents en input."""
    _, _, _, signals = calculate_score(company)
    input_ids = set(company["active_signals"])
    for sig in signals:
        assert sig["id"] in input_ids, f"Signal hallucination : {sig['id']} pas en input"


# ────────────────────────────────────────────────────────────────────
# Invariants enrich_target
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@given(company=company_strategy())
@settings(max_examples=200, deadline=None)
def test_enrich_target_preserves_input_keys(company: dict) -> None:
    """enrich_target doit préserver TOUTES les clés input + ajouter les enrichies."""
    enriched = enrich_target(company)
    for k, v in company.items():
        assert k in enriched, f"Clé '{k}' perdue dans enrichissement"
        assert enriched[k] == v, f"Valeur '{k}' modifiée par enrichissement"
    # Et 4 clés supplémentaires
    for added in ("globalScore", "priorityLevel", "scoring_details", "topSignals"):
        assert added in enriched, f"Clé enrichie '{added}' manquante"


@pytest.mark.unit
@given(company=company_strategy())
@settings(max_examples=200, deadline=None)
def test_enrich_target_idempotent(company: dict) -> None:
    """enrich_target(enrich_target(x)) == enrich_target(x) (idempotence)."""
    enriched_once = enrich_target(company)
    enriched_twice = enrich_target(enriched_once)
    # Le score reste le même (les active_signals ne changent pas)
    assert enriched_twice["globalScore"] == enriched_once["globalScore"]
    assert enriched_twice["priorityLevel"] == enriched_once["priorityLevel"]


# ────────────────────────────────────────────────────────────────────
# Edge cases / robustesse
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
def test_calculate_score_empty_signals() -> None:
    """Cible sans signaux → score=0, priority="Veille Passive"."""
    company = {"siren": "000000000", "active_signals": []}
    total, priority, scored, signals = calculate_score(company)
    assert total == 0
    assert priority == "Veille Passive"
    assert signals == []
    # Toutes les dimensions = 0
    for dim in scored.values():
        assert dim["score"] == 0
        assert dim["raw"] == 0


@pytest.mark.unit
@given(invalid_id=st.text(min_size=1, max_size=50).filter(lambda x: x not in VALID_SIGNAL_IDS))
@settings(max_examples=100, deadline=None)
def test_calculate_score_ignores_invalid_signal_ids(invalid_id: str) -> None:
    """Signaux inexistants dans le catalog doivent être ignorés silencieusement."""
    company = {"siren": "000000000", "active_signals": [invalid_id]}
    total, _, _, signals = calculate_score(company)
    # Score = 0 car signal invalide, pas de signal dans signals_detail
    assert total == 0
    assert signals == []


@pytest.mark.unit
@given(
    multiplier=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=50, deadline=None)
def test_score_capped_even_with_repeated_signals(multiplier: int) -> None:
    """Répéter le même signal N fois ne dépasse pas le max de la dimension."""
    if not VALID_SIGNAL_IDS:
        return
    sig_id = VALID_SIGNAL_IDS[0]
    company = {"siren": "000000000", "active_signals": [sig_id] * multiplier}
    total, _, scored, _ = calculate_score(company)
    # Chaque dimension reste capée
    for dim_name, dim_data in scored.items():
        assert dim_data["score"] <= dim_data["max"], (
            f"Dim {dim_name} dépasse max avec {multiplier} signaux : "
            f"{dim_data['score']} > {dim_data['max']}"
        )
