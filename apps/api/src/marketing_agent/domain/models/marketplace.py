"""Marketplace opportunity, validation, and price estimate models."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from marketing_agent.domain.models.evidence import EvidenceRecord


def _evidence_record_list() -> list[EvidenceRecord]:
    return []


def _rank_signal_list() -> list[RankSignal]:
    return []


def _match_conflict_list() -> list[MatchConflict]:
    return []


def _marketplace_listing_validation_list() -> list[MarketplaceListingValidation]:
    return []


def _marketplace_platform_estimate_list() -> list[MarketplacePlatformEstimate]:
    return []


def _marketplace_price_estimate_list() -> list[MarketplacePriceEstimate]:
    return []


def _marketplace_review_override_list() -> list[MarketplaceReviewOverride]:
    return []


class ProductCondition(StrEnum):
    NEW = "new"
    OPEN_BOX = "open_box"
    REFURBISHED = "refurbished"
    USED_LIKE_NEW = "used_like_new"
    USED_GOOD = "used_good"
    USED_ACCEPTABLE = "used_acceptable"
    FOR_PARTS = "for_parts"
    UNKNOWN = "unknown"


class MatchRuleOutcome(StrEnum):
    PASS = "pass"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class MatchConflictSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProductMatchStatus(StrEnum):
    EXACT_MATCH = "exact_match"
    PROBABLE_MATCH = "probable_match"
    UNCERTAIN = "uncertain"
    REJECTED = "rejected"


class BrandRole(StrEnum):
    OFFICIAL_BRAND = "official_brand"
    MANUFACTURER_BRAND = "manufacturer_brand"
    THIRD_PARTY_BRAND = "third_party_brand"
    COMPATIBILITY_TARGET = "compatibility_target"
    UNKNOWN = "unknown"


class ProductRelationship(StrEnum):
    OFFICIAL_EXACT_PRODUCT = "official_exact_product"
    OFFICIAL_SAME_PRODUCT_FAMILY = "official_same_product_family"
    LICENSED_THIRD_PARTY_ALTERNATIVE = "licensed_third_party_alternative"
    GENERIC_COMPATIBLE_ALTERNATIVE = "generic_compatible_alternative"
    ACCESSORY_OR_REPLACEMENT = "accessory_or_replacement"
    UNRELATED = "unrelated"
    UNKNOWN = "unknown"


class MarketplaceReviewDecision(StrEnum):
    OFFICIAL_MATCH = "official_match"
    OFFICIAL_VARIANT = "official_variant"
    LICENSED_ALTERNATIVE = "licensed_alternative"
    COMPATIBLE_ALTERNATIVE = "compatible_alternative"
    REJECTED = "rejected"
    ALTERNATE_PACKAGE = "alternate_package"


class MarketplaceReviewOverrideInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_id: str = Field(min_length=1)
    decision: MarketplaceReviewDecision
    note: str | None = Field(default=None, max_length=500)
    reviewer: str = Field(default="manual", min_length=1, max_length=80)


class MarketplaceReviewOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    listing_id: str = Field(min_length=1)
    decision: MarketplaceReviewDecision
    note: str | None = Field(default=None, max_length=500)
    reviewer: str = Field(default="manual", min_length=1, max_length=80)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RankSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    value: float
    source: str | None = None


class ProductIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand: str | None = None
    manufacturer: str | None = None
    sub_brand: str | None = None
    product_name: str
    normalized_product_name: str
    official_product_line: str | None = None
    product_type: str | None = None
    category: str | None = None
    model_number: str | None = None
    manufacturer_part_number: str | None = None
    gtin: str | None = None
    upc: str | None = None
    ean: str | None = None
    isbn: str | None = None
    asin: str | None = None
    variant: str | None = None
    color: str | None = None
    size: str | None = None
    material: str | None = None
    pack_quantity: int | None = Field(default=None, ge=1)
    unit_quantity: float | None = Field(default=None, gt=0.0)
    unit_type: str | None = None
    expected_condition: ProductCondition | None = None
    normalized_title: str
    allowed_brand_aliases: list[str] = Field(default_factory=list)
    allowed_manufacturer_aliases: list[str] = Field(default_factory=list)
    official_name_patterns: list[str] = Field(default_factory=list)
    target_is_official_product: bool = False
    aliases: list[str] = Field(default_factory=list)
    excluded_terms: list[str] = Field(default_factory=list)
    source_evidence: list[EvidenceRecord] = Field(default_factory=_evidence_record_list)


class NormalizedMarketplaceListing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    listing_id: str = Field(min_length=1)
    source_url: str | None = None
    title: str = Field(min_length=1)
    normalized_title: str = Field(min_length=1)
    description_excerpt: str | None = None
    brand: str | None = None
    provider_brand: str | None = None
    extracted_title_brand: str | None = None
    manufacturer: str | None = None
    product_line: str | None = None
    model_number: str | None = None
    manufacturer_part_number: str | None = None
    gtin: str | None = None
    upc: str | None = None
    ean: str | None = None
    isbn: str | None = None
    asin: str | None = None
    product_type: str | None = None
    category: str | None = None
    variant: str | None = None
    color: str | None = None
    size: str | None = None
    pack_quantity: int | None = Field(default=None, ge=1)
    unit_quantity: float | None = Field(default=None, gt=0.0)
    unit_type: str | None = None
    condition: ProductCondition | None = None
    compatibility_targets: list[str] = Field(default_factory=list)
    compatibility_phrases: list[str] = Field(default_factory=list)
    claimed_official: bool | None = None
    claimed_licensed: bool | None = None
    brand_role: BrandRole | None = None
    item_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    shipping_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    mandatory_fees: Decimal | None = Field(default=None, ge=Decimal("0"))
    discount: Decimal | None = Field(default=None, ge=Decimal("0"))
    landed_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    image_urls: list[str] = Field(default_factory=list)
    seller_name: str | None = None
    stock_status: str | None = None
    rating: float | None = Field(default=None, ge=0.0)
    review_count: int | None = Field(default=None, ge=0)
    raw_rank_signals: list[RankSignal] = Field(default_factory=_rank_signal_list)
    raw_provider_payload_reference: str | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def fill_landed_price(self) -> NormalizedMarketplaceListing:
        if self.landed_price is None and self.item_price is not None:
            self.landed_price = (
                self.item_price
                + (self.shipping_price or Decimal("0"))
                + (self.mandatory_fees or Decimal("0"))
                - (self.discount or Decimal("0"))
            )
        return self

    @field_serializer(
        "item_price",
        "shipping_price",
        "mandatory_fees",
        "discount",
        "landed_price",
        when_used="json",
    )
    def serialize_money(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None


class MatchConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    field: str = Field(min_length=1)
    expected: Any = None
    observed: Any = None
    severity: MatchConflictSeverity
    explanation: str = Field(min_length=1)


class MatchFeatureScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier_score: float | None = Field(default=None, ge=0.0, le=1.0)
    brand_score: float | None = Field(default=None, ge=0.0, le=1.0)
    brand_owner_score: float | None = Field(default=None, ge=0.0, le=1.0)
    manufacturer_score: float | None = Field(default=None, ge=0.0, le=1.0)
    official_product_line_score: float | None = Field(default=None, ge=0.0, le=1.0)
    compatibility_only_penalty: float | None = Field(default=None, ge=0.0, le=1.0)
    third_party_brand_penalty: float | None = Field(default=None, ge=0.0, le=1.0)
    model_score: float | None = Field(default=None, ge=0.0, le=1.0)
    title_score: float = Field(ge=0.0, le=1.0)
    important_token_score: float = Field(ge=0.0, le=1.0)
    product_type_score: float | None = Field(default=None, ge=0.0, le=1.0)
    category_score: float | None = Field(default=None, ge=0.0, le=1.0)
    variant_score: float | None = Field(default=None, ge=0.0, le=1.0)
    package_score: float | None = Field(default=None, ge=0.0, le=1.0)
    condition_score: float | None = Field(default=None, ge=0.0, le=1.0)
    image_score: float | None = Field(default=None, ge=0.0, le=1.0)


class OfficialNameVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    official_name_match: bool | None = None
    official_product_line_match: bool | None = None
    expected_brand_present_as_brand: bool | None = None
    expected_brand_present_only_as_compatibility_target: bool = False
    detected_listing_brand: str | None = None
    detected_manufacturer: str | None = None
    relationship: ProductRelationship
    reason_codes: list[str] = Field(default_factory=list)
    conflicts: list[MatchConflict] = Field(default_factory=_match_conflict_list)


class ProductMatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_id: str = Field(min_length=1)
    status: ProductMatchStatus
    relationship: ProductRelationship = ProductRelationship.UNKNOWN
    score: float = Field(ge=0.0, le=1.0)
    matched_fields: list[str] = Field(default_factory=list)
    unknown_fields: list[str] = Field(default_factory=list)
    conflicts: list[MatchConflict] = Field(default_factory=_match_conflict_list)
    feature_scores: MatchFeatureScores
    official_name_verification: OfficialNameVerification | None = None
    reason_codes: list[str] = Field(default_factory=list)
    human_summary: str = Field(min_length=1)
    eligible_for_price_aggregation: bool
    aggregation_group: str | None = None
    requires_human_review: bool
    matcher_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MarketplaceListingValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing: NormalizedMarketplaceListing
    match_result: ProductMatchResult
    manual_override: MarketplaceReviewOverride | None = None


class MarketplaceValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_candidates: int = Field(ge=0)
    exact_match_count: int = Field(ge=0)
    probable_match_count: int = Field(ge=0)
    uncertain_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    primary_eligible_count: int = Field(ge=0)
    official_match_count: int = Field(default=0, ge=0)
    official_variant_count: int = Field(default=0, ge=0)
    licensed_alternative_count: int = Field(default=0, ge=0)
    compatible_alternative_count: int = Field(default=0, ge=0)
    accessory_or_replacement_count: int = Field(default=0, ge=0)
    alternate_variant_count: int = Field(ge=0)
    alternate_package_count: int = Field(ge=0)
    alternate_condition_count: int = Field(ge=0)
    matcher_version: str
    scoring_policy_version: str
    normalization_version: str


class MarketplacePlatformEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1, le=10)
    platform: str = Field(min_length=1)
    platform_type: str = Field(
        pattern="^(marketplace|retailer|social_commerce|specialty|brand_store|other)$"
    )
    data_source: str = Field(min_length=1)
    estimated_sales_potential_score: float = Field(ge=0.0, le=1.0)
    observed_offer_count: int | None = Field(default=None, ge=0)
    observed_review_count: int | None = Field(default=None, ge=0)
    observed_units_sold: int | None = Field(default=None, ge=0)
    observed_sales_signal: str | None = None
    sales_rank_basis: str = Field(min_length=1)
    listing_search_phrase: str = Field(min_length=1)
    source_url: str | None = None
    evidence_ids: list[str] = Field(min_length=1)
    source_count: int = Field(default=1, ge=1)
    validated_listing_count: int = Field(default=0, ge=0)
    matcher_version: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    risk_flags: list[str] = Field(default_factory=list)


class MarketplacePriceEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str = Field(min_length=1)
    data_source: str = Field(min_length=1)
    price_low: float | None = Field(default=None, ge=0.0)
    price_median: float | None = Field(default=None, ge=0.0)
    price_high: float | None = Field(default=None, ge=0.0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    observed_offer_count: int | None = Field(default=None, ge=0)
    source_count: int = Field(default=1, ge=1)
    observation_started_at: datetime | None = None
    observation_ended_at: datetime | None = None
    aggregation_group: str = "primary"
    matcher_version: str | None = None
    price_basis: str = Field(min_length=1)
    listing_search_phrase: str = Field(min_length=1)
    source_url: str | None = None
    evidence_ids: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    risk_flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_price_range(self) -> MarketplacePriceEstimate:
        if (
            self.price_low is not None
            and self.price_high is not None
            and self.price_high < self.price_low
        ):
            raise ValueError("price_high must be greater than or equal to price_low")
        return self


class MarketplaceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source_provider: str = Field(min_length=1)
    source_query: str = Field(min_length=1)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_live_data: bool
    methodology: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    product_identity: ProductIdentity | None = None
    validation_summary: MarketplaceValidationSummary | None = None
    validated_listings: list[MarketplaceListingValidation] = Field(
        default_factory=_marketplace_listing_validation_list
    )
    platform_rankings: list[MarketplacePlatformEstimate] = Field(
        default_factory=_marketplace_platform_estimate_list, max_length=10
    )
    price_estimates: list[MarketplacePriceEstimate] = Field(
        default_factory=_marketplace_price_estimate_list, max_length=10
    )
    warnings: list[str] = Field(default_factory=list)
    manual_overrides: list[MarketplaceReviewOverride] = Field(
        default_factory=_marketplace_review_override_list
    )
    overall_confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_rankings(self) -> MarketplaceSnapshot:
        ranks = [item.rank for item in self.platform_rankings]
        if len(ranks) != len(set(ranks)):
            raise ValueError("platform ranking ranks must be unique")
        return self
