"""Keyword candidate and cluster models."""

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

    average_monthly_searches: int | None = None
    competition_level: str | None = None
    cpc_low: float | None = None
    cpc_high: float | None = None
    trend: str | None = None
    source_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def require_empty_for_mvp(self) -> "EnrichmentMetrics":
        values = self.model_dump()
        if any(value is not None for value in values.values()):
            raise ValueError("live keyword enrichment is out of scope for MVP 1B")
        return self


class KeywordCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    normalized_text: str = Field(min_length=1)
    intent: KeywordIntent
    category: KeywordCategory
    rationale: str = Field(min_length=1)
    source: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    relevance_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    score_components: ScoreComponents
    risk_flags: list[str] = Field(default_factory=list)
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
