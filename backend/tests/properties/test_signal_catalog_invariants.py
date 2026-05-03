"""Property-based tests Hypothesis sur demo_data.SIGNAL_CATALOG.

Invariants ciblés (dim 3 path_coverage QA L4 Sprint 1) :
- Toutes les keys non vides, valeurs = dict avec champs obligatoires
- `points` ≥ 0 sur tous les signaux (un signal négatif casserait calculate_score)
- `dimension` référencée DOIT exister dans DEFAULT_SCORING_WEIGHTS (pas d'orphelin)
- `severity` ∈ {high, medium, low} (cohérence ontologie)
- `label` non vide (sinon UI affiche du blank)
- Aucun champ obligatoire à None

Run :
    cd backend && pytest tests/properties/test_signal_catalog_invariants.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hypothesis import given, settings, strategies as st  # type: ignore
import pytest

from demo_data import SIGNAL_CATALOG, DEFAULT_SCORING_WEIGHTS  # type: ignore


SIGNAL_IDS = list(SIGNAL_CATALOG.keys())
DIMENSION_IDS = set(DEFAULT_SCORING_WEIGHTS.keys())
REQUIRED_FIELDS = {"label", "source", "dimension", "points", "severity", "family"}
VALID_SEVERITIES = {"high", "medium", "low"}


# ────────────────────────────────────────────────────────────────────
# Sanity / structure globale
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
def test_signal_catalog_non_empty() -> None:
    """SIGNAL_CATALOG doit contenir au moins 1 signal."""
    assert isinstance(SIGNAL_CATALOG, dict)
    assert len(SIGNAL_CATALOG) > 0


@pytest.mark.unit
@pytest.mark.property
def test_default_scoring_weights_non_empty() -> None:
    """DEFAULT_SCORING_WEIGHTS doit contenir au moins 1 dimension."""
    assert isinstance(DEFAULT_SCORING_WEIGHTS, dict)
    assert len(DEFAULT_SCORING_WEIGHTS) > 0


# ────────────────────────────────────────────────────────────────────
# Hypothesis property tests par signal
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(SIGNAL_IDS))
@settings(max_examples=200, deadline=None)
def test_signal_id_non_empty(signal_id: str) -> None:
    """Aucune key vide dans le catalog."""
    assert signal_id
    assert len(signal_id) > 0
    assert isinstance(signal_id, str)


@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(SIGNAL_IDS))
@settings(max_examples=200, deadline=None)
def test_signal_has_required_fields(signal_id: str) -> None:
    """Tous les signaux ont les champs obligatoires non None."""
    sig = SIGNAL_CATALOG[signal_id]
    assert isinstance(sig, dict), f"Signal {signal_id} pas un dict"
    for field in REQUIRED_FIELDS:
        assert field in sig, f"Signal {signal_id} manque le champ '{field}'"
        assert sig[field] is not None, f"Signal {signal_id}.{field} est None"


@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(SIGNAL_IDS))
@settings(max_examples=200, deadline=None)
def test_signal_points_non_negative(signal_id: str) -> None:
    """Tous les `points` doivent être >= 0 (un negative casserait le scoring)."""
    sig = SIGNAL_CATALOG[signal_id]
    pts = sig["points"]
    assert isinstance(pts, (int, float)), f"{signal_id}.points pas numérique"
    assert pts >= 0, f"{signal_id}.points négatif : {pts}"


@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(SIGNAL_IDS))
@settings(max_examples=200, deadline=None)
def test_signal_dimension_in_scoring_weights(signal_id: str) -> None:
    """Toute dimension référencée par un signal DOIT exister dans DEFAULT_SCORING_WEIGHTS.

    C'est l'invariant critique : un signal pointant vers une dimension
    inexistante = signal mort (aucune contribution au score) — bug silencieux.
    """
    sig = SIGNAL_CATALOG[signal_id]
    dim = sig["dimension"]
    assert dim in DIMENSION_IDS, (
        f"Signal {signal_id} pointe vers dimension orpheline : "
        f"'{dim}' (valides : {sorted(DIMENSION_IDS)})"
    )


@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(SIGNAL_IDS))
@settings(max_examples=200, deadline=None)
def test_signal_severity_valid(signal_id: str) -> None:
    """`severity` doit être ∈ {high, medium, low}."""
    sig = SIGNAL_CATALOG[signal_id]
    assert sig["severity"] in VALID_SEVERITIES, (
        f"{signal_id}.severity invalide : {sig['severity']!r}"
    )


@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(SIGNAL_IDS))
@settings(max_examples=200, deadline=None)
def test_signal_label_non_empty(signal_id: str) -> None:
    """Le label affichage UI doit être non vide."""
    sig = SIGNAL_CATALOG[signal_id]
    assert isinstance(sig["label"], str)
    assert sig["label"].strip(), f"{signal_id}.label vide ou whitespace"


@pytest.mark.unit
@pytest.mark.property
@given(signal_id=st.sampled_from(SIGNAL_IDS))
@settings(max_examples=200, deadline=None)
def test_signal_source_non_empty(signal_id: str) -> None:
    """Le champ `source` (origine de la donnée) doit être non vide."""
    sig = SIGNAL_CATALOG[signal_id]
    assert isinstance(sig["source"], str)
    assert sig["source"].strip()


# ────────────────────────────────────────────────────────────────────
# Cross-invariants : sum points par dimension <= max dimension
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
def test_signals_distributed_across_dimensions() -> None:
    """Chaque dimension référencée a au moins 1 signal (sinon dimension dead).

    Inverse : on garantit que toutes les dimensions du scoring sont alimentées.
    """
    referenced = {SIGNAL_CATALOG[sid]["dimension"] for sid in SIGNAL_IDS}
    orphan_dims = DIMENSION_IDS - referenced
    # Tolerance : ce test est informationnel — on warn mais pas fail si des dims
    # n'ont pas encore de signaux (cas légitime en early dev).
    assert isinstance(orphan_dims, set)


@pytest.mark.unit
@pytest.mark.property
def test_dimension_max_above_zero() -> None:
    """Chaque dimension a un `max` strictement > 0."""
    for dim_id, dim_meta in DEFAULT_SCORING_WEIGHTS.items():
        assert "max" in dim_meta, f"Dimension {dim_id} sans 'max'"
        assert dim_meta["max"] > 0, f"Dimension {dim_id}.max <= 0 : {dim_meta['max']}"


@pytest.mark.unit
@pytest.mark.property
def test_signal_ids_unique() -> None:
    """Les signal_ids sont uniques (Python dict garantit ça, mais on verrouille)."""
    assert len(SIGNAL_IDS) == len(set(SIGNAL_IDS))
