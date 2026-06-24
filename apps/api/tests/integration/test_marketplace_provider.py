import httpx
import pytest

from marketing_agent.domain.models.evidence import (
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.run import ProductAnalysisRequest
from marketing_agent.domain.ports.marketplace_data_provider import (
    MarketplaceDataProviderError,
    MarketplaceDataProviderRequest,
)
from marketing_agent.infrastructure.marketplace.mock_marketplace_data_provider import (
    MockMarketplaceDataProvider,
)
from marketing_agent.infrastructure.marketplace.serpapi_marketplace_data_provider import (
    SerpApiMarketplaceDataProvider,
)


def _profile() -> ProductProfile:
    return ProductProfile(
        product_name=EvidenceLinkedText(
            value="Portable Rechargeable Desk Lamp",
            evidence_ids=["ev-1"],
            confidence=0.8,
        ),
        category=EvidenceLinkedText(value="Lighting", evidence_ids=["ev-1"], confidence=0.8),
        summary=EvidenceLinkedText(value="Lamp summary", evidence_ids=["ev-1"], confidence=0.8),
        evidence=[
            EvidenceRecord(
                id="ev-1",
                source=EvidenceSource.USER_DESCRIPTION,
                source_reference="description",
                observation="Description",
                confidence=0.9,
            )
        ],
        overall_confidence=0.7,
    )


def _nike_profile() -> ProductProfile:
    return ProductProfile(
        product_name=EvidenceLinkedText(
            value="Nike running shoes",
            evidence_ids=["ev-1"],
            confidence=0.78,
        ),
        brand=EvidenceLinkedText(value="Nike", evidence_ids=["ev-1"], confidence=0.92),
        category=EvidenceLinkedText(value="Shoes", evidence_ids=["ev-1"], confidence=0.84),
        marketplace_search_query=EvidenceLinkedText(
            value="Nike P4000",
            evidence_ids=["ev-1"],
            confidence=0.9,
        ),
        summary=EvidenceLinkedText(
            value="Nike shoe summary", evidence_ids=["ev-1"], confidence=0.8
        ),
        observed_facts=[
            EvidenceLinkedText(
                value="Model number: P4000",
                evidence_ids=["ev-1"],
                confidence=0.88,
            )
        ],
        evidence=[
            EvidenceRecord(
                id="ev-1",
                source=EvidenceSource.MODEL_INFERENCE,
                source_reference="profile",
                observation="Normalized product identity",
                confidence=0.9,
            )
        ],
        overall_confidence=0.82,
    )


def _jordan_profile() -> ProductProfile:
    return ProductProfile(
        product_name=EvidenceLinkedText(
            value="Nike Air Jordan 5 Retro 'University Blue'",
            evidence_ids=["ev-1"],
            confidence=0.86,
        ),
        brand=EvidenceLinkedText(value="Nike", evidence_ids=["ev-1"], confidence=0.9),
        category=EvidenceLinkedText(value="Shoes", evidence_ids=["ev-1"], confidence=0.82),
        marketplace_search_query=EvidenceLinkedText(
            value="Nike Air Jordan 5",
            evidence_ids=["ev-1"],
            confidence=0.9,
        ),
        summary=EvidenceLinkedText(
            value="Air Jordan 5 sneaker summary",
            evidence_ids=["ev-1"],
            confidence=0.8,
        ),
        evidence=[
            EvidenceRecord(
                id="ev-1",
                source=EvidenceSource.MODEL_INFERENCE,
                source_reference="profile",
                observation="Normalized sneaker identity",
                confidence=0.9,
            )
        ],
        overall_confidence=0.82,
    )


@pytest.mark.asyncio
async def test_mock_marketplace_provider_returns_fixed_snapshot() -> None:
    result = await MockMarketplaceDataProvider().fetch_snapshot(
        MarketplaceDataProviderRequest(
            request=ProductAnalysisRequest(
                description="Portable rechargeable desk lamp",
                market="US",
            ),
            product_profile=_profile(),
        )
    )

    assert result.snapshot.source_provider == "mock"
    assert result.snapshot.is_live_data is False
    assert len(result.snapshot.platform_rankings) == 10
    assert result.evidence[0].source == EvidenceSource.MARKETPLACE_PROVIDER


@pytest.mark.asyncio
async def test_serpapi_marketplace_provider_prefers_normalized_product_identity() -> None:
    payload = {
        "shopping_results": [
            {
                "position": 1,
                "title": "Nike P4000 Shoe",
                "source": "Nike",
                "extracted_price": 119.99,
                "link": "https://example.test/nike-p4000",
                "reviews": 25,
            }
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "Nike P4000"
        return httpx.Response(200, json=payload)

    provider = SerpApiMarketplaceDataProvider(
        api_key="test-key",
        timeout_seconds=5,
        location=None,
        transport=httpx.MockTransport(handler),
    )
    result = await provider.fetch_snapshot(
        MarketplaceDataProviderRequest(
            request=ProductAnalysisRequest(
                description=(
                    "I need ads for these shoes. The description is noisy and should not "
                    "be used directly as a shopping query."
                ),
                brand="Human-entered Nike",
                category_hint="performance running shoes",
                market="US",
            ),
            product_profile=_nike_profile(),
        )
    )

    assert result.snapshot.source_query == "Nike P4000"


@pytest.mark.asyncio
async def test_serpapi_marketplace_provider_uses_model_generated_core_query() -> None:
    payload = {
        "shopping_results": [
            {
                "position": 1,
                "title": "Nike Air Jordan 5",
                "source": "StockX",
                "extracted_price": 210.0,
                "link": "https://example.test/air-jordan-5",
                "reviews": 50,
            }
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "Nike Air Jordan 5"
        return httpx.Response(200, json=payload)

    provider = SerpApiMarketplaceDataProvider(
        api_key="test-key",
        timeout_seconds=5,
        location=None,
        transport=httpx.MockTransport(handler),
    )
    result = await provider.fetch_snapshot(
        MarketplaceDataProviderRequest(
            request=ProductAnalysisRequest(
                description="Nike Air Jordan 5 Retro University Blue",
                market="US",
            ),
            product_profile=_jordan_profile(),
        )
    )

    assert result.snapshot.source_query == "Nike Air Jordan 5"


@pytest.mark.asyncio
async def test_serpapi_marketplace_provider_maps_google_shopping_results() -> None:
    payload = {
        "shopping_results": [
            {
                "position": 1,
                "title": "Portable LED Desk Lamp",
                "source": "Amazon",
                "extracted_price": 24.99,
                "link": "https://example.test/amazon-lamp",
                "rating": 4.5,
                "reviews": 1200,
                "extensions": ["1K+ bought in past month"],
            },
            {
                "position": 2,
                "title": "Rechargeable Desk Lamp",
                "source": "Walmart",
                "extracted_price": 29.99,
                "link": "https://example.test/walmart-lamp",
                "rating": 4.2,
                "reviews": 250,
            },
            {
                "position": 3,
                "title": "Portable Desk Lamp",
                "source": "Amazon",
                "extracted_price": 19.99,
                "link": "https://example.test/amazon-lamp-2",
                "reviews": 400,
            },
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["engine"] == "google_shopping"
        assert request.url.params["q"] == "Portable Rechargeable Desk Lamp"
        return httpx.Response(200, json=payload)

    provider = SerpApiMarketplaceDataProvider(
        api_key="test-key",
        timeout_seconds=5,
        location=None,
        transport=httpx.MockTransport(handler),
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

    assert result.snapshot.source_provider == "serpapi_google_shopping"
    assert result.snapshot.is_live_data is True
    assert result.snapshot.platform_rankings[0].platform == "Amazon"
    assert result.snapshot.platform_rankings[0].observed_offer_count == 2
    assert result.snapshot.platform_rankings[0].observed_units_sold == 1000
    assert result.snapshot.price_estimates[0].price_low == 19.99
    assert result.snapshot.price_estimates[0].price_high == 24.99
    assert result.evidence[0].id.startswith("ev-marketplace-serpapi-")


@pytest.mark.asyncio
async def test_serpapi_marketplace_provider_fails_visibly_on_empty_results() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"shopping_results": []})

    provider = SerpApiMarketplaceDataProvider(
        api_key="test-key",
        timeout_seconds=5,
        location=None,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(MarketplaceDataProviderError):
        await provider.fetch_snapshot(
            MarketplaceDataProviderRequest(
                request=ProductAnalysisRequest(description="Portable lamp"),
                product_profile=_profile(),
            )
        )
