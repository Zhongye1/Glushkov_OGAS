from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ogas-rag-core"
    api_v1_prefix: str = "/api/v1"
    environment: str = "local"

    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379"

    embedding_model: str = "bge-m3"
    embedding_api_base: str | None = None
    embedding_api_key: str | None = None

    rerank_model: str | None = None
    llm_model: str | None = None
    llm_api_base: str | None = None
    llm_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
