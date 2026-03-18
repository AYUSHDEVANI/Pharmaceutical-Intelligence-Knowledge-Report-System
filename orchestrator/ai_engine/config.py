"""
PIKRS AI Engine — Configuration
=================================
Environment-based configuration driven by Pydantic Settings.
"""

from typing import Optional
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class AIEngineSettings(BaseSettings):
    """
    Configuration for the LLM providers (Groq/OpenAI).
    Validates that necessary keys are provided in the environment.
    """
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    LLM_TIMEOUT: int = 30

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = AIEngineSettings()
