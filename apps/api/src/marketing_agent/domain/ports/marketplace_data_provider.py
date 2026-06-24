"""Domain-facing protocol for marketplace data enrichment."""

from dataclasses import dataclass
from typing import Protocol

from marketing_agent.domain.models.evidence import EvidenceRecord
from marketing_agent.domain.models.marketplace import MarketplaceSnapshot
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.run import ProductAnalysisRequest


@dataclass(frozen=True)
class MarketplaceDataProviderRequest:
    request: ProductAnalysisRequest
    product_profile: ProductProfile


@dataclass(frozen=True)
class MarketplaceDataProviderResult:
    snapshot: MarketplaceSnapshot
    evidence: list[EvidenceRecord]
    warnings: list[str]


class MarketplaceDataProviderError(RuntimeError):
    """Raised when a marketplace provider cannot return usable normalized data."""


class MarketplaceDataProvider(Protocol):
    async def fetch_snapshot(
        self, request: MarketplaceDataProviderRequest
    ) -> MarketplaceDataProviderResult:
        """Fetch marketplace data and normalize it into the fixed snapshot schema."""
        raise NotImplementedError
