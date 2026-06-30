"""Deterministic marketplace data provider for tests and offline development."""

from datetime import UTC, datetime

from marketing_agent.domain.models.evidence import EvidenceRecord, EvidenceSource
from marketing_agent.domain.models.marketplace import (
    NormalizedMarketplaceListing,
    ProductCondition,
    RankSignal,
)
from marketing_agent.domain.models.provider import (
    CacheStatus,
    ProviderRunStatus,
    build_provider_telemetry,
)
from marketing_agent.domain.ports.marketplace_data_provider import (
    MarketplaceDataProviderRequest,
    MarketplaceDataProviderResult,
)
from marketing_agent.domain.services.marketplace_query import build_marketplace_search_query
from marketing_agent.domain.services.product_matcher import (
    ProductMatcherConfig,
    build_validated_marketplace_snapshot,
    decimal_or_none,
    normalize_text,
)


class MockMarketplaceDataProvider:
    def __init__(self, *, matcher_config: ProductMatcherConfig | None = None) -> None:
        self.matcher_config = matcher_config or ProductMatcherConfig()

    async def fetch_snapshot(
        self, request: MarketplaceDataProviderRequest
    ) -> MarketplaceDataProviderResult:
        started_at = datetime.now(UTC)
        product_name = _product_name(request)
        query = build_marketplace_search_query(
            request=request.request,
            profile=request.product_profile,
        )
        now = datetime.now(UTC)
        provider_evidence = [
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
                provider="mock",
                platform="mock_fixture",
                provider_run_id=query,
            )
        ]
        listings = _fixture_listings(product_name=product_name, query=query, observed_at=now)
        snapshot, validation_evidence = build_validated_marketplace_snapshot(
            request=request.request,
            profile=request.product_profile,
            listings=listings,
            source_provider="mock",
            source_query=query,
            title=f"Marketplace Snapshot for {product_name}",
            summary="Mock marketplace ranking and price ranges after deterministic validation.",
            is_live_data=False,
            methodology=(
                "Deterministic fixture shaped like provider output. Candidate listings are "
                "normalized, matched against the canonical product identity, and only validated "
                "primary matches enter price and platform aggregation."
            ),
            limitations=[
                "No marketplace APIs, retailer feeds, web search, or scraping were used.",
                "Use SerpAPI or another marketplace provider for live data.",
            ],
            base_warnings=["Mock marketplace data used; not suitable for production decisions."],
            retrieved_at=now,
            matcher_config=self.matcher_config,
        )
        return MarketplaceDataProviderResult(
            snapshot=snapshot,
            evidence=[*provider_evidence, *validation_evidence],
            warnings=snapshot.warnings,
            telemetry=build_provider_telemetry(
                provider="mock_marketplace",
                operation="marketplace_snapshot",
                started_at=started_at,
                status=ProviderRunStatus.SUCCEEDED,
                result_count=len(snapshot.validated_listings),
                cache_status=CacheStatus.BYPASS,
                correlation_id="mock-marketplace-provider-run",
            ),
        )


def _fixture_listings(
    *,
    product_name: str,
    query: str,
    observed_at: datetime,
) -> list[NormalizedMarketplaceListing]:
    platforms = [
        ("Amazon", 18.99, 39.99, 8, 7900),
        ("Walmart Marketplace", 16.99, 34.99, 5, 640),
        ("AliExpress", 8.99, 24.99, 4, 2100),
        ("eBay", 11.99, 32.99, 3, 330),
        ("Temu", 7.99, 21.99, 3, 1800),
        ("Target", 19.99, 44.99, 2, 180),
        ("Wayfair", 24.99, 59.99, 2, 520),
        ("Etsy", 22.0, 68.0, 2, 95),
        ("TikTok Shop", 12.99, 35.99, 1, 0),
        ("Independent Shopify stores", 19.99, 49.99, 1, 0),
    ]
    listings: list[NormalizedMarketplaceListing] = []
    for rank, (platform, low, high, offer_count, review_count) in enumerate(platforms, start=1):
        for index in range(offer_count):
            price_span = high - low
            price = low + (price_span * (index / max(offer_count - 1, 1)))
            listings.append(
                _listing(
                    platform=platform,
                    listing_id=f"mock-{rank}-{index + 1}",
                    title=f"{product_name} {query}".strip(),
                    item_price=round(price, 2),
                    review_count=max(review_count // offer_count, 0),
                    position=rank + index,
                    observed_at=observed_at,
                )
            )

    listings.extend(
        [
            _listing(
                platform="Amazon",
                listing_id="mock-accessory-1",
                title=f"Replacement charger for {product_name}",
                item_price=9.99,
                review_count=82,
                position=44,
                observed_at=observed_at,
            ),
            _listing(
                platform="Walmart Marketplace",
                listing_id="mock-pack-1",
                title=f"{product_name} - Pack of 2",
                item_price=36.99,
                review_count=42,
                position=45,
                observed_at=observed_at,
                pack_quantity=2,
            ),
            _listing(
                platform="eBay",
                listing_id="mock-condition-1",
                title=f"Open box {product_name}",
                item_price=14.99,
                review_count=12,
                position=46,
                observed_at=observed_at,
                condition=ProductCondition.OPEN_BOX,
            ),
            _listing(
                platform="Etsy",
                listing_id="mock-uncertain-1",
                title="Rechargeable reading light",
                item_price=21.99,
                review_count=8,
                position=47,
                observed_at=observed_at,
            ),
        ]
    )
    return listings


def _listing(
    *,
    platform: str,
    listing_id: str,
    title: str,
    item_price: float,
    review_count: int,
    position: int,
    observed_at: datetime,
    condition: ProductCondition = ProductCondition.NEW,
    pack_quantity: int | None = None,
) -> NormalizedMarketplaceListing:
    price = decimal_or_none(item_price)
    return NormalizedMarketplaceListing(
        provider="mock",
        platform=platform,
        listing_id=listing_id,
        source_url=None,
        title=title,
        normalized_title=normalize_text(title),
        description_excerpt=None,
        condition=condition,
        item_price=price,
        landed_price=price,
        currency="USD",
        image_urls=[],
        seller_name=platform,
        review_count=review_count,
        raw_rank_signals=[
            RankSignal(name="position", value=float(position), source="mock_fixture")
        ],
        pack_quantity=pack_quantity,
        observed_at=observed_at,
    )


def _product_name(request: MarketplaceDataProviderRequest) -> str:
    if request.product_profile.product_name:
        return request.product_profile.product_name.value
    return request.request.description.strip()
