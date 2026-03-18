from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    CLINICALTRIALS_BASE_URL: str = "https://clinicaltrials.gov/api/v2"

    REQUEST_TIMEOUT: float = 15.0
    MAX_RETRIES: int = 3
    RATE_LIMIT_PER_SECOND: float = 5.0

    SERVER_VERSION: str = "1.0.0"

    HOST: str = "0.0.0.0"
    PORT: int = 8103
    LOG_LEVEL: str = "INFO"

    MAX_BODY_BYTES: int = 1 * 1024 * 1024

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


settings = Settings()