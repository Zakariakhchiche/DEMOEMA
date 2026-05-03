"""Property-based tests Hypothesis sur routers.datalake._safe.

Invariants ciblés (dim 3 path_coverage QA L4 Sprint 1) :
- _safe(success_coro) → retourne le résultat du coro (passthrough)
- _safe(timeout_coro) → retourne `default` (jamais d'exception remontée)
- _safe(raising_coro) → retourne `default` (catch-all sur Exception)
- Quel que soit `default` (None, [], {}, dict, int, str…), il est retourné tel quel
- Le timeout par défaut (4s) ne fait pas crasher sur des coros rapides

Cf. routers/datalake.py:38 — wrapper module-level pour éviter HTTP 500
sur queries longues (Carrefour 652014051 = 12 filiales en JOIN).

Run :
    cd backend && pytest tests/properties/test_safe_wrapper_invariants.py -v
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hypothesis import given, settings, strategies as st  # type: ignore
import pytest

from routers.datalake import _safe  # type: ignore


# ────────────────────────────────────────────────────────────────────
# Helpers : factories de coroutines
# ────────────────────────────────────────────────────────────────────
async def _ok(value):
    """Coroutine qui réussit immédiatement et retourne `value`."""
    return value


async def _slow(value, delay=0.5):
    """Coroutine qui prend `delay` secondes avant de retourner."""
    await asyncio.sleep(delay)
    return value


async def _raise(exc):
    """Coroutine qui raise immédiatement."""
    raise exc


# ────────────────────────────────────────────────────────────────────
# Happy path : passthrough du résultat
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@pytest.mark.asyncio
@given(
    value=st.one_of(
        st.none(),
        st.integers(),
        st.text(max_size=100),
        st.lists(st.integers(), max_size=10),
        st.dictionaries(st.text(max_size=10), st.integers(), max_size=5),
    )
)
@settings(max_examples=100, deadline=None)
async def test_safe_passes_through_success(value) -> None:
    """_safe sur coroutine qui réussit doit retourner le résultat tel quel."""
    result = await _safe(_ok(value), timeout_s=2.0, default="DEFAULT_NEVER_USED")
    assert result == value


# ────────────────────────────────────────────────────────────────────
# Timeout : default retourné
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@pytest.mark.negative
@pytest.mark.asyncio
@given(
    default=st.one_of(
        st.none(),
        st.just([]),
        st.just({}),
        st.integers(),
        st.text(max_size=20),
        st.lists(st.integers(), max_size=5),
    )
)
@settings(max_examples=30, deadline=None)
async def test_safe_returns_default_on_timeout(default) -> None:
    """Si la coroutine dépasse le timeout, retourner `default` (pas d'exception)."""
    # Timeout très court (50ms) + coroutine lente (500ms) = timeout garanti
    result = await _safe(_slow("never_returned", delay=0.5), timeout_s=0.05, default=default)
    assert result == default


# ────────────────────────────────────────────────────────────────────
# Exception : default retourné
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("exc_factory", [
    lambda: ValueError("boom"),
    lambda: KeyError("missing"),
    lambda: RuntimeError("oops"),
    lambda: ConnectionError("network"),
    lambda: TimeoutError("from inside"),
])
async def test_safe_returns_default_on_exception(exc_factory) -> None:
    """N'importe quelle Exception → default, jamais propagée."""
    exc = exc_factory()
    sentinel = {"sentinel": True}
    result = await _safe(_raise(exc), timeout_s=2.0, default=sentinel)
    assert result == sentinel


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.negative
@pytest.mark.asyncio
@given(default=st.one_of(st.none(), st.integers(), st.text(max_size=30)))
@settings(max_examples=30, deadline=None)
async def test_safe_default_none_default(default) -> None:
    """Quand le caller ne précise pas default, c'est None par défaut."""
    # Test que default kwargs marche
    result_none = await _safe(_raise(ValueError("x")))
    assert result_none is None
    # Test custom default
    result_custom = await _safe(_raise(ValueError("x")), default=default)
    assert result_custom == default


# ────────────────────────────────────────────────────────────────────
# Tests positifs explicites (sanity)
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@pytest.mark.asyncio
async def test_safe_with_default_timeout() -> None:
    """Timeout par défaut (4s) avec coroutine rapide → succès."""
    result = await _safe(_ok([1, 2, 3]))
    assert result == [1, 2, 3]


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.asyncio
async def test_safe_returns_falsy_value_correctly() -> None:
    """0, '', [], {} sont des résultats valides (pas confondus avec default).

    Pitfall classique : `if not result: return default` masquerait des
    vrais résultats falsy. _safe doit utiliser try/except, pas un check.
    """
    assert await _safe(_ok(0), default=999) == 0
    assert await _safe(_ok(""), default="default") == ""
    assert await _safe(_ok([]), default=[1]) == []
    assert await _safe(_ok({}), default={"k": "v"}) == {}
    assert await _safe(_ok(False), default=True) is False
