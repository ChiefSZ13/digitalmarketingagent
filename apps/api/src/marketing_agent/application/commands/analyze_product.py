"""Command objects for product analysis."""

from dataclasses import dataclass

from marketing_agent.domain.models.run import ProductAnalysisRequest


@dataclass(frozen=True)
class RawImageInput:
    filename: str
    content_type: str | None
    data: bytes


@dataclass(frozen=True)
class AnalyzeProductCommand:
    request: ProductAnalysisRequest
    images: list[RawImageInput]
