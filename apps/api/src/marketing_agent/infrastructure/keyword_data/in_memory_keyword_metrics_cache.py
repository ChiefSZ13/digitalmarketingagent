"""In-memory keyword metrics cache for development and tests."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from marketing_agent.domain.ports.keyword_data_provider import KeywordProviderRecord
from marketing_agent.domain.ports.keyword_metrics_cache import KeywordMetricsCache


@dataclass(frozen=True)
class _CacheEntry:
    record: KeywordProviderRecord
    expires_at: datetime


class InMemoryKeywordMetricsCache(KeywordMetricsCache):
    def __init__(self) -> None:
        self._records: dict[str, _CacheEntry] = {}

    async def get(self, key: str) -> KeywordProviderRecord | None:
        entry = self._records.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self._records.pop(key, None)
            return None
        return entry.record

    async def set(self, key: str, record: KeywordProviderRecord, ttl_seconds: int) -> None:
        self._records[key] = _CacheEntry(
            record=record,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
