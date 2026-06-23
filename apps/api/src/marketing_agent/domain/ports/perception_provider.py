"""Domain-facing protocol for multimodal product perception."""

from dataclasses import dataclass
from typing import Protocol

from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.run import ImageInput, ProductAnalysisRequest, ProviderMetadata


@dataclass(frozen=True)
class ProviderImage:
    index: int
    mime_type: str
    data: bytes
    input: ImageInput


@dataclass(frozen=True)
class PerceptionProviderRequest:
    request: ProductAnalysisRequest
    images: list[ProviderImage]


@dataclass(frozen=True)
class ProviderPerceptionResult:
    product_profile: ProductProfile
    metadata: ProviderMetadata
    warnings: list[str]


class PerceptionProvider(Protocol):
    async def analyze(self, request: PerceptionProviderRequest) -> ProviderPerceptionResult:
        """Analyze product inputs and return a schema-valid product profile."""
        raise NotImplementedError
