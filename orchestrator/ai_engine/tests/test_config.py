"""
PIKRS AI Engine Tests — Configuration verification
====================================================
Ensures strict validation of API keys and Environment variables.
"""

import os
from unittest.mock import patch
import pytest

from orchestrator.ai_engine.config import AIEngineSettings
from orchestrator.ai_engine.providers.groq_provider import GroqProvider

def test_settings_default_values():
    """Verify default configurations are populated correctly."""
    # Temporarily remove any actual env vars so we see raw defaults
    env_keys = ["GROQ_API_KEY", "OPENAI_API_KEY"]
    for key in env_keys:
        if key in os.environ:
            del os.environ[key]
            
    # Load fresh without mocking
    settings = AIEngineSettings()
    assert settings.GROQ_MODEL == "llama-3.1-70b-versatile"
    assert settings.LLM_TIMEOUT == 30
    assert settings.GROQ_API_KEY is None

def test_groq_provider_loads_settings():
    """Ensure the Provider reads from the active configurations."""
    # Mock settings so they are populated
    mock_settings = AIEngineSettings(GROQ_API_KEY="test_key", GROQ_MODEL="test-model")
    
    with patch("orchestrator.ai_engine.providers.groq_provider.settings", mock_settings):
        provider = GroqProvider()
        assert provider.api_key == "test_key"
        assert provider.model == "test-model"

def test_groq_provider_raises_error_if_key_missing():
    """If no API key is present in kwargs or settings, the Provider strictly fails instantiation."""
    mock_settings = AIEngineSettings(GROQ_API_KEY=None)
    
    with patch("orchestrator.ai_engine.providers.groq_provider.settings", mock_settings):
        with pytest.raises(ValueError, match="GROQ_API_KEY is missing"):
            # Attempting to initialize the empty provider raises instantly
            GroqProvider()
