"""Provider-run telemetry shared across external data adapters."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderRunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"


class CacheStatus(StrEnum):
    HIT = "hit"
    MISS = "miss"
    PARTIAL_HIT = "partial_hit"
    BYPASS = "bypass"


class ProviderRunTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime
    latency_ms: int = Field(ge=0)
    status: ProviderRunStatus
    result_count: int = Field(default=0, ge=0)
    cache_status: CacheStatus = CacheStatus.BYPASS
    cost_micros: int | None = Field(default=None, ge=0)
    error_category: str | None = None
    correlation_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_time_order(self) -> "ProviderRunTelemetry":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be after started_at")
        return self


def build_provider_telemetry(
    *,
    provider: str,
    operation: str,
    started_at: datetime,
    status: ProviderRunStatus,
    result_count: int,
    cache_status: CacheStatus,
    correlation_id: str,
    cost_micros: int | None = None,
    error_category: str | None = None,
) -> ProviderRunTelemetry:
    completed_at = datetime.now(UTC)
    latency_ms = int((completed_at - started_at).total_seconds() * 1000)
    return ProviderRunTelemetry(
        provider=provider,
        operation=operation,
        started_at=started_at,
        completed_at=completed_at,
        latency_ms=max(0, latency_ms),
        status=status,
        result_count=result_count,
        cache_status=cache_status,
        cost_micros=cost_micros,
        error_category=error_category,
        correlation_id=correlation_id,
    )
