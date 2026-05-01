"""
EdRCF 6.0 — Tests retry/backoff + fallback silver.opensanctions du tool search_sanctions.

Audit QA 2026-05-01 : OpenSanctions API retournait 503 sur 3% des questions
compliance, sans fallback → degraded UX. Patch G6 : 3 tentatives avec backoff
exponentiel sur 502/503/504, puis fallback direct sur silver.opensanctions
(280k rows) avec flag `degraded:true`.
"""
from __future__ import annotations

import sys
import os
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clients.deepseek import _execute_tool  # noqa: E402


class _Resp:
    def __init__(self, status: int, payload: dict | None = None):
        self.status_code = status
        self._payload = payload or {"rows": []}

    def json(self):
        return self._payload


class _SeqClient:
    """httpx.AsyncClient mock qui retourne des réponses séquentielles."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list[tuple[str, dict | None]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None):
        self.calls.append((url, params))
        if not self.responses:
            return _Resp(500, {})
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_sanctions_200_first_try_no_retry():
    """Cas nominal : 200 du premier coup, pas de fallback."""
    client = _SeqClient([_Resp(200, {"rows": [{"name": "Foo Sanction"}]})])
    with patch("clients.deepseek.httpx.AsyncClient", return_value=client):
        result = await _execute_tool(
            "search_sanctions",
            {"entity_name": "Foo"},
            "http://localhost:8000",
        )
    assert result["n_sanctions"] == 1
    assert result["source"] == "silver.sanctions"
    assert "degraded" not in result
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_sanctions_503_retries_then_succeeds():
    """503 → retry → 200 sur la 2e tentative."""
    client = _SeqClient([_Resp(503), _Resp(200, {"rows": [{"name": "Bar"}]})])
    # Patch asyncio.sleep pour tests rapides
    with patch("clients.deepseek.httpx.AsyncClient", return_value=client), \
         patch("clients.deepseek.asyncio.sleep", return_value=None):
        result = await _execute_tool(
            "search_sanctions",
            {"entity_name": "Bar"},
            "http://localhost:8000",
        )
    assert result["n_sanctions"] == 1
    assert result["source"] == "silver.sanctions"
    assert len(client.calls) == 2  # 1 retry effectué


@pytest.mark.asyncio
async def test_sanctions_503_3x_then_fallback_opensanctions():
    """3x 503 sur silver.sanctions → fallback silver.opensanctions OK."""
    client = _SeqClient(
        [_Resp(503), _Resp(503), _Resp(503), _Resp(200, {"rows": [{"name": "OFAC entry"}]})]
    )
    with patch("clients.deepseek.httpx.AsyncClient", return_value=client), \
         patch("clients.deepseek.asyncio.sleep", return_value=None):
        result = await _execute_tool(
            "search_sanctions",
            {"entity_name": "test"},
            "http://localhost:8000",
        )
    assert result["n_sanctions"] == 1
    assert result["source"] == "silver.opensanctions"
    assert result["degraded"] is True
    assert "503" in result["degraded_reason"]
    # 3 calls primary (les 3 503) + 1 fallback
    assert len(client.calls) == 4


@pytest.mark.asyncio
async def test_sanctions_403_no_retry_no_fallback_returned():
    """4xx (403/404) : pas de retry, fallback direct (peut-être OK), sinon error."""
    client = _SeqClient([_Resp(403), _Resp(404)])
    with patch("clients.deepseek.httpx.AsyncClient", return_value=client), \
         patch("clients.deepseek.asyncio.sleep", return_value=None):
        result = await _execute_tool(
            "search_sanctions",
            {"entity_name": "test"},
            "http://localhost:8000",
        )
    # 1 call primary (403, pas de retry sur 4xx) + 1 fallback (404)
    assert len(client.calls) == 2
    assert result.get("degraded") is True
    assert "error" in result


@pytest.mark.asyncio
async def test_sanctions_504_then_fallback_also_503():
    """Timeout primary + fallback aussi en 503 → error degraded."""
    client = _SeqClient([_Resp(504), _Resp(504), _Resp(504), _Resp(503)])
    with patch("clients.deepseek.httpx.AsyncClient", return_value=client), \
         patch("clients.deepseek.asyncio.sleep", return_value=None):
        result = await _execute_tool(
            "search_sanctions",
            {"entity_name": "test"},
            "http://localhost:8000",
        )
    assert result.get("degraded") is True
    assert "error" in result
    assert result["sanctions"] == []


@pytest.mark.asyncio
async def test_sanctions_default_limit_passed():
    """Sans limit explicite, default 10."""
    client = _SeqClient([_Resp(200, {"rows": []})])
    with patch("clients.deepseek.httpx.AsyncClient", return_value=client):
        await _execute_tool(
            "search_sanctions",
            {},
            "http://localhost:8000",
        )
    assert client.calls[0][1] == {"limit": 10}


@pytest.mark.asyncio
async def test_sanctions_custom_limit_propagated():
    client = _SeqClient([_Resp(200, {"rows": []})])
    with patch("clients.deepseek.httpx.AsyncClient", return_value=client):
        await _execute_tool(
            "search_sanctions",
            {"entity_name": "X", "limit": 25},
            "http://localhost:8000",
        )
    assert client.calls[0][1] == {"limit": 25, "search": "X"}
