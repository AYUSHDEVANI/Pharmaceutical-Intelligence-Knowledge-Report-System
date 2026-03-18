"""
PubChem MCP Server — Router / API Tests
=========================================
Tests the FastAPI endpoints using TestClient with mocked connector.
"""

from __future__ import annotations

import pytest
import httpx
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi.testclient import TestClient
from app.connector import PubChemConnector
from app.router import set_connector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_PUBCHEM_RESPONSE = {
    "PropertyTable": {
        "Properties": [
            {
                "CID": 2244,
                "MolecularFormula": "C9H8O4",
                "MolecularWeight": 180.16,
                "IUPACName": "2-acetoxybenzoic acid",
                "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(O)=O",
                "InChI": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
                "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            }
        ]
    }
}


def _make_mock_transport(not_found_keyword: str = "notarealdrug"):
    """Create a mock transport that returns 404 for a specific drug name."""

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        if not_found_keyword in str(request.url):
            return httpx.Response(404, json={"Fault": {"Code": "PUGREST.NotFound"}})
        return httpx.Response(200, json=MOCK_PUBCHEM_RESPONSE)

    return httpx.MockTransport(mock_handler)


@pytest.fixture(autouse=True)
def mock_connector_setup():
    """
    Create a PubChemConnector with a mocked httpx client and inject it
    into the router before each test.
    """
    connector = PubChemConnector(
        base_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
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
        assert body["source"]["source_id"] == "pubchem"
        assert body["data"]["results"]["molecular_formula"] == "C9H8O4"
        assert body["data"]["results"]["molecular_weight"] == 180.16
        assert body["metadata"]["request_id"] is not None
        assert body["metadata"]["response_time_ms"] >= 0

    def test_query_with_field_filter(self, client):
        resp = client.post(
            "/query",
            json={"drug_name": "aspirin", "fields": ["molecular_formula"]},
        )
        assert resp.status_code == 200

        results = resp.json()["data"]["results"]
        assert "molecular_formula" in results
        assert "iupac_name" not in results

    def test_query_empty_drug_name_returns_422(self, client):
        resp = client.post("/query", json={"drug_name": ""})
        assert resp.status_code == 422

    def test_query_invalid_characters_returns_422(self, client):
        resp = client.post("/query", json={"drug_name": "aspirin; DROP TABLE"})
        assert resp.status_code == 422

    def test_query_not_found(self, client):
        resp = client.post("/query", json={"drug_name": "notarealdrug"})
        assert resp.status_code == 404

        body = resp.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "DRUG_NOT_FOUND"

    def test_request_id_echoed(self, client):
        resp = client.post(
            "/query",
            json={"drug_name": "aspirin", "request_id": "test-trace-id-123"},
        )
        assert resp.status_code == 200
        assert resp.json()["metadata"]["request_id"] == "test-trace-id-123"


# ---------------------------------------------------------------------------
# Tests — GET /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

        body = resp.json()
        assert body["source_id"] == "pubchem"
        assert body["name"] == "PubChem"
        assert body["version"] == "1.0.0"
        assert "uptime_seconds" in body
        assert "upstream_reachable" in body


# ---------------------------------------------------------------------------
# Tests — response headers
# ---------------------------------------------------------------------------

class TestResponseHeaders:
    def test_request_id_header(self, client):
        resp = client.post(
            "/query",
            json={"drug_name": "aspirin"},
            headers={"X-Request-ID": "custom-header-id"},
        )
        assert resp.headers.get("X-Request-ID") == "custom-header-id"

    def test_response_time_header(self, client):
        resp = client.post("/query", json={"drug_name": "aspirin"})
        assert "X-Response-Time-Ms" in resp.headers
