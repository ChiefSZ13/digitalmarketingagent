"""Smoke-test the live marketplace provider without exposing credentials."""

from __future__ import annotations

import argparse
import asyncio

from marketing_agent.config import get_settings
from marketing_agent.domain.models.evidence import (
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.run import ProductAnalysisRequest
from marketing_agent.domain.ports.marketplace_data_provider import (
    MarketplaceDataProviderRequest,
)
from marketing_agent.infrastructure.marketplace.serpapi_marketplace_data_provider import (
    SerpApiMarketplaceDataProvider,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-credentials", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.serpapi_api_key:
        message = "SKIP: SERPAPI_API_KEY is not configured."
        if args.require_credentials:
            raise SystemExit(message)
        print(message)
        return
    asyncio.run(_run(settings.serpapi_api_key, settings.marketplace_timeout_seconds))


async def _run(api_key: str, timeout_seconds: float) -> None:
    provider = SerpApiMarketplaceDataProvider(
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        location="United States",
    )
    result = await provider.fetch_snapshot(
        MarketplaceDataProviderRequest(
            request=ProductAnalysisRequest(
                description="Portable rechargeable desk lamp",
                market="US",
                language="en-US",
            ),
            product_profile=_profile(),
        )
    )
    snapshot = result.snapshot
    if not snapshot.validated_listings:
        raise SystemExit("FAIL: provider returned no normalized listings.")
    if not snapshot.retrieved_at:
        raise SystemExit("FAIL: snapshot did not include a retrieval timestamp.")
    for validation in snapshot.validated_listings:
        listing = validation.listing
        if not listing.provider or not listing.platform or not listing.listing_id:
            raise SystemExit("FAIL: normalized listing is missing source identity fields.")
        if listing.observed_at is None:
            raise SystemExit("FAIL: normalized listing is missing observed_at.")
    for price in snapshot.price_estimates:
        if price.currency and len(price.currency) != 3:
            raise SystemExit("FAIL: price estimate currency is not normalized.")
        if (
            price.price_low is not None
            and price.price_high is not None
            and price.price_low > price.price_high
        ):
            raise SystemExit("FAIL: price range is not parseable.")
    print(
        "OK: marketplace provider returned "
        f"{len(snapshot.validated_listings)} normalized listings and "
        f"{len(snapshot.price_estimates)} price estimates."
    )


def _profile() -> ProductProfile:
    evidence = [
        EvidenceRecord(
            id="ev-smoke-1",
            source=EvidenceSource.USER_DESCRIPTION,
            source_reference="smoke-test",
            observation="Smoke-test product description.",
            confidence=1.0,
        )
    ]
    linked = EvidenceLinkedText(
        value="Portable rechargeable desk lamp",
        evidence_ids=["ev-smoke-1"],
        confidence=0.9,
    )
    return ProductProfile(
        product_name=linked,
        category=EvidenceLinkedText(
            value="Desk lamp",
            evidence_ids=["ev-smoke-1"],
            confidence=0.9,
        ),
        marketplace_search_query=EvidenceLinkedText(
            value="portable rechargeable desk lamp",
            evidence_ids=["ev-smoke-1"],
            confidence=0.9,
        ),
        summary=linked,
        features=[
            EvidenceLinkedText(
                value="rechargeable",
                evidence_ids=["ev-smoke-1"],
                confidence=0.8,
            )
        ],
        use_cases=[
            EvidenceLinkedText(
                value="desk lighting",
                evidence_ids=["ev-smoke-1"],
                confidence=0.8,
            )
        ],
        evidence=evidence,
        overall_confidence=0.9,
    )


if __name__ == "__main__":
    main()
