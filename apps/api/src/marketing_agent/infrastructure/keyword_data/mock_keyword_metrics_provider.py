"""Deterministic keyword metrics provider for tests and offline development."""

from datetime import UTC, datetime

from marketing_agent.domain.models.keyword import KeywordCompetition, KeywordMonthlyMetric
from marketing_agent.domain.models.provider import (
    CacheStatus,
    ProviderRunStatus,
    build_provider_telemetry,
)
from marketing_agent.domain.ports.keyword_data_provider import (
    KeywordEnrichmentProviderResult,
    KeywordEnrichmentRequest,
    KeywordMetricsProvider,
    KeywordProviderRecord,
)
from marketing_agent.domain.services.keyword_normalizer import normalize_keyword


class MockKeywordMetricsProvider(KeywordMetricsProvider):
    def __init__(self, *, scenario: str = "complete") -> None:
        self.scenario = scenario

    async def enrich(self, request: KeywordEnrichmentRequest) -> KeywordEnrichmentProviderResult:
        started_at = datetime.now(UTC)
        records: list[KeywordProviderRecord] = []
        warnings: list[str] = []
        for index, keyword in enumerate(request.keywords[: request.max_keywords], start=1):
            normalized = normalize_keyword(keyword)
            if self.scenario == "empty":
                continue
            volume: int | None = max(90, 2400 - index * 140)
            cpc_low: float | None = round(0.45 + index * 0.08, 2)
            cpc_high: float | None = round(cpc_low + 1.35, 2)
            competition: KeywordCompetition | None = (
                KeywordCompetition.LOW
                if index % 3 == 1
                else KeywordCompetition.MEDIUM
                if index % 3 == 2
                else KeywordCompetition.HIGH
            )
            monthly_history = _monthly_history(volume or 0, index)
            if self.scenario == "missing":
                cpc_low = None
                cpc_high = None
                monthly_history = []
            if self.scenario == "partial" and index % 2 == 0:
                warnings.append(f"Mock provider omitted metrics for '{keyword}'.")
                continue
            records.append(
                KeywordProviderRecord(
                    keyword=normalized,
                    provider="mock_keyword_metrics",
                    provider_record_id=f"mock-keyword-{index}",
                    average_monthly_searches=volume,
                    competition=competition,
                    competition_index=_competition_index(competition),
                    cpc_low=cpc_low,
                    cpc_high=cpc_high,
                    currency=request.currency,
                    monthly_history=monthly_history,
                    related_terms=_related_terms(normalized),
                    source_confidence=0.78,
                )
            )

        status = ProviderRunStatus.SUCCEEDED
        if warnings or len(records) < min(len(request.keywords), request.max_keywords):
            status = ProviderRunStatus.PARTIAL_SUCCESS
        return KeywordEnrichmentProviderResult(
            records=records,
            warnings=warnings,
            telemetry=build_provider_telemetry(
                provider="mock_keyword_metrics",
                operation="keyword_enrichment",
                started_at=started_at,
                status=status,
                result_count=len(records),
                cache_status=CacheStatus.BYPASS,
                correlation_id=request.correlation_id,
            ),
        )


def _monthly_history(base: int, offset: int) -> list[KeywordMonthlyMetric]:
    if base <= 0:
        return []
    points: list[KeywordMonthlyMetric] = []
    year = 2026
    for month in range(1, 7):
        searches = max(0, base - 240 + month * 80 + offset * 12)
        points.append(KeywordMonthlyMetric(year=year, month=month, searches=searches))
    return points


def _competition_index(competition: KeywordCompetition | None) -> float | None:
    if competition is None:
        return None
    return {
        KeywordCompetition.LOW: 0.25,
        KeywordCompetition.MEDIUM: 0.55,
        KeywordCompetition.HIGH: 0.82,
        KeywordCompetition.UNKNOWN: None,
    }[competition]


def _related_terms(normalized: str) -> list[str]:
    tokens = normalized.split()
    if len(tokens) < 2:
        return []
    head = " ".join(tokens[:2])
    tail = " ".join(tokens[-2:])
    return list(dict.fromkeys([f"{head} deals", f"best {tail}", f"{normalized} reviews"]))
