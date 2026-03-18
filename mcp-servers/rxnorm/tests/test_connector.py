"""
RxNorm MCP Server — Connector Unit Tests
===========================================
Tests the RxNormConnector with mocked HTTP responses
simulating the two-step NLM API resolution process.
"""

from __future__ import annotations

import pytest
import httpx
import sys
import os

# Ensure shared library is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.schemas import MCPRequest
from shared.exceptions import DrugNotFoundError
from app.connector import RxNormConnector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_RXCUI_RESPONSE = {
    "idGroup": {
        "name": "aspirin",
        "rxnormId": ["1191"]
    }
}

MOCK_RXCUI_NOT_FOUND_RESPONSE = {
    "idGroup": {
        "name": "notarealdrug"
    }
}

MOCK_ALLRELATED_RESPONSE = {
    "allRelatedGroup": {
        "conceptGroup": [
            {
                "tty": "IN",
                "conceptProperties": [
                    {"rxcui": "1191", "name": "Aspirin", "synonym": "", "tty": "IN"}
                ]
            },
            {
                "tty": "BN",
                "conceptProperties": [
                    {"rxcui": "202433", "name": "Bayer", "synonym": "", "tty": "BN"},
                    {"rxcui": "202433", "name": "Ecotrin", "synonym": "", "tty": "BN"},
                    {"rxcui": "202433", "name": "Bayer", "synonym": "", "tty": "BN"}  # Duplicate
                ]
            },
            {
                "tty": "SY",
                "conceptProperties": [
                    {"name": "acetylsalicylic acid", "tty": "SY"},
                    {"name": "ASA", "tty": "SY"}
                ]
            }
        ]
    }
}


@pytest.fixture
def connector():
    """Create an RxNormConnector with test settings."""
    return RxNormConnector(
        base_url="https://rxnav.nlm.nih.gov/REST",
        timeout=10.0,
        max_retries=1,
        rate_limit=100.0,
        server_version="1.0.0-test",
    )


@pytest.fixture
def sample_request():
    """Create a standard test request."""
    return MCPRequest(drug_name="aspirin")


@pytest.fixture
def sample_request_with_rxcui():
    """Request with pre-resolved RxNorm CUI."""
    from shared.schemas import DrugIdentifiers
    return MCPRequest(
        drug_name="aspirin",
        identifiers=DrugIdentifiers(rxnorm_cui="1191"),
    )


# ---------------------------------------------------------------------------
# Tests — parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    @pytest.mark.asyncio
    async def test_successful_parse(self, connector, sample_request):
        result = await connector.parse_response(MOCK_ALLRELATED_RESPONSE, sample_request)

        assert result["drug_name"] == "aspirin"
        assert result["results"]["ingredient_name"] == "Aspirin"
        
        # Check brand names (duplicates removed, sorted logically by set)
        assert len(result["results"]["brand_names"]) == 2
        assert "Bayer" in result["results"]["brand_names"]
        assert "Ecotrin" in result["results"]["brand_names"]
        
        # Check synonyms
        assert len(result["results"]["synonyms"]) == 2
        assert "ASA" in result["results"]["synonyms"]
        assert "acetylsalicylic acid" in result["results"]["synonyms"]

    @pytest.mark.asyncio
    async def test_empty_concept_groups(self, connector, sample_request):
        raw = {"allRelatedGroup": {"conceptGroup": []}}
        result = await connector.parse_response(raw, sample_request)
        
        assert result["results"]["ingredient_name"] is None
        assert result["results"]["brand_names"] == []
        assert result["results"]["synonyms"] == []


# ---------------------------------------------------------------------------
# Tests — full query (mocked HTTP)
# ---------------------------------------------------------------------------

class TestFullQuery:
    @pytest.mark.asyncio
    async def test_query_two_step_resolution(self, connector, sample_request):
        """Test the two-step URL flow with mocked httpx."""

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            if "rxcui.json" in str(request.url):
                return httpx.Response(200, json=MOCK_RXCUI_RESPONSE)
            elif "allrelated.json" in str(request.url):
                return httpx.Response(200, json=MOCK_ALLRELATED_RESPONSE)
            return httpx.Response(404)

        connector._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

        result = await connector.query(sample_request)

        assert result.status == "success"
        assert result.source.source_id == "rxnorm"
        assert result.data.identifiers["rxnorm_cui"] == "1191"
        assert result.data.results["ingredient_name"] == "Aspirin"
        assert "Bayer" in result.data.results["brand_names"]

        await connector._client.aclose()

    @pytest.mark.asyncio
    async def test_query_skips_step1_if_cui_provided(self, connector, sample_request_with_rxcui):
        """Should jump straight to allrelated.json if CUI is already known."""

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert "rxcui.json" not in str(request.url), "Should not query resolution endpoint"
            return httpx.Response(200, json=MOCK_ALLRELATED_RESPONSE)

        connector._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

        result = await connector.query(sample_request_with_rxcui)

        assert result.data.identifiers["rxnorm_cui"] == "1191"
        assert result.data.results["ingredient_name"] == "Aspirin"

        await connector._client.aclose()

    @pytest.mark.asyncio
    async def test_query_drug_not_found(self, connector):
        """If step 1 returns no RxCUI, raise DrugNotFoundError."""

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=MOCK_RXCUI_NOT_FOUND_RESPONSE)

        connector._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

        request = MCPRequest(drug_name="notarealdrug")
        with pytest.raises(DrugNotFoundError):
            await connector.query(request)

        await connector._client.aclose()
