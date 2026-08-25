from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "اتوماسیون فروشگاه حبوبات"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{(Path(__file__).resolve().parents[2] / 'store.db').as_posix()}"
    )
    secret_key: str = "change-this-secret-before-deployment"
    access_token_expire_minutes: int = 60 * 8
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
    ]
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"
    default_admin_full_name: str = "مدیر سیستم"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
