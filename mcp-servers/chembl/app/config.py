from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    CHEMBL_BASE_URL: str = "https://www.ebi.ac.uk/chembl/api/data"

    REQUEST_TIMEOUT: float = 15.0
    MAX_RETRIES: int = 3
    RATE_LIMIT_PER_SECOND: float = 3.0

    SERVER_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8105
    LOG_LEVEL: str = "INFO"

    MAX_BODY_BYTES: int = 1 * 1024 * 1024

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()