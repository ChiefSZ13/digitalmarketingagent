"""Deterministic marketplace data provider for tests and offline development."""

from datetime import UTC, datetime

from marketing_agent.domain.models.evidence import EvidenceRecord, EvidenceSource
from marketing_agent.domain.models.marketplace import (
    MarketplacePlatformEstimate,
    MarketplacePriceEstimate,
    MarketplaceSnapshot,
)
from marketing_agent.domain.ports.marketplace_data_provider import (
    MarketplaceDataProviderRequest,
    MarketplaceDataProviderResult,
)
from marketing_agent.domain.services.marketplace_query import build_marketplace_search_query


class MockMarketplaceDataProvider:
    async def fetch_snapshot(
        self, request: MarketplaceDataProviderRequest
    ) -> MarketplaceDataProviderResult:
        product_name = _product_name(request)
        category = (
            request.product_profile.category.value
            if request.product_profile.category
            else "Product"
        )
        query = build_marketplace_search_query(
            request=request.request,
            profile=request.product_profile,
        )
        now = datetime.now(UTC)
        evidence = [
            EvidenceRecord(
                id="ev-marketplace-mock-1",
                source=EvidenceSource.MARKETPLACE_PROVIDER,
                source_reference="mock_marketplace_provider",
                observation=(
                    "Mock marketplace provider returned deterministic fixture data. "
                    "No live marketplace request was made."
                ),
                quote=query,
                confidence=1.0,
                created_at=now,
            )
        ]
        evidence_ids = ["ev-marketplace-mock-1"]
        platforms = [
            ("Amazon", "marketplace", 0.9, 18.99, 39.99, 8, 7900),
            ("Walmart Marketplace", "marketplace", 0.78, 16.99, 34.99, 5, 640),
            ("AliExpress", "marketplace", 0.74, 8.99, 24.99, 4, 2100),
            ("eBay", "marketplace", 0.66, 11.99, 32.99, 3, 330),
            ("Temu", "marketplace", 0.64, 7.99, 21.99, 3, 1800),
            ("Target", "retailer", 0.58, 19.99, 44.99, 2, 180),
            ("Wayfair", "specialty", 0.53, 24.99, 59.99, 2, 520),
            ("Etsy", "marketplace", 0.45, 22.0, 68.0, 2, 95),
            ("TikTok Shop", "social_commerce", 0.43, 12.99, 35.99, 1, 0),
            ("Independent Shopify stores", "brand_store", 0.38, 19.99, 49.99, 1, 0),
        ]
        rankings: list[MarketplacePlatformEstimate] = []
        prices: list[MarketplacePriceEstimate] = []
        for rank, (
            platform,
            platform_type,
            score,
            low,
            high,
            offer_count,
            review_count,
        ) in enumerate(platforms, start=1):
            search_phrase = f"{query} {platform}".strip()
            rankings.append(
                MarketplacePlatformEstimate(
                    rank=rank,
                    platform=platform,
                    platform_type=platform_type,
                    data_source="mock_marketplace_provider",
                    estimated_sales_potential_score=score,
                    observed_offer_count=offer_count,
                    observed_review_count=review_count,
                    observed_units_sold=None,
                    observed_sales_signal=None,
                    sales_rank_basis=(
                        f"Mock ranking shaped like real marketplace data for category '{category}'."
                    ),
                    listing_search_phrase=search_phrase,
                    source_url=None,
                    evidence_ids=evidence_ids,
                    confidence=0.5 if rank <= 5 else 0.4,
                    risk_flags=["mock_data", "not_live_marketplace_data"],
                )
            )
            prices.append(
                MarketplacePriceEstimate(
                    platform=platform,
                    data_source="mock_marketplace_provider",
                    price_low=low,
                    price_high=high,
                    currency="USD",
                    observed_offer_count=offer_count,
                    price_basis="Mock comparable-listing price range for UI and contract tests.",
                    listing_search_phrase=search_phrase,
                    source_url=None,
                    evidence_ids=evidence_ids,
                    confidence=0.5 if rank <= 5 else 0.4,
                    risk_flags=["mock_data", "not_live_marketplace_data"],
                )
            )
        snapshot = MarketplaceSnapshot(
            title=f"Marketplace Snapshot for {product_name}",
            summary="Mock marketplace ranking and price ranges for development.",
            source_provider="mock",
            source_query=query,
            retrieved_at=now,
            is_live_data=False,
            methodology="Deterministic fixture shaped like live marketplace-provider output.",
            limitations=[
                "No marketplace APIs, retailer feeds, web search, or scraping were used.",
                "Use SerpAPI or another marketplace provider for live data.",
            ],
            platform_rankings=rankings,
            price_estimates=prices,
            warnings=["Mock marketplace data used; not suitable for production decisions."],
            overall_confidence=0.5,
        )
        return MarketplaceDataProviderResult(
            snapshot=snapshot,
            evidence=evidence,
            warnings=snapshot.warnings,
        )


def _product_name(request: MarketplaceDataProviderRequest) -> str:
    if request.product_profile.product_name:
        return request.product_profile.product_name.value
    return request.request.description.strip()
