"""Run, request, and provider metadata models."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from marketing_agent.domain.models.keyword import (
    KeywordCandidate,
    KeywordCluster,
    KeywordIntelligence,
)
from marketing_agent.domain.models.marketplace import MarketplaceSnapshot
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.provider import ProviderRunTelemetry

SCHEMA_VERSION = "2026-06-26.live_keyword_enrichment.v1"


def _provider_run_telemetry_list() -> list[ProviderRunTelemetry]:
    return []


class StageState(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    WARNING = "warning"
    FAILED = "failed"


class StageStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    state: StageState
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    message: str | None = None


class ImageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1)
    filename: str
    mime_type: str
    content_hash: str
    byte_size: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class ProductAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    brand: str | None = None
    market: str | None = None
    language: str | None = None
    category_hint: str | None = None
    target_audience_hint: str | None = None
    include_debug: bool = False


class ProviderUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ProviderMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    request_id: str | None = None
    latency_ms: int | None = None
    prompt_version: str
    usage: ProviderUsage | None = None


class PerceptionRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    run_id: str
    analysis_run_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    request: ProductAnalysisRequest
    images: list[ImageInput]
    product_profile: ProductProfile
    marketplace_snapshot: MarketplaceSnapshot
    keyword_candidates: list[KeywordCandidate]
    keyword_clusters: list[KeywordCluster]
    keyword_intelligence: KeywordIntelligence = Field(default_factory=KeywordIntelligence)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    stage_statuses: list[StageStatus]
    metadata: ProviderMetadata
    provider_runs: list[ProviderRunTelemetry] = Field(default_factory=_provider_run_telemetry_list)
