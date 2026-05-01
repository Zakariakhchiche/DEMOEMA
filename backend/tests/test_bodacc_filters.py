"""
EdRCF 6.0 — Tests filtres tool search_signaux_bodacc.

Audit QA 2026-05-01 : la signature LLM déclarait dept/type_avis/days mais l'impl
ne les transmettait pas à l'endpoint datalake → faux positifs (l'agent croyait
filtrer mais retournait toujours les 10-50 dernières annonces).

Ces tests vérifient via mock httpx que les filtres sont bien composés en query
params lorsqu'ils sont fournis.
"""
from __future__ import annotations

import sys
import os
from unittest.mock import patch, AsyncMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clients.deepseek import _execute_tool  # noqa: E402


class _FakeResp:
    def __init__(self, status: int = 200, payload: dict | None = None):
        self.status_code = status
        self._payload = payload or {"rows": []}

    def json(self):
        return self._payload


class _FakeClient:
    """Capture le dernier appel GET pour assertion."""

    def __init__(self):
        self.last_url: str | None = None
        self.last_params: dict | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None):
        self.last_url = url
        self.last_params = params
        return _FakeResp(200, {"rows": [{"siren": "123456789", "type_avis": "cession"}]})


@pytest.mark.asyncio
async def test_no_filters_default_limit():
    fake = _FakeClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=fake):
        result = await _execute_tool(
            "search_signaux_bodacc",
            {},
            "http://localhost:8000",
        )
    assert fake.last_params == {"limit": 10}
    assert "filters_applied" in result


@pytest.mark.asyncio
async def test_dept_filter_zfilled_to_2_digits():
    """dept=1 (Ain) doit être normalisé en '01' (le datalake stocke à 2 digits)."""
    fake = _FakeClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=fake):
        await _execute_tool(
            "search_signaux_bodacc",
            {"dept": "1", "limit": 5},
            "http://localhost:8000",
        )
    assert fake.last_params is not None
    filt = fake.last_params.get("filter", "")
    assert "dept.eq.01" in filt, f"dept must be zfilled to 01, got: {filt}"


@pytest.mark.asyncio
async def test_dept_filter_already_2_digits_unchanged():
    fake = _FakeClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=fake):
        await _execute_tool(
            "search_signaux_bodacc",
            {"dept": "13"},
            "http://localhost:8000",
        )
    assert "dept.eq.13" in fake.last_params.get("filter", "")


@pytest.mark.asyncio
async def test_siren_filter_applied():
    fake = _FakeClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=fake):
        await _execute_tool(
            "search_signaux_bodacc",
            {"siren": "892318312"},
            "http://localhost:8000",
        )
    assert "siren.eq.892318312" in fake.last_params.get("filter", "")


@pytest.mark.asyncio
async def test_type_avis_filter_applied():
    fake = _FakeClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=fake):
        await _execute_tool(
            "search_signaux_bodacc",
            {"type_avis": "procedure_collective"},
            "http://localhost:8000",
        )
    assert "type_avis.eq.procedure_collective" in fake.last_params.get("filter", "")


@pytest.mark.asyncio
async def test_days_filter_temporal():
    fake = _FakeClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=fake):
        await _execute_tool(
            "search_signaux_bodacc",
            {"days": 30},
            "http://localhost:8000",
        )
    filt = fake.last_params.get("filter", "")
    assert "date_publication.gte" in filt
    assert "30" in filt


@pytest.mark.asyncio
async def test_combined_filters():
    fake = _FakeClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=fake):
        await _execute_tool(
            "search_signaux_bodacc",
            {"dept": "13", "type_avis": "cession", "days": 7, "limit": 20},
            "http://localhost:8000",
        )
    filt = fake.last_params.get("filter", "")
    assert "dept.eq.13" in filt
    assert "type_avis.eq.cession" in filt
    assert "date_publication.gte" in filt
    assert fake.last_params["limit"] == 20


@pytest.mark.asyncio
async def test_invalid_days_silently_ignored():
    """days='abc' ne doit pas crasher — juste ignoré."""
    fake = _FakeClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=fake):
        result = await _execute_tool(
            "search_signaux_bodacc",
            {"days": "abc"},
            "http://localhost:8000",
        )
    # Pas de filter date_publication
    filt = fake.last_params.get("filter", "")
    assert "date_publication" not in filt
    # Le résultat reste valide
    assert "filters_applied" in result


@pytest.mark.asyncio
async def test_response_includes_filters_applied():
    """Le résultat retourné au LLM doit lister les filtres pour audit/transparence."""
    fake = _FakeClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=fake):
        result = await _execute_tool(
            "search_signaux_bodacc",
            {"siren": "892318312", "type_avis": "cession"},
            "http://localhost:8000",
        )
    fa = result.get("filters_applied")
    assert isinstance(fa, list)
    assert any("siren" in f for f in fa)
    assert any("type_avis" in f for f in fa)


@pytest.mark.asyncio
async def test_http_error_returns_empty_with_filters_context():
    """Sur erreur HTTP, on retourne quand même filters_applied (pour debug LLM)."""
    fake = _FakeClient()

    class _ErrClient(_FakeClient):
        async def get(self, url, params=None):
            self.last_url = url
            self.last_params = params
            return _FakeResp(503, {})

    err = _ErrClient()
    with patch("clients.deepseek.httpx.AsyncClient", return_value=err):
        result = await _execute_tool(
            "search_signaux_bodacc",
            {"dept": "75"},
            "http://localhost:8000",
        )
    assert "error" in result
    assert "filters_applied" in result
    assert any("dept" in f for f in result["filters_applied"])
