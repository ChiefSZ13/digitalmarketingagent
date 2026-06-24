"""Marketplace opportunity and price estimate models."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    confidence: float = Field(ge=0.0, le=1.0)
    risk_flags: list[str] = Field(default_factory=list)


class MarketplacePriceEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str = Field(min_length=1)
    data_source: str = Field(min_length=1)
    price_low: float | None = Field(default=None, ge=0.0)
    price_high: float | None = Field(default=None, ge=0.0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    observed_offer_count: int | None = Field(default=None, ge=0)
    price_basis: str = Field(min_length=1)
    listing_search_phrase: str = Field(min_length=1)
    source_url: str | None = None
    evidence_ids: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    risk_flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_price_range(self) -> "MarketplacePriceEstimate":
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
    platform_rankings: list[MarketplacePlatformEstimate] = Field(min_length=1, max_length=10)
    price_estimates: list[MarketplacePriceEstimate] = Field(min_length=1, max_length=10)
    warnings: list[str] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_rankings(self) -> "MarketplaceSnapshot":
        ranks = [item.rank for item in self.platform_rankings]
        if len(ranks) != len(set(ranks)):
            raise ValueError("platform ranking ranks must be unique")
        return self
