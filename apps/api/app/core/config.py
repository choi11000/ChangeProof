from functools import lru_cache

from pydantic import model_validator
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
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_max_output_tokens: int = 1200
    max_ai_evidence: int = 30
    max_ai_changes: int = 50
    max_evidence_excerpt_chars: int = 240
    max_ai_warnings: int = 10
    max_warning_chars: int = 200
    ai_cache_max_entries: int = 256
    ai_cache_ttl_seconds: int = 3600
    analysis_rate_limit: int = 10
    experiment_rate_limit: int = 6
    proof_rate_limit: int = 3
    rate_limit_window_seconds: int = 60
    rate_limit_max_clients: int = 4096
    trust_proxy_headers: bool = False
    max_concurrent_sandbox_runs: int = 2
    github_public_repositories_only: bool = True
    cors_allowed_origins: str = "http://localhost:3000"
    api_docs_enabled: bool = True
    require_sandbox_tests: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_safe_deployment(self) -> "Settings":
        if "*" in self.cors_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS cannot contain a wildcard")
        positive_fields = (
            "openai_max_output_tokens",
            "max_ai_evidence",
            "max_ai_changes",
            "max_evidence_excerpt_chars",
            "max_ai_warnings",
            "max_warning_chars",
            "ai_cache_max_entries",
            "ai_cache_ttl_seconds",
            "analysis_rate_limit",
            "experiment_rate_limit",
            "proof_rate_limit",
            "rate_limit_window_seconds",
            "rate_limit_max_clients",
            "max_concurrent_sandbox_runs",
        )
        if any(getattr(self, name) <= 0 for name in positive_fields):
            raise ValueError("Runtime guard limits must be positive")
        if self.app_env.lower() == "production":
            if not self.cors_origins:
                raise ValueError("Production requires CORS_ALLOWED_ORIGINS")
            if not self.github_public_repositories_only:
                raise ValueError("Production requires public-repository-only GitHub access")
            if not self.sandbox_database_url.strip():
                raise ValueError("Production requires SANDBOX_DATABASE_URL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
