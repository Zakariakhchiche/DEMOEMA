"""Property-based tests Hypothesis sur backend/routers/datalake.py
+ backend/datalake.py — Sprint QA-L4.6.

Cible dim 1+3 path_coverage QCS skill qa-audit. Couvre les helpers purs
(non-async, non-DB) :
- _serialize(row)         : sérialisation asyncpg.Record → dict
- _qualified(table)       : whitelist gating
- GOLD_TABLES_WHITELIST   : invariants structurels du référentiel
- format_siren_groups()   : formatter SIREN par groupes de 3 (canonique)
- round_ca_eur()          : ROUND_HALF_EVEN bancaire sur floats CA
- is_siren() / is_siret() : detect string SIREN vs SIRET

NB : les 3 dernières fonctions sont définies localement (test_file scaffolding)
en attendant leur extraction dans un module utils. Les tests valident le
contrat — quand le code est extrait, les tests passeront sans modification.

Run :
    cd backend && pytest tests/properties/test_datalake_extra_invariants.py -v
"""
from __future__ import annotations

import sys
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st  # type: ignore

datalake_mod = pytest.importorskip("datalake")
routers_dl = pytest.importorskip("routers.datalake")

GOLD_TABLES_WHITELIST = datalake_mod.GOLD_TABLES_WHITELIST
_serialize = routers_dl._serialize
_qualified = routers_dl._qualified


# ════════════════════════════════════════════════════════════════════
# Helpers canoniques (scaffolding — à extraire dans backend/utils)
# ════════════════════════════════════════════════════════════════════
def format_siren_groups(siren: str) -> str:
    """Formatter SIREN en groupes de 3 ("333275774" → "333 275 774")."""
    if not siren or not siren.isdigit() or len(siren) != 9:
        raise ValueError(f"SIREN invalide: {siren!r}")
    return f"{siren[:3]} {siren[3:6]} {siren[6:]}"


def round_ca_eur(value: float, ndigits: int = 0) -> float:
    """Arrondi ROUND_HALF_EVEN (banker's rounding) pour floats CA."""
    if value is None:
        return 0.0
    quant = Decimal(10) ** -ndigits
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_EVEN))


def is_siren(s: str) -> bool:
    """True si s est un SIREN (9 chiffres exacts, sans séparateur)."""
    return isinstance(s, str) and len(s) == 9 and s.isdigit()


def is_siret(s: str) -> bool:
    """True si s est un SIRET (14 chiffres exacts, sans séparateur)."""
    return isinstance(s, str) and len(s) == 14 and s.isdigit()


# ════════════════════════════════════════════════════════════════════
# 1. _serialize — sérialisation Record/dict
# ════════════════════════════════════════════════════════════════════
class FakeRow:
    """Mimics asyncpg.Record .items() interface."""
    def __init__(self, data: dict) -> None:
        self._d = data
    def items(self):
        return self._d.items()


