"""Domain-facing protocol for live keyword metric providers."""

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from marketing_agent.domain.models.keyword import (
    KeywordCompetition,
    KeywordMonthlyMetric,
)
from marketing_agent.domain.models.provider import ProviderRunTelemetry


def _keyword_monthly_metric_list() -> list[KeywordMonthlyMetric]:
    return []


def _string_list() -> list[str]:
    return []


class KeywordProviderRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keyword: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    provider_record_id: str | None = None
    average_monthly_searches: int | None = Field(default=None, ge=0)
    competition: KeywordCompetition | None = None
    competition_index: float | None = Field(default=None, ge=0.0, le=1.0)
    cpc_low: float | None = Field(default=None, ge=0.0)
    cpc_high: float | None = Field(default=None, ge=0.0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    monthly_history: list[KeywordMonthlyMetric] = Field(
        default_factory=_keyword_monthly_metric_list
    )
    related_terms: list[str] = Field(default_factory=_string_list)
    source_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


@dataclass(frozen=True)
class KeywordEnrichmentRequest:
    keywords: list[str]
    market: str
    language: str
    currency: str
    max_keywords: int
    correlation_id: str = field(default_factory=lambda: f"kw_{uuid4().hex}")


@dataclass(frozen=True)
class KeywordEnrichmentProviderResult:
    records: list[KeywordProviderRecord]
    warnings: list[str]
    telemetry: ProviderRunTelemetry


class KeywordMetricsProviderError(RuntimeError):
    """Raised when a keyword metrics provider cannot return normalized data."""


class KeywordMetricsProvider(Protocol):
    async def enrich(self, request: KeywordEnrichmentRequest) -> KeywordEnrichmentProviderResult:
        """Fetch and normalize keyword metric records."""
        raise NotImplementedError
