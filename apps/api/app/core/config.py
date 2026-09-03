from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app configuration. Fails fast at startup if a required var is missing
    (docs/DEPLOYMENT.md §7) — real environment variables always win over the .env file,
    which is only a local-dev fallback (see apps/api/README.md)."""

    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"

    # Database (docs/DATABASE.md)
    database_url: str = Field(
        default="postgresql+asyncpg://careerai:careerai@localhost:5432/careerai"
    )
    database_url_sync: str = Field(default="postgresql://careerai:careerai@localhost:5432/careerai")

    # Redis (cache + Celery broker/result backend)
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Supabase Auth (docs/SECURITY.md). `supabase_jwt_secret` only applies to legacy
    # projects using the shared HS256 secret; current projects use asymmetric "JWT Signing
    # Keys" verified via JWKS (needs only `supabase_url`) — see app/core/security.py.
    supabase_url: str = ""
    supabase_secret_key: str = ""
    supabase_jwt_secret: str = ""

    # Object storage (docs/DATABASE.md, docs/DEPLOYMENT.md §5 — Supabase Storage by default)
    storage_bucket: str = ""

    # AI / LLM providers (docs/AI_ARCHITECTURE.md). `openai_api_key`/`llm_model_reasoning` are
    # used directly by app/ai/resume_extraction.py since Phase 4 — a narrow stopgap ahead of
    # the full provider abstraction Phase 5 formally owns (see that module's docstring).
    # `gemini_api_key`/`llm_provider`/`llm_model_default` stay unused until Phase 5.
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_provider: str = "openai"
    llm_model_default: str = "gpt-4o-mini"
    llm_model_reasoning: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # Job ingestion — Adzuna API (docs/ROADMAP.md Phase 7). Free-tier developer account at
    # https://developer.adzuna.com; both must be set for app/scripts/ingest_adzuna_jobs.py to
    # pull real postings. Left blank, that script fails fast with a clear message rather than
    # silently ingesting nothing.
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    # Trained ML models (docs/ML_PIPELINE.md §3, §6 — Phase 8). Each is loaded from
    # ml/models/<name>/<version>/model.joblib by app/ml/registry.py — rollback is a config
    # change, not a redeploy of training code. Missing artifact/wrong version degrades
    # gracefully (app/ml/registry.py returns None), never a 500.
    model_version_job_suitability: str = "1.0.0"
    model_version_career_recommendation: str = "1.0.0"
    model_version_skill_clustering: str = "1.0.0"
    model_version_salary_prediction: str = "1.0.0"
    model_version_job_category: str = "1.0.0"
    model_version_skill_demand_forecast: str = "1.0.0"

    # CORS
    cors_allowed_origins: str = "http://localhost:3000"

    # Security
    secret_key: str = "dev-only-insecure-secret-change-me"
    rate_limit_default_per_minute: int = 120
    rate_limit_ai_per_minute: int = 20

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.is_production:
            if self.secret_key == "dev-only-insecure-secret-change-me":
                raise ValueError("SECRET_KEY must be set to a real value in production")
            # Either verification path is valid — see app/core/security.py — but at least
            # one must be configured, or every request would 503.
            if not self.supabase_jwt_secret and not self.supabase_url:
                raise ValueError("SUPABASE_URL or SUPABASE_JWT_SECRET must be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
