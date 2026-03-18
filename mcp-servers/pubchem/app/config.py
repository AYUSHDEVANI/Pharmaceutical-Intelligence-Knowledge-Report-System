"""
PubChem MCP Server — Configuration
====================================
Environment-driven settings for the PubChem connector.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """PubChem MCP server configuration, loaded from environment / .env file."""

    # PubChem upstream
    PUBCHEM_BASE_URL: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    REQUEST_TIMEOUT: float = 15.0
    MAX_RETRIES: int = 3
    RATE_LIMIT_PER_SECOND: float = 5.0

    # Server
    SERVER_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8100
    LOG_LEVEL: str = "INFO"

    # Security
    MAX_BODY_BYTES: int = 1 * 1024 * 1024  # 1 MB

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Singleton settings instance
settings = Settings()
