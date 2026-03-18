"""
OpenFDA MCP Server — Connector Unit Tests
===========================================
Tests the OpenFDAConnector with mocked HTTP responses,
simulating the FDA label extraction logic.
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
from app.connector import OpenFDAConnector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_OPENFDA_RESPONSE = {
    "meta": {
        "disclaimer": "Do not rely on openFDA to make decisions.",
        "terms": "https://open.fda.gov/terms/",
        "license": "https://creativecommons.org/publicdomain/zero/1.0/",
        "last_updated": "2023-10-01",
        "results": {
            "skip": 0,
            "limit": 1,
            "total": 50
        }
    },
    "results": [
        {
            "effective_time": "20220511",
            "indications_and_usage": ["For the relief of minor aches and pains."],
            "dosage_and_administration": ["Take 1 or 2 tablets every 4 hours."],
            "warnings": ["Reye's syndrome warning."],
            "boxed_warning": ["WARNING: BLEEDING RISK"],
            "contraindications": ["Do not use if allergic to aspirin."],
            "adverse_reactions": ["Stomach pain, heartburn."],
            "drug_interactions": ["Blood thinners."]
        }
    ]
}

MOCK_OPENFDA_NOT_FOUND_RESPONSE = {
    "error": {
        "code": "NOT_FOUND",
        "message": "No matches found!"
    }
}

MOCK_OPENFDA_EMPTY_RESULTS = {
    "meta": {"results": {"total": 0}},
    "results": []
}


@pytest.fixture
def connector():
    """Create an OpenFDAConnector with test settings."""
    return OpenFDAConnector(
        base_url="https://api.fda.gov/drug",
        timeout=10.0,
        max_retries=1,
        rate_limit=100.0,
        server_version="1.0.0-test",
    )


@pytest.fixture
def sample_request():
    """Create a standard test request."""
    return MCPRequest(drug_name="aspirin")


# ---------------------------------------------------------------------------
# Tests — parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    @pytest.mark.asyncio
    async def test_successful_parse(self, connector, sample_request):
        result = await connector.parse_response(MOCK_OPENFDA_RESPONSE, sample_request)

        assert result["drug_name"] == "aspirin"
        
        # Check assertions for all 6 extracted fields
        assert result["results"]["indications"] == "For the relief of minor aches and pains."
        assert result["results"]["dosage"] == "Take 1 or 2 tablets every 4 hours."
        
        # Should prefer boxed_warning over general warnings
        assert result["results"]["warnings"] == "WARNING: BLEEDING RISK"
        
        assert result["results"]["contraindications"] == "Do not use if allergic to aspirin."
        assert result["results"]["adverse_reactions"] == "Stomach pain, heartburn."
        assert result["results"]["drug_interactions"] == "Blood thinners."

    @pytest.mark.asyncio
    async def test_fallback_to_general_warnings(self, connector, sample_request):
        # Create a deep copy to avoid mutating the class-level dict
        import copy
        response_copy = copy.deepcopy(MOCK_OPENFDA_RESPONSE)
        # Remove boxed warning
        if "boxed_warning" in response_copy["results"][0]:
            del response_copy["results"][0]["boxed_warning"]
        
        result = await connector.parse_response(response_copy, sample_request)
        
        # Should now use the general warnings field
        assert result["results"]["warnings"] == "Reye's syndrome warning."

    @pytest.mark.asyncio
    async def test_empty_results_raises_not_found(self, connector, sample_request):
        with pytest.raises(DrugNotFoundError):
            await connector.parse_response(MOCK_OPENFDA_EMPTY_RESULTS, sample_request)

    @pytest.mark.asyncio
    async def test_error_code_raises_not_found(self, connector, sample_request):
        with pytest.raises(DrugNotFoundError):
            await connector.parse_response(MOCK_OPENFDA_NOT_FOUND_RESPONSE, sample_request)


# ---------------------------------------------------------------------------
# Tests — full query (mocked HTTP)
# ---------------------------------------------------------------------------

class TestFullQuery:
    @pytest.mark.asyncio
    async def test_query_fetches_and_envelopes(self, connector, sample_request):
        """Test the full URL fetch and envelope structure with mocked httpx."""

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert "label.json" in str(request.url)
            assert "search=openfda.generic_name:aspirin" in str(request.url)
            assert "limit=1" in str(request.url)
            return httpx.Response(200, json=MOCK_OPENFDA_RESPONSE)

        connector._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

        result = await connector.query(sample_request)

        assert result.status == "success"
        assert result.source.source_id == "openfda"
        assert result.data.drug_name == "aspirin"
        assert result.data.results["dosage"] == "Take 1 or 2 tablets every 4 hours."

        await connector._client.aclose()
