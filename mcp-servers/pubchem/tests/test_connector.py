"""
PubChem MCP Server — Connector Unit Tests
===========================================
Tests the PubChemConnector with mocked HTTP responses.
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
from app.connector import PubChemConnector


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


@pytest.fixture
def connector():
    """Create a PubChemConnector with test settings."""
    return PubChemConnector(
        base_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
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
def sample_request_with_cid():
    """Request with pre-resolved CID."""
    from shared.schemas import DrugIdentifiers
    return MCPRequest(
        drug_name="aspirin",
        identifiers=DrugIdentifiers(pubchem_cid=2244),
    )


# ---------------------------------------------------------------------------
# Tests — build_request_url
# ---------------------------------------------------------------------------

class TestBuildRequestUrl:
    @pytest.mark.asyncio
    async def test_url_by_drug_name(self, connector, sample_request):
        url = await connector.build_request_url(sample_request)
        assert "/compound/name/aspirin/property/" in url
        assert "MolecularFormula" in url
        assert "MolecularWeight" in url

    @pytest.mark.asyncio
    async def test_url_by_cid(self, connector, sample_request_with_cid):
        url = await connector.build_request_url(sample_request_with_cid)
        assert "/compound/cid/2244/property/" in url

    @pytest.mark.asyncio
    async def test_url_encodes_special_characters(self, connector):
        request = MCPRequest(drug_name="acetylsalicylic acid")
        url = await connector.build_request_url(request)
        assert "acetylsalicylic%20acid" in url


# ---------------------------------------------------------------------------
# Tests — parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    @pytest.mark.asyncio
    async def test_successful_parse(self, connector, sample_request):
        result = await connector.parse_response(MOCK_PUBCHEM_RESPONSE, sample_request)

        assert result["drug_name"] == "aspirin"
        assert result["identifiers"]["pubchem_cid"] == 2244
        assert result["results"]["molecular_formula"] == "C9H8O4"
        assert result["results"]["molecular_weight"] == 180.16
        assert result["results"]["iupac_name"] == "2-acetoxybenzoic acid"
        assert result["results"]["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(O)=O"
        assert result["results"]["inchi"] is not None
        assert result["results"]["inchi_key"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"

    @pytest.mark.asyncio
    async def test_empty_properties_raises(self, connector, sample_request):
        raw = {"PropertyTable": {"Properties": []}}
        with pytest.raises(DrugNotFoundError):
            await connector.parse_response(raw, sample_request)

    @pytest.mark.asyncio
    async def test_missing_property_table_raises(self, connector, sample_request):
        raw = {"Fault": {"Code": "PUGREST.NotFound"}}
        with pytest.raises(DrugNotFoundError):
            await connector.parse_response(raw, sample_request)


# ---------------------------------------------------------------------------
# Tests — full query (mocked HTTP)
# ---------------------------------------------------------------------------

class TestFullQuery:
    @pytest.mark.asyncio
    async def test_query_returns_mcp_response(self, connector, sample_request):
        """Test the full query pipeline with a mocked httpx client."""

        # Create a mock transport
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=MOCK_PUBCHEM_RESPONSE)

        connector._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

        result = await connector.query(sample_request)

        assert result.status == "success"
        assert result.source.source_id == "pubchem"
        assert result.source.name == "PubChem"
        assert result.data.results["molecular_formula"] == "C9H8O4"
        assert result.data.results["molecular_weight"] == 180.16
        assert result.data.identifiers["pubchem_cid"] == 2244
        assert result.metadata.response_time_ms > 0

        await connector._client.aclose()

    @pytest.mark.asyncio
    async def test_query_with_field_filter(self, connector):
        """Only requested fields should appear in results."""

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=MOCK_PUBCHEM_RESPONSE)

        connector._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

        request = MCPRequest(
            drug_name="aspirin",
            fields=["molecular_formula", "molecular_weight"],
        )
        result = await connector.query(request)

        assert "molecular_formula" in result.data.results
        assert "molecular_weight" in result.data.results
        assert "iupac_name" not in result.data.results

        await connector._client.aclose()

    @pytest.mark.asyncio
    async def test_query_404_raises_drug_not_found(self, connector, sample_request):
        """Upstream 404 should raise DrugNotFoundError."""

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"Fault": {"Code": "PUGREST.NotFound"}})

        connector._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

        with pytest.raises(DrugNotFoundError):
            await connector.query(sample_request)

        await connector._client.aclose()
