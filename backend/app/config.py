from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    session_secret: str = "local-development-secret-change-me"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_database_url: str | None = None
    allowed_origins: str = "http://localhost:5000"
    max_query_rows: int = 200
    query_timeout_ms: int = 3000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()