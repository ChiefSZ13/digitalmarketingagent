"""Future keyword data provider port kept out of MVP 1B runtime."""

from typing import Protocol

from marketing_agent.domain.models.keyword import EnrichmentMetrics


class KeywordDataProvider(Protocol):
    async def enrich(self, normalized_keyword: str) -> EnrichmentMetrics:
        """Return optional third-party keyword metrics."""
        raise NotImplementedError
