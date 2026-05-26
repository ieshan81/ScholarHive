from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_PUBLIC_APP_URL = "https://web-production-586ef.up.railway.app"
DEFAULT_GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required in production (Railway injects DATABASE_URL)
    database_url: str = "sqlite:///./scholarhive.db"
    secret_key: str = "dev-change-me"
    environment: str = "development"

    # Active integrations (optional at boot)
    gemini_api_key: str = ""
    tavily_api_key: str = ""

    # Future optional
    google_client_id: str = ""
    google_client_secret: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    # Code defaults (not required as Railway env vars)
    public_app_url: str = DEFAULT_PUBLIC_APP_URL
    log_level: str = "INFO"
    upload_storage_driver: str = "railway_volume"
    upload_storage_path: str = "/data/uploads"
    max_upload_mb: int = 20
    enable_demo_data: bool = False
    trusted_only_mode: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def should_seed_demo(self) -> bool:
        return (
            not self.is_production
            and self.enable_demo_data
        )

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def tavily_configured(self) -> bool:
        return bool(self.tavily_api_key.strip())

    @property
    def gmail_configured(self) -> bool:
        return bool(self.google_client_id.strip() and self.google_client_secret.strip())

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token.strip())

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.public_app_url.rstrip('/')}/api/gmail/callback"

    @property
    def gmail_scopes(self) -> str:
        return DEFAULT_GMAIL_SCOPE

    @property
    def cors_origin_list(self) -> list[str]:
        return list(
            dict.fromkeys(
                [
                    self.public_app_url.rstrip("/"),
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "http://localhost:8000",
                ]
            )
        )

    @property
    def storage_writable(self) -> bool:
        from pathlib import Path

        path = Path(self.upload_storage_path)
        try:
            path.mkdir(parents=True, exist_ok=True)
            test = path / ".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return True
        except OSError:
            return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
