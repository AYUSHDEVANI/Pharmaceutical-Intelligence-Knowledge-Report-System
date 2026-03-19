from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PUBMED_BASE_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    REQUEST_TIMEOUT: float = 15.0
    MAX_PAPERS: int = 100
    LOG_LEVEL: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
