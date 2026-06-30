"""Disabled keyword metrics provider."""

from datetime import UTC, datetime

from marketing_agent.domain.models.provider import (
    CacheStatus,
    ProviderRunStatus,
    build_provider_telemetry,
)
from marketing_agent.domain.ports.keyword_data_provider import (
    KeywordEnrichmentProviderResult,
    KeywordEnrichmentRequest,
    KeywordMetricsProvider,
)


class NullKeywordMetricsProvider(KeywordMetricsProvider):
    async def enrich(self, request: KeywordEnrichmentRequest) -> KeywordEnrichmentProviderResult:
        started_at = datetime.now(UTC)
        return KeywordEnrichmentProviderResult(
            records=[],
            warnings=["Keyword metrics provider is disabled."],
            telemetry=build_provider_telemetry(
                provider="null",
                operation="keyword_enrichment",
                started_at=started_at,
                status=ProviderRunStatus.SKIPPED,
                result_count=0,
                cache_status=CacheStatus.BYPASS,
                correlation_id=request.correlation_id,
            ),
        )