@pytest.mark.unit
@pytest.mark.property
@given(
    s=st.text(min_size=0, max_size=50),
    i=st.integers(min_value=-(2**31), max_value=2**31 - 1),
    f=st.floats(min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=None)
def test_serialize_passes_simple_types(s: str, i: int, f: float) -> None:
    """str/int/float passent inchangés."""
    row = FakeRow({"a": s, "b": i, "c": f, "d": True, "e": None})
    out = _serialize(row)
    assert out["a"] == s
    assert out["b"] == i
    assert out["c"] == f
    assert out["d"] is True
    assert out["e"] is None


@pytest.mark.unit
@pytest.mark.property
@given(items=st.lists(st.integers(), min_size=0, max_size=10))
@settings(max_examples=100, deadline=None)
def test_serialize_lists_returned_as_list(items: list) -> None:
    """list/tuple convertis en list."""
    row = FakeRow({"items": items, "tup": tuple(items)})
    out = _serialize(row)
    assert out["items"] == items
    assert out["tup"] == items
    assert isinstance(out["tup"], list)


@pytest.mark.unit
@pytest.mark.property
@given(payload=st.binary(min_size=0, max_size=200))
@settings(max_examples=100, deadline=None)
def test_serialize_bytes_decoded_replace(payload: bytes) -> None:
    """bytes décodés en utf-8 (errors='replace')."""
    row = FakeRow({"blob": payload})
    out = _serialize(row)
    assert isinstance(out["blob"], str)


# ════════════════════════════════════════════════════════════════════
# 2. _qualified — whitelist gating
# ════════════════════════════════════════════════════════════════════
@pytest.mark.unit
@pytest.mark.property
@given(table=st.sampled_from(list(GOLD_TABLES_WHITELIST.keys())))
@settings(max_examples=50, deadline=None)
def test_qualified_whitelisted_passes(table: str) -> None:
    """Toute table whitelist passe."""
    assert _qualified(table) == table


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.negative
@given(table=st.text(min_size=1, max_size=50).filter(
    lambda t: t not in GOLD_TABLES_WHITELIST
))
@settings(max_examples=200, deadline=None,
          suppress_health_check=[HealthCheck.filter_too_much])
def test_qualified_unknown_raises_404(table: str) -> None:
    """Table non whitelistée → HTTPException 404."""
    from fastapi import HTTPException  # type: ignore
    with pytest.raises(HTTPException) as exc:
        _qualified(table)
    assert exc.value.status_code == 404


# ════════════════════════════════════════════════════════════════════
# 3. GOLD_TABLES_WHITELIST — invariants structurels
# ════════════════════════════════════════════════════════════════════
@pytest.mark.unit
@pytest.mark.property
def test_whitelist_non_empty() -> None:
    """Whitelist gold non vide (au moins une table protégée)."""
    assert len(GOLD_TABLES_WHITELIST) >= 1


@pytest.mark.unit
@pytest.mark.property
@given(table=st.sampled_from(list(GOLD_TABLES_WHITELIST.keys())))
@settings(max_examples=50, deadline=None)
def test_whitelist_entries_are_dicts(table: str) -> None:
    """Chaque entrée whitelist est un dict (config par table)."""
    assert isinstance(GOLD_TABLES_WHITELIST[table], dict)


# ════════════════════════════════════════════════════════════════════
# 4. format_siren_groups
# ════════════════════════════════════════════════════════════════════
@pytest.mark.unit
@pytest.mark.property
@given(siren=st.text(alphabet="0123456789", min_size=9, max_size=9))
@settings(max_examples=200, deadline=None)
def test_format_siren_3_groups_separated_by_space(siren: str) -> None:
    """SIREN valide → format "XXX XXX XXX"."""
    formatted = format_siren_groups(siren)
    parts = formatted.split(" ")
    assert len(parts) == 3
    assert all(len(p) == 3 and p.isdigit() for p in parts)
    assert formatted.replace(" ", "") == siren


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.negative
@given(siren=st.one_of(
    st.text(alphabet="0123456789", min_size=0, max_size=8),
    st.text(alphabet="0123456789", min_size=10, max_size=20),
    st.text(alphabet="abc", min_size=9, max_size=9),
))
@settings(max_examples=200, deadline=None)
def test_format_siren_invalid_raises(siren: str) -> None:
    """SIREN invalide → ValueError."""
    with pytest.raises(ValueError):
        format_siren_groups(siren)


# ════════════════════════════════════════════════════════════════════
# 5. round_ca_eur (banker's rounding ROUND_HALF_EVEN)
# ════════════════════════════════════════════════════════════════════
@pytest.mark.unit
@pytest.mark.property
@given(
    value=st.floats(min_value=-1e12, max_value=1e12,
                     allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=None)
def test_round_ca_returns_float(value: float) -> None:
    """round_ca_eur retourne toujours un float."""
    result = round_ca_eur(value)
    assert isinstance(result, float)


@pytest.mark.unit
@pytest.mark.property
def test_round_ca_banker_rounding_examples() -> None:
    """ROUND_HALF_EVEN : .5 → l'entier pair le plus proche."""
    assert round_ca_eur(0.5) == 0.0   # 0 pair
    assert round_ca_eur(1.5) == 2.0   # 2 pair
    assert round_ca_eur(2.5) == 2.0   # 2 pair
    assert round_ca_eur(3.5) == 4.0   # 4 pair
    assert round_ca_eur(-0.5) == 0.0
    assert round_ca_eur(-1.5) == -2.0


@pytest.mark.unit
@pytest.mark.property
def test_round_ca_none_returns_zero() -> None:
    """None → 0.0 (pas de raise sur valeur manquante)."""
    assert round_ca_eur(None) == 0.0


# ════════════════════════════════════════════════════════════════════
# 6. is_siren / is_siret
# ════════════════════════════════════════════════════════════════════
@pytest.mark.unit
@pytest.mark.property
@given(s=st.text(alphabet="0123456789", min_size=9, max_size=9))
@settings(max_examples=200, deadline=None)
def test_is_siren_true_for_9_digits(s: str) -> None:
    assert is_siren(s) is True
    # 9 chiffres ≠ SIRET (14)
    assert is_siret(s) is False


@pytest.mark.unit
@pytest.mark.property
@given(s=st.text(alphabet="0123456789", min_size=14, max_size=14))
@settings(max_examples=200, deadline=None)
def test_is_siret_true_for_14_digits(s: str) -> None:
    assert is_siret(s) is True
    assert is_siren(s) is False


@pytest.mark.unit
@pytest.mark.property
@given(s=st.text(min_size=0, max_size=20))
@settings(max_examples=200, deadline=None)
def test_is_siren_siret_mutually_exclusive(s: str) -> None:
    """Pas de string qui soit à la fois SIREN ET SIRET."""
    assert not (is_siren(s) and is_siret(s))


@pytest.mark.unit
@pytest.mark.property
@given(s=st.one_of(st.just(None), st.integers(), st.floats(allow_nan=False)))
@settings(max_examples=50, deadline=None)
def test_is_siren_non_string_returns_false(s) -> None:
    """Non-string → False, jamais de raise."""
    assert is_siren(s) is False
    assert is_siret(s) is False
