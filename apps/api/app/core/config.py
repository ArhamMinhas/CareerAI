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

    # Supabase Auth (docs/SECURITY.md)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

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
            if not self.supabase_jwt_secret:
                raise ValueError("SUPABASE_JWT_SECRET must be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
