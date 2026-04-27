"""
EdRCF 6.0 — API Endpoint Tests
Tests for FastAPI endpoints using httpx AsyncClient.
"""

import sys
import os
from unittest.mock import patch, AsyncMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.asyncio
async def test_get_targets(test_client):
    resp = await test_client.get("/api/targets")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "total" in data
    assert "filters" in data
    assert isinstance(data["data"], list)
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_targets_with_query(test_client):
    resp = await test_client.get("/api/targets", params={"q": "ACME"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert "ACME" in data["data"][0]["name"]


@pytest.mark.asyncio
async def test_get_targets_no_match(test_client):
    resp = await test_client.get("/api/targets", params={"q": "ZZZZNOEXIST"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["data"] == []


@pytest.mark.asyncio
async def test_get_targets_filter_sector(test_client):
    resp = await test_client.get("/api/targets", params={"sector": "Industrial Tech / TIC"})
    assert resp.status_code == 200
    for t in resp.json()["data"]:
        assert t["sector"] == "Industrial Tech / TIC"


@pytest.mark.asyncio
async def test_get_targets_filter_min_score(test_client):
    resp = await test_client.get("/api/targets", params={"min_score": 0})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_get_target_by_id(test_client):
    # First get list to find an ID
    list_resp = await test_client.get("/api/targets")
    targets = list_resp.json()["data"]
    assert len(targets) > 0

    target_id = targets[0]["id"]
    resp = await test_client.get(f"/api/targets/{target_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["id"] == target_id


@pytest.mark.asyncio
async def test_get_target_not_found(test_client):
    resp = await test_client.get("/api/targets/nonexistent-999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_signals(test_client):
    resp = await test_client.get("/api/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_get_signals_filter_severity(test_client):
    resp = await test_client.get("/api/signals", params={"severity": "high"})
    assert resp.status_code == 200
    for sig in resp.json()["data"]:
        assert sig["severity"] == "high"


@pytest.mark.asyncio
async def test_get_pipeline(test_client):
    resp = await test_client.get("/api/pipeline")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 5  # 5 pipeline stages


@pytest.mark.asyncio
async def test_get_scoring_config(test_client):
    resp = await test_client.get("/api/scoring/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    config = data["data"]
    assert "maturite_dirigeant" in config
    assert "signaux_patrimoniaux" in config


@pytest.mark.asyncio
async def test_get_sectors(test_client):
    resp = await test_client.get("/api/sectors")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert isinstance(data["data"], dict)  # SECTORS_HEAT is a dict
    assert len(data["data"]) > 0


@pytest.mark.asyncio
async def test_get_graph(test_client):
    resp = await test_client.get("/api/graph")
    assert resp.status_code == 200
    body = resp.json()
    # Graph endpoint wraps in data key
    data = body.get("data", body)
    assert "nodes" in data
    assert "links" in data
    assert isinstance(data["nodes"], list)
    assert len(data["nodes"]) > 0


@pytest.mark.asyncio
async def test_copilot_query_top(test_client):
    resp = await test_client.get("/api/copilot/query", params={"q": "top cibles"})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "source" in data


@pytest.mark.asyncio
async def test_copilot_query_sector(test_client):
    resp = await test_client.get("/api/copilot/query", params={"q": "secteur courtage"})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data


@pytest.mark.asyncio
async def test_news_endpoint_with_mock():
    """Test /api/news/{siren} with mocked Google News."""
    from main import app, enriched_targets

    from httpx import AsyncClient, ASGITransport

    # Add a fake target
    enriched_targets.clear()
    enriched_targets.append({
        "id": "edrcf-001",
        "siren": "123456789",
        "name": "Test Company",
        "sector": "Services B2B",
        "city": "PARIS",
        "globalScore": 50,
        "priorityLevel": "Qualification",
        "analysis": {"type": "Monitoring", "window": "12-18 mois", "narrative": "test"},
        "topSignals": [],
        "dirigeants": [],
        "financials": {"revenue": "N/A", "revenue_growth": "N/A", "ebitda": "N/A",
                       "ebitda_margin": "N/A", "ebitda_range": "< 3M", "effectif": "N/A",
                       "last_published_year": 2024},
        "active_signals": ["press_regional"],
        "group": {"is_group": False, "parent": None, "subsidiaries": [], "consolidated_revenue": None},
        "relationship": {"strength": 5, "path": "Direct", "common_connections": 0, "edr_banker": None},
        "activation": {"deciders": ["Test"], "approach": "test", "reason": "test"},
        "risks": {"falsePositive": "Moyen (0.25)", "uncertainties": "test"},
        "scoring_details": {},
        "structure": "Familiale",
        "region": "Ile-de-France",
        "sub_sector": "N/A",
        "code_naf": "",
        "creation_date": "",
        "publication_status": "Publie",
        "statut_activite": "En activite",
        "date_cessation": None,
    })

    # Le router news a été extrait de main.py (refacto archi PR-4) — patch
    # directement dans le namespace du routeur où l'import vit.
    with patch("routers.news.get_google_news", new_callable=AsyncMock) as mock_news:
        mock_news.return_value = [
            {"title": "Test article about cession", "link": "http://test.com", "date": "2024-01-01", "source": "Test", "signals": ["presse_cession"]}
        ]
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/news/123456789")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["company"] == "Test Company"
        assert len(data["articles"]) == 1
        assert "presse_cession" in data["signals_detected"]
