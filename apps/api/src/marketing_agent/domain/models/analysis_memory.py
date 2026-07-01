"""Read models for persisted product-intelligence memory."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from marketing_agent.domain.models.keyword import KeywordCandidate, KeywordIntelligence
from marketing_agent.domain.models.marketplace import (
    MarketplaceReviewDecision,
    MarketplaceSnapshot,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.run import PerceptionRun


def _keyword_candidate_list() -> list[KeywordCandidate]:
    return []


def _provider_run_record_list() -> list[ProviderRunRecord]:
    return []


def _marketplace_observation_record_list() -> list[MarketplaceObservationRecord]:
    return []


def _product_match_result_record_list() -> list[ProductMatchResultRecordView]:
    return []


def _manual_match_override_record_list() -> list[ManualMatchOverrideRecordView]:
    return []


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    run_id: str
    created_at: datetime
    completed_at: datetime | None = None
    product_name: str | None = None
    brand: str | None = None
    status: str
    marketplace_observation_count: int = Field(ge=0)
    validated_match_count: int = Field(ge=0)
    keyword_count: int = Field(ge=0)
    provider_status: str = "none"
    duration_ms: int | None = None


class AnalysisListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AnalysisSummary]
    total: int = Field(ge=0)
    limit: int = Field(gt=0)
    offset: int = Field(ge=0)


class ProviderRunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    provider_name: str
    provider_type: str
    operation: str
    status: str
    result_count: int | None = None
    started_at: datetime
    completed_at: datetime | None = None
    latency_ms: int | None = None
    estimated_cost_usd: float | None = None
    actual_cost_usd: float | None = None
    error_type: str | None = None
    error_message: str | None = None
    correlation_id: str | None = None


class MarketplaceObservationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    provider_name: str
    platform: str
    listing_id: str
    source_url: str | None = None
    title: str
    normalized_title: str
    brand: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    condition: str | None = None
    currency: str | None = None
    item_price: float | None = None
    landed_price: float | None = None
    observed_at: datetime


class ProductMatchResultRecordView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    marketplace_observation_id: str
    status: str
    relationship: str
    score: float
    eligible_for_price_aggregation: bool
    aggregation_group: str | None = None
    human_summary: str
    matcher_version: str
    created_at: datetime


class ManualMatchOverrideRecordView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    marketplace_observation_id: str
    listing_id: str
    override_status: str
    override_relationship: str | None = None
    override_eligible_for_price_aggregation: bool | None = None
    reason: str | None = Field(default=None, max_length=500)
    created_by: str | None = None
    created_at: datetime


class AnalysisDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: AnalysisSummary
    product_profile: ProductProfile | None = None
    marketplace_snapshot: MarketplaceSnapshot | None = None
    keyword_candidates: list[KeywordCandidate] = Field(default_factory=_keyword_candidate_list)
    keyword_intelligence: KeywordIntelligence | None = None
    provider_runs: list[ProviderRunRecord] = Field(default_factory=_provider_run_record_list)
    marketplace_observations: list[MarketplaceObservationRecord] = Field(
        default_factory=_marketplace_observation_record_list
    )
    match_results: list[ProductMatchResultRecordView] = Field(
        default_factory=_product_match_result_record_list
    )
    manual_overrides: list[ManualMatchOverrideRecordView] = Field(
        default_factory=_manual_match_override_record_list
    )
    report: PerceptionRun | None = None


class AnalysisMarketplaceOverrideInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    override_status: MarketplaceReviewDecision
    override_relationship: str | None = None
    override_eligible_for_price_aggregation: bool | None = None
    reason: str | None = Field(default=None, max_length=500)
    created_by: str = Field(default="manual", min_length=1, max_length=80)


class AdminDbTableSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    columns: list[str]
    record_count: int | None = None


class AdminDbTableListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tables: list[AdminDbTableSummary]


class AdminDbTableRowsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class AdminDbRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_name: str
    record: dict[str, Any]
