"""Typed application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ALLOWED_ORIGINS = ",".join(
    (
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:3100",
        "http://localhost:3100",
        "http://127.0.0.1:3101",
        "http://localhost:3101",
    )
)


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
    cors_allowed_origins: str = DEFAULT_CORS_ALLOWED_ORIGINS
    perception_provider: str = "mock"
    marketplace_data_provider: str = "mock"
    serpapi_api_key: str | None = None
    serpapi_location: str | None = "United States"
    marketplace_timeout_seconds: float = 20.0
    keyword_provider: str = "mock"
    keyword_provider_api_key: str | None = None
    dataforseo_login: str | None = None
    dataforseo_password: str | None = None
    keyword_provider_timeout_seconds: float = 20.0
    keyword_provider_retries: int = Field(default=2, ge=0, le=5)
    keyword_provider_cache_ttl_seconds: int = Field(default=86_400, ge=0)
    keyword_provider_batch_size: int = Field(default=20, gt=0, le=100)
    keyword_provider_max_keywords: int = Field(default=40, gt=0, le=200)
    keyword_provider_country: str = "US"
    keyword_provider_location_name: str = "United States"
    keyword_provider_language: str = "en"
    keyword_provider_language_name: str = "English"
    keyword_provider_currency: str = "USD"
    keyword_scoring_policy_version: str = "keyword-opportunity-v1"
    keyword_matching_policy_version: str = "keyword-provider-match-v1"
    keyword_trend_policy_version: str = "keyword-trend-v1"
    product_matcher_version: str = "product-matcher-v2"
    product_match_exact_threshold: float = Field(default=0.93, ge=0.0, le=1.0)
    product_match_probable_threshold: float = Field(default=0.84, ge=0.0, le=1.0)
    product_match_uncertain_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    product_match_require_brand: bool = False
    product_match_color_strict: bool = False
    product_match_exclude_refurbished: bool = True
    product_match_exclude_used: bool = True
    ambiguous_match_reviewer_enabled: bool = False
    ambiguous_match_reviewer_provider: str = "mock"
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
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketing_agent"
    database_echo: bool = False
    database_pool_size: int = Field(default=5, gt=0)
    database_max_overflow: int = Field(default=10, ge=0)
    persistence_enabled: bool = False
    admin_db_inspector_enabled: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
