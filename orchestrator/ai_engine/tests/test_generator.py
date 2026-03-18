"""
PIKRS AI Engine — Unit Tests
==============================
Verifies LLM JSON parsing, prompt rendering, and fallback error handling.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch

from orchestrator.models import DrugProfile, ChemicalProperties, RegulatoryInformation, DrugIdentifiers
from orchestrator.ai_engine.models import DrugIntelligenceReport
from orchestrator.ai_engine.providers.base_provider import LLMProvider
from orchestrator.ai_engine.generator import generate_report
from orchestrator.ai_engine.service import generate_drug_intelligence

class MockProvider(LLMProvider):
    """A deterministic mock LLM returning pristine JSON strings."""
    def __init__(self, should_fail: bool = False, bad_json: bool = False):
        self.should_fail = should_fail
        self.bad_json = bad_json
        
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.should_fail:
            raise ValueError("Rate Limit Exceeded")
            
        if self.bad_json:
            return "This is a hallucinated string not JSON!"
            
        return json.dumps({
            "drug_name": "IGNORED", # Generator overrides this to guarantee accuracy
            "overview": "This is a test overview.",
            "chemical_summary": "Formula C-Test",
            "therapeutic_indications": "Testing Indications",
            "dosage_guidelines": "1 pill",
            "safety_summary": "Do not overdose",
            "brand_names": ["TestBrand"],
            "key_identifiers": {"rxnorm": "123"},
            "sources": [] # Generator overrides this too
        })

@pytest.fixture
def mock_profile() -> DrugProfile:
    return DrugProfile(
        drug_name="aspirin",
        chemical_properties=ChemicalProperties(molecular_formula="C9H8O4"),
        regulatory_information=RegulatoryInformation(warnings="Stomach bleeding"),
        identifiers=DrugIdentifiers(rxnorm_cui="1191"),
        brand_names=["Bayer"],
        synonyms=[],
        sources=["pubchem", "rxnorm", "openfda"]
    )

@pytest.mark.asyncio
async def test_successful_generation_parses_schema(mock_profile):
    """Validates the exact formatting and hard-coded fallbacks of the generator."""
    provider = MockProvider()
    
    report = await generate_report(mock_profile, provider=provider)
    
    assert isinstance(report, DrugIntelligenceReport)
    # Forced accuracy from the source profile
    assert report.drug_name == "ASPIRIN"
    assert report.sources == ["pubchem", "rxnorm", "openfda"]
    # Synthesized from the fake LLM
    assert report.overview == "This is a test overview."
    assert report.chemical_summary == "Formula C-Test"

@pytest.mark.asyncio
async def test_generator_catches_invalid_json(mock_profile):
    """Test that a broken JSON output from the LLM raises a clear ValueError."""
    provider = MockProvider(bad_json=True)
    
    with pytest.raises(ValueError, match="Failed to parse LLM generation"):
        await generate_report(mock_profile, provider=provider)


@pytest.mark.asyncio
@patch("orchestrator.ai_engine.service.generate_drug_profile")
@patch("orchestrator.ai_engine.service.generate_report")
async def test_pipeline_fallback_on_llm_failure(mock_generate_report, mock_generate_profile, mock_profile):
    """
    If the LLM raises an error (e.g., API key invalid/billing/rate limit),
    verify the Service catches it and returns the original `DrugProfile`.
    """
    mock_generate_profile.return_value = mock_profile
    mock_generate_report.side_effect = Exception("OpenAI API Key Missing")
    
    # Run the main pipeline
    result = await generate_drug_intelligence("aspirin")
    
    # It should seamlessly downgrade back to the raw dict model
    assert isinstance(result, DrugProfile)
    assert result.drug_name == "aspirin"
    assert "AI_ENGINE_ERROR" in result.regulatory_information.warnings
