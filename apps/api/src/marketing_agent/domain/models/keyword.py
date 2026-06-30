"""Keyword candidate, enrichment, and cluster models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KeywordIntent(StrEnum):
    INFORMATIONAL = "informational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"
    COMPARISON = "comparison"
    NAVIGATIONAL = "navigational"
    UNKNOWN = "unknown"


class KeywordCategory(StrEnum):
    PRODUCT = "product"
    FEATURE = "feature"
    BENEFIT = "benefit"
    PROBLEM_SOLUTION = "problem_solution"
    USE_CASE = "use_case"
    AUDIENCE = "audience"
    LONG_TAIL = "long_tail"
    ALTERNATIVE = "alternative"
    NEGATIVE = "negative"
    CONTENT_ANGLE = "content_angle"


class MarketingTermType(StrEnum):
    SEARCH_QUERY = "search_query"
    CONTENT_TOPIC = "content_topic"
    PRODUCT_FEATURE = "product_feature"
    PRODUCT_BENEFIT = "product_benefit"
    AUDIENCE_DESCRIPTION = "audience_description"


class SearchQueryCategory(StrEnum):
    BRAND_PRODUCT = "brand_product"
    GENERIC_PRODUCT = "generic_product"
    FEATURE = "feature"
    USE_CASE = "use_case"
    PROBLEM_SOLUTION = "problem_solution"
    COMPARISON = "comparison"
    REVIEW = "review"
    TRANSACTIONAL = "transactional"
    LOCAL_OR_SIZE_SPECIFIC = "local_or_size_specific"


class SearchQueryRejectionReason(StrEnum):
    EMPTY = "empty"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    SENTENCE_PUNCTUATION = "sentence_punctuation"
    BANNED_PHRASE = "banned_phrase"
    DESCRIPTION_COPY = "description_copy"
    ATTRIBUTE_DENSE = "attribute_dense"
    LOW_PRODUCT_RELEVANCE = "low_product_relevance"
    LOW_QUERY_REALISM = "low_query_realism"
    DUPLICATE = "duplicate"


class KeywordOrigin(StrEnum):
    PRODUCT_PROFILE = "product_profile"
    MODEL_GENERATED = "model_generated"
    PROVIDER_RELATED_TERM = "provider_related_term"
    MANUAL = "manual"


class KeywordCompetition(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class KeywordTrendDirection(StrEnum):
    RISING = "rising"
    FLAT = "flat"
    DECLINING = "declining"
    SEASONAL = "seasonal"
    INSUFFICIENT_DATA = "insufficient_data"
    UNKNOWN = "unknown"


class ProviderMatchType(StrEnum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    PUNCTUATION_INSENSITIVE = "punctuation_insensitive"
    SINGULAR_PLURAL = "singular_plural"
    TOKEN_OVERLAP = "token_overlap"
    RELATED_TERM = "related_term"
    NONE = "none"


class KeywordEnrichmentStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"


def _rejection_reason_list() -> list[SearchQueryRejectionReason]:
    return []


def _keyword_origin_list() -> list[KeywordOrigin]:
    return [KeywordOrigin.MODEL_GENERATED]


def _keyword_monthly_metric_list() -> list[KeywordMonthlyMetric]:
    return []


def _keyword_intelligence_keyword_list() -> list[KeywordIntelligenceKeyword]:
    return []


def _keyword_intelligence_cluster_list() -> list[KeywordIntelligenceCluster]:
    return []


def _string_list() -> list[str]:
    return []


class ScoreComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_match: float = Field(ge=0.0, le=1.0)
    intent_value: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    audience_fit: float = Field(ge=0.0, le=1.0)
    specificity: float = Field(ge=0.0, le=1.0)
    risk_penalty: float = Field(ge=0.0, le=1.0)

    def relevance(self) -> float:
        score = (
            0.35 * self.product_match
            + 0.20 * self.intent_value
            + 0.15 * self.evidence_strength
            + 0.15 * self.audience_fit
            + 0.15 * self.specificity
            - self.risk_penalty
        )
        return round(max(0.0, min(1.0, score)), 4)


class EnrichmentMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    average_monthly_searches: int | None = Field(default=None, ge=0)
    competition_level: str | None = None
    cpc_low: float | None = Field(default=None, ge=0.0)
    cpc_high: float | None = Field(default=None, ge=0.0)
    trend: str | None = None
    source_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    provider: str | None = None
    provider_record_id: str | None = None
    provider_match_type: ProviderMatchType | None = None
    provider_match_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    matched_provider_term: str | None = None
    market: str | None = None
    language: str | None = None
    currency: str | None = None
    retrieved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_range(self) -> EnrichmentMetrics:
        if self.cpc_low is not None and self.cpc_high is not None and self.cpc_low > self.cpc_high:
            raise ValueError("cpc_low cannot exceed cpc_high")
        return self


class KeywordMonthlyMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    searches: int = Field(ge=0)


class KeywordMarketMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    provider_record_id: str | None = None
    keyword: str = Field(min_length=1)
    matched_provider_term: str = Field(min_length=1)
    provider_match_type: ProviderMatchType
    provider_match_confidence: float = Field(ge=0.0, le=1.0)
    average_monthly_searches: int | None = Field(default=None, ge=0)
    competition: KeywordCompetition | None = None
    competition_index: float | None = Field(default=None, ge=0.0, le=1.0)
    cpc_low: float | None = Field(default=None, ge=0.0)
    cpc_high: float | None = Field(default=None, ge=0.0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    monthly_history: list[KeywordMonthlyMetric] = Field(
        default_factory=_keyword_monthly_metric_list
    )
    trend_direction: KeywordTrendDirection = KeywordTrendDirection.UNKNOWN
    trend_strength: float | None = Field(default=None, ge=0.0, le=1.0)
    trend_explanation: str | None = None
    market: str = Field(min_length=2)
    language: str = Field(min_length=2)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_price_range(self) -> KeywordMarketMetrics:
        if self.cpc_low is not None and self.cpc_high is not None and self.cpc_low > self.cpc_high:
            raise ValueError("cpc_low cannot exceed cpc_high")
        return self


class KeywordOpportunityScoreComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_relevance: float = Field(ge=0.0, le=1.0)
    market_demand: float | None = Field(default=None, ge=0.0, le=1.0)
    competition_advantage: float | None = Field(default=None, ge=0.0, le=1.0)
    commercial_intent: float = Field(ge=0.0, le=1.0)
    cpc_efficiency: float | None = Field(default=None, ge=0.0, le=1.0)
    trend_signal: float | None = Field(default=None, ge=0.0, le=1.0)
    data_completeness: float = Field(ge=0.0, le=1.0)
    risk_penalty: float = Field(default=0.0, ge=0.0, le=1.0)


class KeywordIntelligenceKeyword(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    normalized_text: str = Field(min_length=1)
    origins: list[KeywordOrigin] = Field(min_length=1)
    intent: KeywordIntent
    category: KeywordCategory
    query_family: SearchQueryCategory
    product_relevance_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    market_signal_score: float | None = Field(default=None, ge=0.0, le=1.0)
    opportunity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    opportunity_components: KeywordOpportunityScoreComponents | None = None
    scoring_policy_version: str = Field(min_length=1)
    metrics: KeywordMarketMetrics | None = None
    rationale: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    source: str = Field(min_length=1)
    related_to: str | None = None


class KeywordIntelligenceCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=3)
    theme: str = Field(min_length=1)
    primary_keyword: str = Field(min_length=1)
    member_keywords: list[str] = Field(min_length=1)
    dominant_intent: KeywordIntent
    aggregate_relevance: float = Field(ge=0.0, le=1.0)
    aggregate_opportunity: float | None = Field(default=None, ge=0.0, le=1.0)
    keyword_count: int = Field(ge=1)


class KeywordIntelligenceMethodology(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scoring_policy_version: str = "keyword-opportunity-v1"
    matching_policy_version: str = "keyword-provider-match-v1"
    trend_policy_version: str = "keyword-trend-v1"
    notes: list[str] = Field(default_factory=_string_list)


class KeywordIntelligence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: KeywordEnrichmentStatus = KeywordEnrichmentStatus.SKIPPED
    provider: str = "none"
    market: str = "US"
    language: str = "en"
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    keywords: list[KeywordIntelligenceKeyword] = Field(
        default_factory=_keyword_intelligence_keyword_list
    )
    clusters: list[KeywordIntelligenceCluster] = Field(
        default_factory=_keyword_intelligence_cluster_list
    )
    warnings: list[str] = Field(default_factory=_string_list)
    methodology: KeywordIntelligenceMethodology = Field(
        default_factory=KeywordIntelligenceMethodology
    )


class KeywordCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    normalized_text: str = Field(min_length=1)
    marketing_term_type: MarketingTermType = MarketingTermType.SEARCH_QUERY
    query_family: SearchQueryCategory = SearchQueryCategory.GENERIC_PRODUCT
    intent: KeywordIntent
    category: KeywordCategory
    rationale: str = Field(min_length=1)
    source: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    relevance_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    generation_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    product_relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    query_realism_score: float = Field(default=0.0, ge=0.0, le=1.0)
    specificity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    commercial_intent_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_concepts: list[str] = Field(default_factory=_string_list)
    origin: str = Field(default="deterministic_search_query_generator", min_length=1)
    origins: list[KeywordOrigin] = Field(default_factory=_keyword_origin_list)
    rejection_reasons: list[SearchQueryRejectionReason] = Field(
        default_factory=_rejection_reason_list
    )
    eligible_for_live_enrichment: bool = False
    generator_version: str = Field(default="search-query-generator-v1", min_length=1)
    score_components: ScoreComponents
    market_signal_score: float | None = Field(default=None, ge=0.0, le=1.0)
    opportunity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    opportunity_components: KeywordOpportunityScoreComponents | None = None
    scoring_policy_version: str = "keyword-opportunity-v1"
    risk_flags: list[str] = Field(default_factory=_string_list)
    enrichment: EnrichmentMetrics = Field(default_factory=EnrichmentMetrics)


class KeywordCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=3)
    theme: str = Field(min_length=1)
    primary_keyword: str = Field(min_length=1)
    member_keywords: list[str] = Field(min_length=1)
    dominant_intent: KeywordIntent
    category: KeywordCategory
    aggregate_relevance: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(min_length=1)
    recommended_usage: str = Field(min_length=1)
