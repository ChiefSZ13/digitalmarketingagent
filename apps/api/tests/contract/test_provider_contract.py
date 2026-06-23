import pytest

from marketing_agent.domain.models.run import ImageInput, ProductAnalysisRequest
from marketing_agent.domain.ports.perception_provider import (
    PerceptionProviderRequest,
    ProviderImage,
)
from marketing_agent.infrastructure.ai.mock_perception_provider import MockPerceptionProvider
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
