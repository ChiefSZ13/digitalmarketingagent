"""SQLAlchemy ORM tables for persisted product intelligence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from marketing_agent.infrastructure.database.base import (
    Base,
    JSONBType,
    TimestampMixin,
    UpdatedTimestampMixin,
    uuid_pk,
)


class Product(UpdatedTimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_display_name", "display_name"),
        Index("ix_products_normalized_name", "normalized_name"),
        Index("ix_products_brand", "brand"),
        Index("ix_products_created_at", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    display_name: Mapped[str] = mapped_column(String(500))
    brand: Mapped[str | None] = mapped_column(String(255))
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model_number: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(255))
    product_type: Mapped[str | None] = mapped_column(String(255))
    normalized_name: Mapped[str | None] = mapped_column(String(500))
    gtin: Mapped[str | None] = mapped_column(String(64))
    upc: Mapped[str | None] = mapped_column(String(64))
    ean: Mapped[str | None] = mapped_column(String(64))
    asin: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict)


class AnalysisRun(UpdatedTimestampMixin, Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_analysis_runs_run_id"),
        Index("ix_analysis_runs_product_id", "product_id"),
        Index("ix_analysis_runs_status", "status"),
        Index("ix_analysis_runs_created_at", "created_at"),
        Index("ix_analysis_runs_completed_at", "completed_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    run_id: Mapped[str] = mapped_column(String(80))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(40), default="queued")
    input_description: Mapped[str] = mapped_column(Text)
    input_payload_json: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    schema_version: Mapped[str] = mapped_column(String(120))


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        Index("ix_media_assets_product_id", "product_id"),
        Index("ix_media_assets_analysis_run_id", "analysis_run_id"),
        Index("ix_media_assets_content_hash", "content_hash"),
    )

    id: Mapped[UUID] = uuid_pk()
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    asset_type: Mapped[str] = mapped_column(String(40), default="image")
    filename: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    storage_uri: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict)


class ProductProfileVersion(TimestampMixin, Base):
    __tablename__ = "product_profile_versions"
    __table_args__ = (
        Index("ix_product_profile_versions_product_id", "product_id"),
        Index("ix_product_profile_versions_analysis_run_id", "analysis_run_id"),
        Index("ix_product_profile_versions_provider", "provider"),
        Index("ix_product_profile_versions_created_at", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    analysis_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    profile_version: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(120))
    model_name: Mapped[str | None] = mapped_column(String(255))
    prompt_version: Mapped[str | None] = mapped_column(String(120))
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSONBType)
    confidence_summary_json: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict)


class ProviderRun(TimestampMixin, Base):
    __tablename__ = "provider_runs"
    __table_args__ = (
        Index("ix_provider_runs_analysis_run_id", "analysis_run_id"),
        Index("ix_provider_runs_provider_name", "provider_name"),
        Index("ix_provider_runs_status", "status"),
        Index("ix_provider_runs_created_at", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    provider_name: Mapped[str] = mapped_column(String(120))
    provider_type: Mapped[str] = mapped_column(String(40))
    operation: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40))
    request_hash: Mapped[str | None] = mapped_column(String(128))
    request_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict)
    response_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict)
    result_count: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    actual_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    error_type: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(160))


class MarketplaceObservation(TimestampMixin, Base):
    __tablename__ = "marketplace_observations"
    __table_args__ = (
        Index("ix_marketplace_observations_analysis_run_id", "analysis_run_id"),
        Index("ix_marketplace_observations_provider_name", "provider_name"),
        Index("ix_marketplace_observations_platform", "platform"),
        Index("ix_marketplace_observations_listing_id", "listing_id"),
        Index("ix_marketplace_observations_observed_at", "observed_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    analysis_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    provider_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("provider_runs.id", ondelete="SET NULL")
    )
    provider_name: Mapped[str] = mapped_column(String(120))
    platform: Mapped[str] = mapped_column(String(160))
    listing_id: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    normalized_title: Mapped[str] = mapped_column(Text)
    seller_name: Mapped[str | None] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(255))
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model_number: Mapped[str | None] = mapped_column(String(255))
    condition: Mapped[str | None] = mapped_column(String(80))
    currency: Mapped[str | None] = mapped_column(String(3))
    item_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    shipping_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    landed_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stock_status: Mapped[str | None] = mapped_column(String(120))
    rating: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    review_count: Mapped[int | None] = mapped_column(Integer)
    rank_signals_json: Mapped[list[Any]] = mapped_column(JSONBType, default=list)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)


class ProductMatchResultRecord(TimestampMixin, Base):
    __tablename__ = "product_match_results"
    __table_args__ = (
        Index("ix_product_match_results_analysis_run_id", "analysis_run_id"),
        Index("ix_product_match_results_observation_id", "marketplace_observation_id"),
        Index("ix_product_match_results_status", "status"),
        Index("ix_product_match_results_created_at", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    analysis_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    marketplace_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("marketplace_observations.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(80))
    relationship: Mapped[str] = mapped_column(String(120))
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    eligible_for_price_aggregation: Mapped[bool] = mapped_column(Boolean)
    aggregation_group: Mapped[str | None] = mapped_column(String(120))
    matched_fields_json: Mapped[list[Any]] = mapped_column(JSONBType, default=list)
    unknown_fields_json: Mapped[list[Any]] = mapped_column(JSONBType, default=list)
    conflicts_json: Mapped[list[Any]] = mapped_column(JSONBType, default=list)
    feature_scores_json: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict)
    reason_codes_json: Mapped[list[Any]] = mapped_column(JSONBType, default=list)
    human_summary: Mapped[str] = mapped_column(Text)
    matcher_version: Mapped[str] = mapped_column(String(120))
    scoring_policy_version: Mapped[str] = mapped_column(String(120))
    normalization_version: Mapped[str] = mapped_column(String(120))


class ManualMatchOverride(TimestampMixin, Base):
    __tablename__ = "manual_match_overrides"
    __table_args__ = (
        Index("ix_manual_match_overrides_analysis_run_id", "analysis_run_id"),
        Index("ix_manual_match_overrides_observation_id", "marketplace_observation_id"),
        Index("ix_manual_match_overrides_created_at", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    analysis_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    marketplace_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("marketplace_observations.id", ondelete="CASCADE")
    )
    product_match_result_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_match_results.id", ondelete="SET NULL")
    )
    override_status: Mapped[str] = mapped_column(String(80))
    override_relationship: Mapped[str | None] = mapped_column(String(120))
    override_eligible_for_price_aggregation: Mapped[bool | None] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(120))


class KeywordCandidateRecord(TimestampMixin, Base):
    __tablename__ = "keyword_candidates"
    __table_args__ = (
        Index("ix_keyword_candidates_analysis_run_id", "analysis_run_id"),
        Index("ix_keyword_candidates_keyword", "keyword"),
        Index("ix_keyword_candidates_normalized_keyword", "normalized_keyword"),
        Index("ix_keyword_candidates_created_at", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    analysis_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    keyword: Mapped[str] = mapped_column(Text)
    normalized_keyword: Mapped[str] = mapped_column(Text)
    term_type: Mapped[str] = mapped_column(String(80))
    query_family: Mapped[str | None] = mapped_column(String(120))
    intent: Mapped[str | None] = mapped_column(String(80))
    origin_json: Mapped[list[Any]] = mapped_column(JSONBType, default=list)
    product_relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    query_realism_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    commercial_intent_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    eligible_for_live_enrichment: Mapped[bool] = mapped_column(Boolean, default=False)
    cluster_id: Mapped[str | None] = mapped_column(String(120))
    score_components_json: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict)
    rejection_reasons_json: Mapped[list[Any]] = mapped_column(JSONBType, default=list)
    generator_version: Mapped[str] = mapped_column(String(120))


class KeywordMetric(TimestampMixin, Base):
    __tablename__ = "keyword_metrics"
    __table_args__ = (
        Index("ix_keyword_metrics_candidate_id", "keyword_candidate_id"),
        Index("ix_keyword_metrics_analysis_run_id", "analysis_run_id"),
        Index("ix_keyword_metrics_provider_name", "provider_name"),
        Index("ix_keyword_metrics_collected_at", "collected_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    keyword_candidate_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("keyword_candidates.id", ondelete="SET NULL")
    )
    analysis_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    provider_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("provider_runs.id", ondelete="SET NULL")
    )
    provider_name: Mapped[str] = mapped_column(String(120))
    keyword: Mapped[str] = mapped_column(Text)
    normalized_keyword: Mapped[str] = mapped_column(Text)
    country_code: Mapped[str] = mapped_column(String(16))
    language_code: Mapped[str] = mapped_column(String(16))
    currency_code: Mapped[str | None] = mapped_column(String(3))
    average_monthly_searches: Mapped[int | None] = mapped_column(Integer)
    cpc_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    low_top_of_page_bid: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    high_top_of_page_bid: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    paid_competition: Mapped[str | None] = mapped_column(String(80))
    competition_index: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    trend_direction: Mapped[str | None] = mapped_column(String(80))
    monthly_history_json: Mapped[list[Any]] = mapped_column(JSONBType, default=list)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)


class IntelligenceReportSnapshot(TimestampMixin, Base):
    __tablename__ = "intelligence_report_snapshots"
    __table_args__ = (
        Index("ix_intelligence_report_snapshots_analysis_run_id", "analysis_run_id"),
        Index("ix_intelligence_report_snapshots_created_at", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    analysis_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    schema_version: Mapped[str] = mapped_column(String(120))
    report_json: Mapped[dict[str, Any]] = mapped_column(JSONBType)
