from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./scholarhive.db"
    gemini_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/gmail/callback"
    gmail_scopes: str = "https://www.googleapis.com/auth/gmail.readonly"
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    app_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    secret_key: str = "dev-change-me"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    railway_public_domain: str = ""
    upload_storage_path: str = "./uploads"

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def gmail_configured(self) -> bool:
        return bool(self.google_client_id.strip() and self.google_client_secret.strip())

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        for url in (self.frontend_url, self.backend_url, self.app_base_url):
            if url:
                origins.append(url.rstrip("/"))
        if self.railway_public_domain:
            domain = self.railway_public_domain.removeprefix("https://").removeprefix("http://")
            origins.append(f"https://{domain}")
        return list(dict.fromkeys(origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()
