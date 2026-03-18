"""
RxNorm MCP Server — Configuration
====================================
Environment-driven settings for the RxNorm connector.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """RxNorm MCP server configuration, loaded from environment / .env file."""

    # RxNorm upstream
    RXNORM_BASE_URL: str = "https://rxnav.nlm.nih.gov/REST"
    REQUEST_TIMEOUT: float = 15.0
    MAX_RETRIES: int = 3
    RATE_LIMIT_PER_SECOND: float = 20.0  # NLM allows 20 req/sec per IP

    # Server
    SERVER_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8101
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
