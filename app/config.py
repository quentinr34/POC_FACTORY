from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Quote Catcher"
    environment: str = "local"

    anthropic_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-latest"

    gcp_project_id: str = ""
    firestore_collection: str = "qualifications"

    score_weights_clarity: float = 0.30
    score_weights_budget: float = 0.25
    score_weights_urgency: float = 0.20
    score_weights_offer_fit: float = 0.25


@lru_cache
def get_settings() -> Settings:
    return Settings()
