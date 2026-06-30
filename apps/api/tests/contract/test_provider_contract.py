import pytest

from marketing_agent.domain.models.run import ImageInput, ProductAnalysisRequest
from marketing_agent.domain.ports.keyword_data_provider import KeywordEnrichmentRequest
from marketing_agent.domain.ports.perception_provider import (
    PerceptionProviderRequest,
    ProviderImage,
)
from marketing_agent.infrastructure.ai.mock_perception_provider import MockPerceptionProvider
from marketing_agent.infrastructure.keyword_data.mock_keyword_metrics_provider import (
    MockKeywordMetricsProvider,
)
from tests.conftest import make_png_bytes


@pytest.mark.asyncio
async def test_mock_provider_returns_valid_domain_profile() -> None:
    image = ImageInput(
        index=1,
        filename="image-1.png",
        mime_type="image/png",
        content_hash="abc",
        byte_size=10,
        width=8,
        height=8,
    )
    result = await MockPerceptionProvider().analyze(
        PerceptionProviderRequest(
            request=ProductAnalysisRequest(description="Portable rechargeable desk lamp"),
            images=[
                ProviderImage(index=1, mime_type="image/png", data=make_png_bytes(), input=image)
            ],
        )
    )
    assert result.product_profile.evidence
    assert result.metadata.provider == "mock"


@pytest.mark.asyncio
async def test_mock_keyword_metrics_provider_returns_normalized_records() -> None:
    result = await MockKeywordMetricsProvider().enrich(
        KeywordEnrichmentRequest(
            keywords=["Rechargeable desk lamp", "desk lamp price"],
            market="US",
            language="en",
            currency="USD",
            max_keywords=2,
        )
    )

    assert result.records
    assert result.telemetry.provider == "mock_keyword_metrics"
    assert result.records[0].keyword == "rechargeable desk lamp"
    assert result.records[0].average_monthly_searches is not None
    assert result.records[0].monthly_history
    assert result.records[0].related_terms
