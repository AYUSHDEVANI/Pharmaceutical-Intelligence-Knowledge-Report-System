from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    KEGG_BASE_URL: str = "https://rest.kegg.jp"
    REQUEST_TIMEOUT: float = 15.0
    LOG_LEVEL: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
