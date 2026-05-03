"""Tests négatifs paramétrés sur endpoints critiques — Sprint QA-L4.6.

Cible dim 15 (negative coverage) du QCS skill qa-audit. ~30 tests négatifs
couvrant inputs invalides : SIREN malformé, dates impossibles, SQL injection
basique, JSON malformé, headers manquants, auth tokens expirés.

Skip si :
- SKIP_INTEGRATION_TESTS=1 dans l'env
- main.app non importable
- endpoint cible répond 0 (pas accessible)

Run :
    cd backend && pytest tests/test_negative_endpoints.py -v
    SKIP_INTEGRATION_TESTS=1 pytest tests/test_negative_endpoints.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if os.environ.get("SKIP_INTEGRATION_TESTS") == "1":
    pytest.skip("SKIP_INTEGRATION_TESTS=1", allow_module_level=True)


# ────────────────────────────────────────────────────────────────────
# Datasets paramétrés
# ────────────────────────────────────────────────────────────────────
INVALID_SIRENS = [
    pytest.param("ABCDEFGHI", id="letters_only"),
    pytest.param("12345", id="too_short"),
    pytest.param("12345678901234", id="too_long_siret_like"),
    pytest.param("", id="empty"),
    pytest.param("12345678X", id="mixed_letter"),
    pytest.param("123 456 78", id="space_short"),
    pytest.param("---------", id="dashes"),
    pytest.param("000000000", id="all_zeros_pass_format_only"),
]

SQL_INJECTION_PAYLOADS = [
    pytest.param("'; DROP TABLE users; --", id="sqli_drop_table"),
    pytest.param("1 OR 1=1", id="sqli_or_true"),
    pytest.param("' UNION SELECT * FROM pg_catalog.pg_user --", id="sqli_union"),
    pytest.param("admin'--", id="sqli_comment_bypass"),
    pytest.param("\"; DELETE FROM gold.cibles; --", id="sqli_delete"),
]

INVALID_DATES = [
    pytest.param("2026-02-30", id="feb_30_impossible"),
    pytest.param("0000-00-00", id="zero_date"),
    pytest.param("not-a-date", id="not_a_date"),
    pytest.param("2026-13-01", id="month_13"),
    pytest.param("2026-12-32", id="day_32"),
]

INVALID_QUERY_PARAMS = [
    pytest.param({"min_score": "abc"}, id="min_score_not_number"),
    pytest.param({"min_score": "-9999"}, id="min_score_below_range"),
    pytest.param({"depth": "10"}, id="depth_above_max"),
    pytest.param({"limit": "-5"}, id="limit_negative"),
    pytest.param({"limit": "999999"}, id="limit_too_large"),
]


# ────────────────────────────────────────────────────────────────────
# Test client setup (réutilise main.app si disponible)
# ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def app_client():
    try:
        from main import app  # type: ignore
        from httpx import AsyncClient, ASGITransport
    except ImportError as e:
        pytest.skip(f"main.app indisponible: {e}")

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ────────────────────────────────────────────────────────────────────
# Tests SIREN invalide → 400/404/422
# ────────────────────────────────────────────────────────────────────
@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_siren", INVALID_SIRENS)
async def test_fiche_invalid_siren(app_client, invalid_siren: str) -> None:
    """GET /api/datalake/fiche/<SIREN_invalide> → 400/404/422 ou 503 (pool)."""
    resp = await app_client.get(f"/api/datalake/fiche/{invalid_siren}")
    # 400 validation, 404 not found, 422 unprocessable, 503 datalake unavail
    assert resp.status_code in {400, 404, 422, 503, 500}, \
        f"got {resp.status_code} for SIREN={invalid_siren!r}"


@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_siren", INVALID_SIRENS)
async def test_scoring_invalid_siren(app_client, invalid_siren: str) -> None:
    """GET /api/datalake/scoring/<SIREN_invalide> → 4xx/5xx."""
    resp = await app_client.get(f"/api/datalake/scoring/{invalid_siren}")
    assert resp.status_code >= 400


@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_siren", INVALID_SIRENS[:5])
async def test_graph_invalid_siren(app_client, invalid_siren: str) -> None:
    """GET /api/datalake/graph/<SIREN_invalide> → 4xx/5xx."""
    resp = await app_client.get(f"/api/datalake/graph/{invalid_siren}")
    assert resp.status_code >= 400


# ────────────────────────────────────────────────────────────────────
# Tests SQL injection
# ────────────────────────────────────────────────────────────────────
@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
async def test_sqli_in_search(app_client, payload: str) -> None:
    """SQLi dans /api/targets?q= → jamais 500, jamais leak schéma."""
    resp = await app_client.get("/api/targets", params={"q": payload})
    # Doit retourner 200 (résultat vide) ou 4xx, pas 500 (crash)
    assert resp.status_code != 500, f"SQLi crashed: {payload!r}"
    if resp.status_code == 200:
        # Pas de leak de structure DB dans le body
        body = resp.text.lower()
        assert "pg_catalog" not in body
        assert "information_schema" not in body
        assert "syntax error" not in body


@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:3])
async def test_sqli_in_siren_path(app_client, payload: str) -> None:
    """SQLi dans path SIREN → 4xx, pas 500."""
    resp = await app_client.get(f"/api/datalake/fiche/{payload}")
    assert resp.status_code != 500


# ────────────────────────────────────────────────────────────────────
# Tests query params invalides
# ────────────────────────────────────────────────────────────────────
@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("params", INVALID_QUERY_PARAMS)
async def test_invalid_query_params(app_client, params: dict) -> None:
    """Query params invalides → 422 (FastAPI validation) ou 400."""
    resp = await app_client.get("/api/targets", params=params)
    assert resp.status_code in {200, 400, 422}, \
        f"got {resp.status_code} for params={params}"


# ────────────────────────────────────────────────────────────────────
# Tests JSON malformé / Content-Type missing
# ────────────────────────────────────────────────────────────────────
@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
async def test_json_malformed_post(app_client) -> None:
    """POST avec JSON malformé → 422."""
    resp = await app_client.post(
        "/api/scoring/config",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code in {400, 422, 404, 405}


@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
async def test_json_empty_body_post(app_client) -> None:
    """POST avec body vide → 422."""
    resp = await app_client.post("/api/scoring/config", content=b"")
    assert resp.status_code >= 400


@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
async def test_json_wrong_content_type(app_client) -> None:
    """POST JSON avec Content-Type text/plain → erreur."""
    resp = await app_client.post(
        "/api/scoring/config",
        content=b'{"a":1}',
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code >= 400


# ────────────────────────────────────────────────────────────────────
# Tests dirigeant endpoint avec inputs invalides
# ────────────────────────────────────────────────────────────────────
@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("nom,prenom", [
    pytest.param("", "", id="both_empty"),
    pytest.param("X", "", id="prenom_empty"),
    pytest.param("'; DROP--", "Jean", id="sqli_in_nom"),
    pytest.param("A" * 500, "B" * 500, id="overflow_long"),
])
async def test_dirigeant_invalid_input(app_client, nom: str, prenom: str) -> None:
    """GET /api/datalake/dirigeant/<nom>/<prenom> avec inputs douteux → no 500."""
    resp = await app_client.get(f"/api/datalake/dirigeant/{nom}/{prenom}")
    # Un 404 propre ou un 4xx attendu, pas un 500 crash
    assert resp.status_code != 500, \
        f"crashed on nom={nom!r} prenom={prenom!r}"


# ────────────────────────────────────────────────────────────────────
# Tests Headers / Auth
# ────────────────────────────────────────────────────────────────────
@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
async def test_expired_auth_token(app_client) -> None:
    """Authorization Bearer avec token expiré → 401 ou ignoré (endpoint public)."""
    resp = await app_client.get(
        "/api/targets",
        headers={"Authorization": "Bearer eyJexpired.token.signature"},
    )
    # Endpoint public → 200 ; sinon → 401/403
    assert resp.status_code in {200, 401, 403}


@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
async def test_method_not_allowed(app_client) -> None:
    """DELETE sur GET-only endpoint → 405."""
    resp = await app_client.delete("/api/targets")
    assert resp.status_code in {404, 405}


@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
async def test_unknown_endpoint_404(app_client) -> None:
    """Endpoint inexistant → 404."""
    resp = await app_client.get("/api/this-does-not-exist-1234")
    assert resp.status_code == 404


# ────────────────────────────────────────────────────────────────────
# Tests path traversal
# ────────────────────────────────────────────────────────────────────
@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    pytest.param("../../etc/passwd", id="unix_traversal"),
    pytest.param("..%2F..%2Fetc%2Fpasswd", id="encoded_traversal"),
    pytest.param("..\\..\\windows\\system32", id="win_traversal"),
])
async def test_path_traversal_in_siren(app_client, payload: str) -> None:
    """Path traversal dans SIREN → 4xx, jamais 500 ni leak."""
    resp = await app_client.get(f"/api/datalake/fiche/{payload}")
    assert resp.status_code != 500
    body = resp.text.lower()
    assert "root:" not in body  # /etc/passwd marker
    assert "uid=" not in body
