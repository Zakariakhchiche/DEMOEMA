"""Property-based tests Hypothesis sur validators — Sprint QA-1.6.

Cible : étendre dim 3 path_coverage en couvrant validate_siren via
Hypothesis. ~500 inputs aléatoires (valides + invalides + edge cases).

Run :
    cd backend && pytest tests/properties/test_validators_invariants.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hypothesis import given, settings, strategies as st  # type: ignore
import pytest
from fastapi import HTTPException  # type: ignore

from domain.validators import validate_siren  # type: ignore


# ────────────────────────────────────────────────────────────────────
# Stratégies Hypothesis
# ────────────────────────────────────────────────────────────────────
def valid_siren_strategy():
    """SIREN valide = 9 chiffres exactement."""
    return st.text(alphabet="0123456789", min_size=9, max_size=9)


def invalid_siren_strategy():
    """SIREN invalide : tout sauf 9 chiffres exacts."""
    return st.one_of(
        st.text(alphabet="0123456789", min_size=0, max_size=8),  # trop court
        st.text(alphabet="0123456789", min_size=10, max_size=20),  # trop long
        st.text(alphabet="abcdefghij", min_size=9, max_size=9),  # lettres
        st.text(alphabet="0123456789!@#", min_size=9, max_size=9).filter(
            lambda s: not s.isdigit()
        ),  # mix
    )


# ────────────────────────────────────────────────────────────────────
# Happy paths
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@given(siren=valid_siren_strategy())
@settings(max_examples=300, deadline=None)
def test_valid_siren_normalized(siren: str) -> None:
    """SIREN valide → retourné inchangé."""
    result = validate_siren(siren)
    assert result == siren
    assert len(result) == 9
    assert result.isdigit()


@pytest.mark.unit
@given(
    siren=valid_siren_strategy(),
    spaces=st.integers(min_value=0, max_value=5),
    dots=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=200, deadline=None)
def test_valid_siren_strips_separators(siren: str, spaces: int, dots: int) -> None:
    """SIREN avec espaces/points → strippé proprement."""
    # Interleave separators
    s_with_sep = " " * spaces + siren[:3] + "." * dots + siren[3:6] + " " * spaces + siren[6:]
    result = validate_siren(s_with_sep)
    assert result == siren
    assert len(result) == 9


@pytest.mark.unit
@given(
    leading_ws=st.text(alphabet=" \t", min_size=0, max_size=10),
    trailing_ws=st.text(alphabet=" \t", min_size=0, max_size=10),
    siren=valid_siren_strategy(),
)
@settings(max_examples=100, deadline=None)
def test_valid_siren_strips_whitespace(leading_ws: str, trailing_ws: str, siren: str) -> None:
    """SIREN entouré de whitespace → strippé."""
    padded = f"{leading_ws}{siren}{trailing_ws}"
    result = validate_siren(padded)
    assert result == siren


# ────────────────────────────────────────────────────────────────────
# Negative paths (raise HTTPException 400)
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.negative
@given(invalid=invalid_siren_strategy())
@settings(max_examples=300, deadline=None)
def test_invalid_siren_raises(invalid: str) -> None:
    """SIREN invalide → HTTPException(400)."""
    with pytest.raises(HTTPException) as exc_info:
        validate_siren(invalid)
    assert exc_info.value.status_code == 400


@pytest.mark.unit
@pytest.mark.negative
def test_empty_siren_raises() -> None:
    """SIREN vide → HTTPException(400) avec message clair."""
    with pytest.raises(HTTPException) as exc_info:
        validate_siren("")
    assert exc_info.value.status_code == 400
    assert "manquant" in str(exc_info.value.detail)


@pytest.mark.unit
@pytest.mark.negative
def test_none_siren_raises() -> None:
    """SIREN None → HTTPException(400)."""
    with pytest.raises(HTTPException):
        validate_siren(None)  # type: ignore


@pytest.mark.unit
@pytest.mark.negative
@given(
    siren=valid_siren_strategy(),
    extra_char=st.sampled_from(["a", "Z", "!", "?", "@", "#", "*"]),
)
@settings(max_examples=100, deadline=None)
def test_siren_with_letters_raises(siren: str, extra_char: str) -> None:
    """SIREN avec un caractère non-digit (hors space/dot) → invalide."""
    # Insert invalid char in middle
    invalid = siren[:4] + extra_char + siren[5:]
    with pytest.raises(HTTPException):
        validate_siren(invalid)


# ────────────────────────────────────────────────────────────────────
# Idempotence
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@given(siren=valid_siren_strategy())
@settings(max_examples=100, deadline=None)
def test_validate_siren_idempotent(siren: str) -> None:
    """validate_siren(validate_siren(x)) == validate_siren(x)."""
    once = validate_siren(siren)
    twice = validate_siren(once)
    assert once == twice


@pytest.mark.unit
def test_known_real_sirens() -> None:
    """SIRENs réels DEMOEMA — ne doivent jamais raise."""
    real_sirens = [
        "333275774",  # PERMIS INFORMATIQUE
        "552081317",
        "562112732",
        "542065479",
        "892318312",
    ]
    for s in real_sirens:
        result = validate_siren(s)
        assert result == s
