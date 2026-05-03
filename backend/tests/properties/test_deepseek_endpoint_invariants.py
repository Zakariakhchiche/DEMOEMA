"""Property-based tests Hypothesis sur clients.deepseek._resolve_endpoint.

Invariants ciblés (dim 3 path_coverage QA L4 Sprint 1) :
- Si AI_GATEWAY_API_KEY définie → tuple (key, gateway URL Vercel, gateway model)
- Sinon si DEEPSEEK_API_KEY définie → tuple (key, deepseek URL, deepseek model)
- Si aucune → None
- Priorité absolue gateway > deepseek (jamais l'inverse)
- Aucune valeur autre que tuple|None retournée

NOTE — `_resolve_endpoint` lit AI_GATEWAY_API_KEY et DEEPSEEK_API_KEY au
niveau module (capturés à import-time depuis os.getenv). On utilise un
context manager `_patched_keys()` pour swap temporaire les attributs
module (Hypothesis interdit les fixtures pytest function-scoped car elles
ne sont pas reset entre inputs générés).

Run :
    cd backend && pytest tests/properties/test_deepseek_endpoint_invariants.py -v
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hypothesis import given, settings, strategies as st  # type: ignore
import pytest

from clients import deepseek  # type: ignore


GATEWAY_URL = "https://ai-gateway.vercel.sh/v1/chat/completions"
GATEWAY_MODEL = "deepseek/deepseek-chat"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


@contextmanager
def _patched_keys(gateway: str = "", deepseek_key: str = ""):
    """Context manager qui swap AI_GATEWAY_API_KEY + DEEPSEEK_API_KEY puis restore.

    Hypothesis exige une approche non-fixture (les fixtures function-scoped
    ne sont pas re-exécutées entre inputs générés).
    """
    orig_gw = deepseek.AI_GATEWAY_API_KEY
    orig_ds = deepseek.DEEPSEEK_API_KEY
    deepseek.AI_GATEWAY_API_KEY = gateway
    deepseek.DEEPSEEK_API_KEY = deepseek_key
    try:
        yield
    finally:
        deepseek.AI_GATEWAY_API_KEY = orig_gw
        deepseek.DEEPSEEK_API_KEY = orig_ds


# Stratégie : clés non-vides plausibles (sk-... format type)
def api_key_strategy():
    """Génère des api keys plausibles (non-vides, sans whitespace)."""
    return st.text(
        alphabet=st.characters(min_codepoint=33, max_codepoint=126, blacklist_characters=" \t\n\r"),
        min_size=1,
        max_size=80,
    )


# ────────────────────────────────────────────────────────────────────
# Invariants positifs
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@given(gateway_key=api_key_strategy())
@settings(max_examples=200, deadline=None)
def test_gateway_key_takes_priority(gateway_key: str) -> None:
    """AI_GATEWAY_API_KEY définie → tuple gateway, peu importe DEEPSEEK_API_KEY."""
    with _patched_keys(gateway=gateway_key, deepseek_key="ignored-deepseek-key"):
        result = deepseek._resolve_endpoint()
    assert result is not None
    assert isinstance(result, tuple)
    assert len(result) == 3
    key, url, model = result
    assert key == gateway_key
    assert url == GATEWAY_URL
    assert model == GATEWAY_MODEL


@pytest.mark.unit
@pytest.mark.property
@given(deepseek_key=api_key_strategy())
@settings(max_examples=200, deadline=None)
def test_deepseek_key_only(deepseek_key: str) -> None:
    """Sans gateway, DEEPSEEK_API_KEY → tuple deepseek direct."""
    with _patched_keys(gateway="", deepseek_key=deepseek_key):
        result = deepseek._resolve_endpoint()
    assert result is not None
    key, url, model = result
    assert key == deepseek_key
    assert url == DEEPSEEK_URL
    assert model == DEEPSEEK_MODEL


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.negative
def test_no_keys_returns_none() -> None:
    """Aucune clé → None (caller doit fallback rule-based)."""
    with _patched_keys(gateway="", deepseek_key=""):
        assert deepseek._resolve_endpoint() is None


@pytest.mark.unit
@pytest.mark.property
@given(
    gateway_key=st.one_of(st.just(""), api_key_strategy()),
    deepseek_key=st.one_of(st.just(""), api_key_strategy()),
)
@settings(max_examples=200, deadline=None)
def test_resolve_endpoint_return_shape(gateway_key: str, deepseek_key: str) -> None:
    """Toutes combinaisons : retour est None ou tuple[str, str, str] de longueur 3.

    Invariant universel — pas d'autre type, pas d'éléments None dans le tuple.
    """
    with _patched_keys(gateway=gateway_key, deepseek_key=deepseek_key):
        result = deepseek._resolve_endpoint()
    if not gateway_key and not deepseek_key:
        assert result is None
    else:
        assert isinstance(result, tuple)
        assert len(result) == 3
        for elem in result:
            assert isinstance(elem, str)
            assert elem  # non-vide


@pytest.mark.unit
@pytest.mark.property
@given(
    gateway_key=api_key_strategy(),
    deepseek_key=api_key_strategy(),
)
@settings(max_examples=100, deadline=None)
def test_gateway_priority_strict(gateway_key: str, deepseek_key: str) -> None:
    """Si les DEUX clés sont définies, gateway gagne TOUJOURS."""
    with _patched_keys(gateway=gateway_key, deepseek_key=deepseek_key):
        result = deepseek._resolve_endpoint()
    assert result is not None
    key, url, _ = result
    assert key == gateway_key
    assert "ai-gateway.vercel.sh" in url


@pytest.mark.unit
@pytest.mark.property
def test_resolve_endpoint_idempotent() -> None:
    """Appel répété sans changement d'env retourne le même résultat."""
    with _patched_keys(gateway="stable-gateway-key", deepseek_key="stable-deepseek-key"):
        a = deepseek._resolve_endpoint()
        b = deepseek._resolve_endpoint()
        c = deepseek._resolve_endpoint()
    assert a == b == c
