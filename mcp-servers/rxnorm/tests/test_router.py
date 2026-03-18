"""
RxNorm MCP Server — Router / API Tests
=========================================
Tests the FastAPI endpoints using TestClient with a mocked connector.
"""

from __future__ import annotations

import pytest
import httpx
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi.testclient import TestClient
from app.connector import RxNormConnector
from app.router import set_connector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_RXCUI_RESPONSE = {
    "idGroup": {
        "name": "aspirin",
        "rxnormId": ["1191"]
    }
}

MOCK_ALLRELATED_RESPONSE = {
    "allRelatedGroup": {
        "conceptGroup": [
            {
                "tty": "IN",
                "conceptProperties": [
                    {"rxcui": "1191", "name": "Aspirin", "tty": "IN"}
                ]
            },
            {
                "tty": "BN",
                "conceptProperties": [
                    {"rxcui": "202433", "name": "Bayer", "tty": "BN"}
                ]
            }
        ]
    }
}


def _make_mock_transport(not_found_keyword: str = "notarealdrug"):
    """Create a mock transport simulating RxNorm endpoints."""

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if not_found_keyword in url_str:
            return httpx.Response(200, json={"idGroup": {"name": not_found_keyword}})
        
        if "rxcui.json" in url_str:
            return httpx.Response(200, json=MOCK_RXCUI_RESPONSE)
        elif "allrelated.json" in url_str:
            return httpx.Response(200, json=MOCK_ALLRELATED_RESPONSE)
            
        return httpx.Response(404)

    return httpx.MockTransport(mock_handler)


@pytest.fixture(autouse=True)
def mock_connector_setup():
    """Inject a configured RxNormConnector before each test."""
    connector = RxNormConnector(
        base_url="https://rxnav.nlm.nih.gov/REST",
        timeout=10.0,
        max_retries=1,
        rate_limit=100.0,
        server_version="1.0.0",
    )
    connector._client = httpx.AsyncClient(transport=_make_mock_transport())
    set_connector(connector)
    yield connector


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests — POST /query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    def test_successful_query(self, client):
        resp = client.post("/query", json={"drug_name": "aspirin"})
        assert resp.status_code == 200

        body = resp.json()
        assert body["status"] == "success"
        assert body["source"]["source_id"] == "rxnorm"
        assert body["data"]["identifiers"]["rxnorm_cui"] == "1191"
        assert body["data"]["results"]["ingredient_name"] == "Aspirin"
        assert "Bayer" in body["data"]["results"]["brand_names"]

    def test_query_invalid_payload(self, client):
        resp = client.post("/query", json={"drug_name": ""})
        assert resp.status_code == 422

    def test_query_not_found(self, client):
        resp = client.post("/query", json={"drug_name": "notarealdrug"})
        assert resp.status_code == 404

        body = resp.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "DRUG_NOT_FOUND"


# ---------------------------------------------------------------------------
# Tests — GET /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

        body = resp.json()
        assert body["source_id"] == "rxnorm"
        assert body["name"] == "RxNorm"
        assert body["version"] == "1.0.0"
