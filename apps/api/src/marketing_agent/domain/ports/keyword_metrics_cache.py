"""Cache protocol for normalized keyword provider records."""

from typing import Protocol

from marketing_agent.domain.ports.keyword_data_provider import KeywordProviderRecord


class KeywordMetricsCache(Protocol):
    async def get(self, key: str) -> KeywordProviderRecord | None:
        """Return a cached provider record when it is still fresh."""
        raise NotImplementedError

    async def set(self, key: str, record: KeywordProviderRecord, ttl_seconds: int) -> None:
        """Persist a normalized provider record for a bounded TTL."""
        raise NotImplementedError
