"""Property-based tests Hypothesis sur backend/demo_data.py — Sprint QA-L4.6.

demo_data.py est déjà 100% couvert mais on étend les INVARIANTS structurels :
- DEFAULT_SCORING_WEIGHTS : sum(max) constante connue, weights summent à 100
- Modifier les poids → score recalculé reste cohérent
- Sérialisation JSON round-trip stable
- SIGNAL_CATALOG : tous les signaux pointent vers une dimension valide

~600 inputs aléatoires.

Run :
    cd backend && pytest tests/properties/test_demo_data_extra_invariants.py -v
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from hypothesis import given, settings, strategies as st  # type: ignore

demo_data = pytest.importorskip("demo_data")
DEFAULT_SCORING_WEIGHTS = demo_data.DEFAULT_SCORING_WEIGHTS
SIGNAL_CATALOG = demo_data.SIGNAL_CATALOG
SECTORS_HEAT = demo_data.SECTORS_HEAT


# Constantes attendues — issues de l'analyse statique
EXPECTED_MAX_TOTAL = 125          # 30+30+25+25+15
EXPECTED_WEIGHTS_TOTAL = 100      # 25+25+20+20+10
EXPECTED_NB_DIMENSIONS = 5
EXPECTED_NB_SIGNALS = 18
EXPECTED_NB_SECTORS = 8


# ────────────────────────────────────────────────────────────────────
# 1. Invariants structurels constants
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
def test_scoring_weights_sum_max_equals_constant() -> None:
    """∑(max) sur DEFAULT_SCORING_WEIGHTS == 125 (invariant produit)."""
    total_max = sum(d["max"] for d in DEFAULT_SCORING_WEIGHTS.values())
    assert total_max == EXPECTED_MAX_TOTAL


@pytest.mark.unit
@pytest.mark.property
def test_scoring_weights_sum_weight_equals_100() -> None:
    """∑(weight) sur DEFAULT_SCORING_WEIGHTS == 100 (pondération relative)."""
    total_w = sum(d["weight"] for d in DEFAULT_SCORING_WEIGHTS.values())
    assert total_w == EXPECTED_WEIGHTS_TOTAL


@pytest.mark.unit
@pytest.mark.property
def test_scoring_weights_count_dimensions() -> None:
    """5 dimensions exactement."""
    assert len(DEFAULT_SCORING_WEIGHTS) == EXPECTED_NB_DIMENSIONS


@pytest.mark.unit
@pytest.mark.property
def test_scoring_weights_each_max_geq_weight() -> None:
    """Pour chaque dimension : max >= weight (toujours vrai sinon score plafonné < pondération)."""
    for dim, payload in DEFAULT_SCORING_WEIGHTS.items():
        assert payload["max"] >= payload["weight"], f"{dim} max<weight"


# ────────────────────────────────────────────────────────────────────
# 2. Modifier les poids → cohérence préservée
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@given(
    new_weights=st.lists(
        st.integers(min_value=0, max_value=100),
        min_size=EXPECTED_NB_DIMENSIONS,
        max_size=EXPECTED_NB_DIMENSIONS,
    )
)
@settings(max_examples=200, deadline=None)
def test_modified_weights_recompute_max_total(new_weights: list) -> None:
    """En changeant tous les "max" par un nouveau set, la somme suit."""
    cfg = copy.deepcopy(DEFAULT_SCORING_WEIGHTS)
    for (dim, _), m in zip(cfg.items(), new_weights):
        cfg[dim]["max"] = m
    total = sum(d["max"] for d in cfg.values())
    assert total == sum(new_weights)


@pytest.mark.unit
@pytest.mark.property
@given(
    factor=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=100, deadline=None)
def test_scaled_weights_proportional(factor: int) -> None:
    """Multiplier tous les weights par k → total = k * 100."""
    cfg = copy.deepcopy(DEFAULT_SCORING_WEIGHTS)
    for d in cfg.values():
        d["weight"] *= factor
    total_w = sum(d["weight"] for d in cfg.values())
    assert total_w == EXPECTED_WEIGHTS_TOTAL * factor


# ────────────────────────────────────────────────────────────────────
# 3. JSON round-trip
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
def test_default_scoring_weights_json_round_trip() -> None:
    """JSON-serializable et round-trip identique."""
    encoded = json.dumps(DEFAULT_SCORING_WEIGHTS, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded == DEFAULT_SCORING_WEIGHTS


@pytest.mark.unit
@pytest.mark.property
def test_signal_catalog_json_round_trip() -> None:
    """SIGNAL_CATALOG entièrement JSON-serializable."""
    encoded = json.dumps(SIGNAL_CATALOG, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded == SIGNAL_CATALOG


@pytest.mark.unit
@pytest.mark.property
def test_sectors_heat_json_round_trip() -> None:
    """SECTORS_HEAT JSON-serializable."""
    encoded = json.dumps(SECTORS_HEAT, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded == SECTORS_HEAT


# ────────────────────────────────────────────────────────────────────
# 4. Cross-référentiel SIGNAL_CATALOG ↔ DEFAULT_SCORING_WEIGHTS
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(list(SIGNAL_CATALOG.keys())))
@settings(max_examples=100, deadline=None)
def test_signal_dimension_in_scoring_config(signal_id: str) -> None:
    """Chaque signal pointe vers une dimension valide de DEFAULT_SCORING_WEIGHTS."""
    sig = SIGNAL_CATALOG[signal_id]
    assert sig["dimension"] in DEFAULT_SCORING_WEIGHTS, \
        f"{signal_id} pointe vers dimension inexistante"


@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(list(SIGNAL_CATALOG.keys())))
@settings(max_examples=100, deadline=None)
def test_signal_severity_in_known_set(signal_id: str) -> None:
    """severity ∈ {high, medium, low}."""
    severity = SIGNAL_CATALOG[signal_id].get("severity")
    assert severity in {"high", "medium", "low"}, f"{signal_id} severity={severity}"


@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(list(SIGNAL_CATALOG.keys())))
@settings(max_examples=100, deadline=None)
def test_signal_points_positive_int(signal_id: str) -> None:
    """points est un int strictement positif."""
    pts = SIGNAL_CATALOG[signal_id].get("points")
    assert isinstance(pts, int)
    assert 0 < pts <= 100


# ────────────────────────────────────────────────────────────────────
# 5. SECTORS_HEAT invariants
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@given(sector=st.sampled_from(list(SECTORS_HEAT.keys())))
@settings(max_examples=50, deadline=None)
def test_sectors_heat_in_range(sector: str) -> None:
    """heat ∈ [0, 100] pour chaque secteur."""
    heat = SECTORS_HEAT[sector].get("heat")
    assert isinstance(heat, int)
    assert 0 <= heat <= 100


@pytest.mark.unit
@pytest.mark.property
def test_sectors_heat_count() -> None:
    """8 secteurs exactement."""
    assert len(SECTORS_HEAT) == EXPECTED_NB_SECTORS
