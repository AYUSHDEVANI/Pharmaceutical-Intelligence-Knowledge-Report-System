from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DAILMED_BASE_URL: str = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
    REQUEST_TIMEOUT: float = 15.0
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()