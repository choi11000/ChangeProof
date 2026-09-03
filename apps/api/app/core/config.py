from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ChangeProof API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://changeproof:changeproof@localhost:5432/changeproof"
    sandbox_database_url: str = (
        "postgresql+psycopg://changeproof:changeproof@localhost:5433/changeproof_sandbox"
    )
    github_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
