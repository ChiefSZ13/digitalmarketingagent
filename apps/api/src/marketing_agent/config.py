"""Typed application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_log_level: str = "INFO"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    perception_provider: str = "mock"
    marketplace_data_provider: str = "mock"
    serpapi_api_key: str | None = None
    serpapi_location: str | None = "United States"
    marketplace_timeout_seconds: float = 20.0
    app_access_key: str | None = None
    rate_limit_requests: int = Field(default=20, ge=0)
    rate_limit_window_seconds: int = Field(default=3600, gt=0)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    perception_timeout_seconds: float = 30.0
    max_image_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    max_image_pixels: int = Field(default=12_000_000, gt=0)
    max_images_per_request: int = Field(default=5, gt=0, le=5)
    artifact_dir: Path = Path("artifacts/runs")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
