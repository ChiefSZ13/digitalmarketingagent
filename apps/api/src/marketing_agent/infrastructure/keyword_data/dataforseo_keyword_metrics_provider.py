"""DataForSEO-backed keyword metrics provider."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import httpx

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
    KeywordMetricsProviderError,
    KeywordProviderRecord,
)
from marketing_agent.domain.services.keyword_normalizer import normalize_keyword

DATAFORSEO_SEARCH_VOLUME_URL = (
    "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"
)


class DataForSeoKeywordMetricsProvider(KeywordMetricsProvider):
    def __init__(
        self,
        *,
        login: str,
        password: str,
        timeout_seconds: float,
        retries: int,
        location_name: str,
        language_name: str,
    ) -> None:
        self.login = login
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.location_name = location_name
        self.language_name = language_name

    async def enrich(self, request: KeywordEnrichmentRequest) -> KeywordEnrichmentProviderResult:
        started_at = datetime.now(UTC)
        payload = [
            {
                "keywords": request.keywords[: request.max_keywords],
                "location_name": self.location_name,
                "language_name": self.language_name,
            }
        ]
        response_payload = await self._post_with_retries(payload)
        records, warnings = _parse_records(
            response_payload,
            currency=request.currency,
        )
        status = ProviderRunStatus.SUCCEEDED if records else ProviderRunStatus.PARTIAL_SUCCESS
        if warnings:
            status = ProviderRunStatus.PARTIAL_SUCCESS
        return KeywordEnrichmentProviderResult(
            records=records,
            warnings=warnings,
            telemetry=build_provider_telemetry(
                provider="dataforseo",
                operation="keyword_enrichment",
                started_at=started_at,
                status=status,
                result_count=len(records),
                cache_status=CacheStatus.BYPASS,
                correlation_id=request.correlation_id,
            ),
        )

    async def _post_with_retries(self, payload: list[dict[str, Any]]) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        DATAFORSEO_SEARCH_VOLUME_URL,
                        auth=(self.login, self.password),
                        json=payload,
                    )
                if response.status_code in {400, 401, 403}:
                    raise KeywordMetricsProviderError(
                        f"DataForSEO rejected keyword request with status {response.status_code}"
                    )
                if response.status_code in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                response.raise_for_status()
                return response.json()
            except KeywordMetricsProviderError:
                raise
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                await asyncio.sleep(min(2.0, 0.25 * 2**attempt))
        raise KeywordMetricsProviderError("DataForSEO keyword request failed") from last_error


def _parse_records(payload: Any, *, currency: str) -> tuple[list[KeywordProviderRecord], list[str]]:
    warnings: list[str] = []
    records: list[KeywordProviderRecord] = []
    if not isinstance(payload, dict):
        raise KeywordMetricsProviderError("DataForSEO response was not a JSON object")
    payload_object = cast(dict[str, Any], payload)
    tasks_value = payload_object.get("tasks")
    if not isinstance(tasks_value, list):
        raise KeywordMetricsProviderError("DataForSEO response did not include tasks")
    for task_index, task_value in enumerate(cast(list[Any], tasks_value)):
        if not isinstance(task_value, dict):
            continue
        task = cast(dict[str, Any], task_value)
        status_code = _optional_int(task.get("status_code")) or 0
        if status_code >= 40_000:
            warnings.append(f"DataForSEO task {task_index + 1} returned status {status_code}.")
        result_value = task.get("result")
        if not isinstance(result_value, list):
            continue
        for item_index, item_value in enumerate(cast(list[Any], result_value)):
            if not isinstance(item_value, dict):
                continue
            item = cast(dict[str, Any], item_value)
            keyword = item.get("keyword")
            if not isinstance(keyword, str) or not keyword.strip():
                continue
            normalized = normalize_keyword(keyword)
            records.append(
                KeywordProviderRecord(
                    keyword=normalized,
                    provider="dataforseo",
                    provider_record_id=str(
                        item.get("keyword_info_hash")
                        or item.get("id")
                        or f"task-{task_index + 1}-item-{item_index + 1}"
                    ),
                    average_monthly_searches=_optional_int(
                        item.get("search_volume") or item.get("avg_monthly_searches")
                    ),
                    competition=_competition(item.get("competition")),
                    competition_index=_competition_index(item.get("competition_index")),
                    cpc_low=_optional_float(
                        item.get("low_top_of_page_bid") or item.get("cpc_low") or item.get("cpc")
                    ),
                    cpc_high=_optional_float(
                        item.get("high_top_of_page_bid") or item.get("cpc_high") or item.get("cpc")
                    ),
                    currency=currency,
                    monthly_history=_monthly_history(item.get("monthly_searches")),
                    related_terms=_related_terms(item),
                    source_confidence=0.85,
                )
            )
    return records, warnings


def _competition(value: Any) -> KeywordCompetition | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"low", "0"}:
        return KeywordCompetition.LOW
    if normalized in {"medium", "med", "1"}:
        return KeywordCompetition.MEDIUM
    if normalized in {"high", "2"}:
        return KeywordCompetition.HIGH
    return KeywordCompetition.UNKNOWN


def _competition_index(value: Any) -> float | None:
    parsed = _optional_float(value)
    if parsed is None:
        return None
    if parsed > 1.0:
        parsed = parsed / 100
    return max(0.0, min(1.0, parsed))


def _optional_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _monthly_history(value: Any) -> list[KeywordMonthlyMetric]:
    if not isinstance(value, list):
        return []
    history: list[KeywordMonthlyMetric] = []
    for item_value in cast(list[Any], value):
        if not isinstance(item_value, dict):
            continue
        item = cast(dict[str, Any], item_value)
        year = _optional_int(item.get("year"))
        month = _optional_int(item.get("month"))
        searches = _optional_int(
            item.get("search_volume") or item.get("searches") or item.get("volume")
        )
        if year is None or month is None or searches is None:
            continue
        if 2000 <= year <= 2100 and 1 <= month <= 12:
            history.append(KeywordMonthlyMetric(year=year, month=month, searches=searches))
    return history


def _related_terms(item: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in ("related_keywords", "keyword_ideas", "related_terms"):
        value = item.get(key)
        if isinstance(value, list):
            for term_value in cast(list[Any], value):
                if isinstance(term_value, str) and term_value.strip():
                    terms.append(term_value.strip())
                elif isinstance(term_value, dict):
                    term_object = cast(dict[str, Any], term_value)
                    keyword = term_object.get("keyword")
                    if isinstance(keyword, str) and keyword.strip():
                        terms.append(keyword.strip())
    return list(dict.fromkeys(terms))
