"""SerpAPI-backed Google Shopping marketplace data provider."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from marketing_agent.domain.models.evidence import EvidenceRecord, EvidenceSource
from marketing_agent.domain.models.marketplace import (
    NormalizedMarketplaceListing,
    ProductCondition,
    RankSignal,
)
from marketing_agent.domain.models.provider import (
    CacheStatus,
    ProviderRunStatus,
    build_provider_telemetry,
)
from marketing_agent.domain.ports.marketplace_data_provider import (
    MarketplaceDataProviderError,
    MarketplaceDataProviderRequest,
    MarketplaceDataProviderResult,
)
from marketing_agent.domain.services.marketplace_query import build_marketplace_search_query
from marketing_agent.domain.services.product_matcher import (
    ProductMatcherConfig,
    build_validated_marketplace_snapshot,
    decimal_or_none,
    extract_model_number,
    normalize_text,
    parse_condition,
    parse_package,
)

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class SerpApiMarketplaceDataProvider:
    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float,
        location: str | None,
        matcher_config: ProductMatcherConfig | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.location = location
        self.matcher_config = matcher_config or ProductMatcherConfig()
        self.transport = transport

    async def fetch_snapshot(
        self, request: MarketplaceDataProviderRequest
    ) -> MarketplaceDataProviderResult:
        started_at = datetime.now(UTC)
        query = _build_query(request)
        params: dict[str, str] = {
            "engine": "google_shopping",
            "q": query,
            "api_key": self.api_key,
            "gl": _market_to_gl(request.request.market),
            "hl": _language_to_hl(request.request.language),
        }
        if self.location:
            params["location"] = self.location

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(SERPAPI_ENDPOINT, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MarketplaceDataProviderError("SerpAPI marketplace request failed") from exc

        raw_payload: Any = response.json()
        payload = cast(dict[str, Any], raw_payload) if isinstance(raw_payload, dict) else {}
        if payload.get("error"):
            raise MarketplaceDataProviderError(f"SerpAPI error: {payload['error']}")

        now = datetime.now(UTC)
        listings = _extract_listings(payload, observed_at=now)
        if not listings:
            raise MarketplaceDataProviderError("SerpAPI returned no Google Shopping offers")

        provider_evidence = [
            EvidenceRecord(
                id="ev-marketplace-serpapi-provider-run",
                source=EvidenceSource.MARKETPLACE_PROVIDER,
                source_reference="serpapi_google_shopping",
                observation=(
                    f"SerpAPI returned {len(listings)} Google Shopping candidate listing(s) "
                    "before deterministic product validation."
                ),
                quote=query,
                confidence=0.82,
                created_at=now,
                provider="serpapi_google_shopping",
                platform="google_shopping",
                provider_run_id=query,
            )
        ]
        product_name = _product_name(request)
        snapshot, validation_evidence = build_validated_marketplace_snapshot(
            request=request.request,
            profile=request.product_profile,
            listings=listings,
            source_provider="serpapi_google_shopping",
            source_query=query,
            title=f"Live Marketplace Snapshot for {product_name}",
            summary=(
                "Live Google Shopping candidate data grouped by merchant/source after "
                "deterministic product validation."
            ),
            is_live_data=True,
            methodology=(
                "Fetched Google Shopping results through SerpAPI, normalized provider-specific "
                "records into common listing objects, applied hard product-validation rules and "
                "deterministic similarity scoring, then aggregated only eligible primary matches."
            ),
            limitations=[
                (
                    "Google Shopping offer visibility is not equivalent to total marketplace "
                    "units sold."
                ),
                "observed_units_sold is only populated when a source result explicitly exposes a "
                "sold/bought signal.",
                (
                    "Rejected, uncertain, alternate-package, alternate-variant, and "
                    "alternate-condition listings are excluded from primary price ranges."
                ),
            ],
            base_warnings=[
                "Live provider data used; verify critical sales and pricing decisions against "
                "marketplace APIs or seller dashboards."
            ],
            retrieved_at=now,
            matcher_config=self.matcher_config,
        )
        return MarketplaceDataProviderResult(
            snapshot=snapshot,
            evidence=[*provider_evidence, *validation_evidence],
            warnings=snapshot.warnings,
            telemetry=build_provider_telemetry(
                provider="serpapi_google_shopping",
                operation="marketplace_snapshot",
                started_at=started_at,
                status=ProviderRunStatus.SUCCEEDED,
                result_count=len(snapshot.validated_listings),
                cache_status=CacheStatus.BYPASS,
                correlation_id=query,
            ),
        )


def _extract_listings(payload: Any, *, observed_at: datetime) -> list[NormalizedMarketplaceListing]:
    raw_results: list[dict[str, Any]] = []
    payload_object = cast(dict[str, Any], payload) if isinstance(payload, dict) else {}
    raw_results.extend(_as_dict_list(payload_object.get("shopping_results")))
    for category in _as_dict_list(payload_object.get("categorized_shopping_results")):
        raw_results.extend(_as_dict_list(category.get("shopping_results")))

    listings: list[NormalizedMarketplaceListing] = []
    for fallback_position, raw in enumerate(raw_results, start=1):
        source = _clean_text(raw.get("source"))
        title = _clean_text(raw.get("title"))
        if not source or not title:
            continue
        text_parts = [
            title,
            _clean_text(raw.get("snippet")),
            _clean_text(raw.get("tag")),
            " ".join(str(item) for item in raw.get("extensions", []) if isinstance(item, str)),
        ]
        text = " ".join(part for part in text_parts if part)
        sales_signal, units_sold = _extract_sales_signal(text)
        position = _int_or_default(raw.get("position"), fallback_position)
        pack_quantity, unit_quantity, unit_type = parse_package(text)
        condition = parse_condition(text) or ProductCondition.NEW
        rank_signals = [RankSignal(name="position", value=float(position), source="serpapi")]
        if units_sold is not None:
            rank_signals.append(
                RankSignal(name="units_sold", value=float(units_sold), source=sales_signal)
            )
        image_url = _clean_text(raw.get("thumbnail")) or _clean_text(raw.get("image"))
        listings.append(
            NormalizedMarketplaceListing(
                provider="serpapi_google_shopping",
                platform=source,
                listing_id=_listing_id(source=source, position=position, title=title),
                source_url=_clean_text(raw.get("link"))
                or _clean_text(raw.get("product_link"))
                or _clean_text(raw.get("serpapi_product_api")),
                title=title,
                normalized_title=normalize_text(title),
                description_excerpt=_clean_text(raw.get("snippet")),
                provider_brand=_clean_text(raw.get("brand")),
                manufacturer=_clean_text(raw.get("manufacturer")),
                model_number=extract_model_number(title, _clean_text(raw.get("snippet"))),
                pack_quantity=pack_quantity,
                unit_quantity=unit_quantity,
                unit_type=unit_type,
                condition=condition,
                item_price=decimal_or_none(raw.get("extracted_price")),
                shipping_price=decimal_or_none(raw.get("extracted_shipping")),
                currency=_currency(raw),
                image_urls=[image_url] if image_url else [],
                seller_name=source,
                rating=_float_or_none(raw.get("rating")),
                review_count=_int_or_none(raw.get("reviews")),
                raw_rank_signals=rank_signals,
                raw_provider_payload_reference=f"shopping_results[{fallback_position - 1}]",
                observed_at=observed_at,
            )
        )
    return listings


def _build_query(request: MarketplaceDataProviderRequest) -> str:
    return build_marketplace_search_query(
        request=request.request,
        profile=request.product_profile,
    )


def _product_name(request: MarketplaceDataProviderRequest) -> str:
    if request.product_profile.product_name:
        return request.product_profile.product_name.value
    return request.request.description.strip()


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = cast(list[Any], value)
    return [cast(dict[str, Any], item) for item in items if isinstance(item, dict)]


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _int_or_default(value: Any, default: int) -> int:
    parsed = _int_or_none(value)
    return parsed if parsed is not None else default


def _extract_sales_signal(text: str) -> tuple[str | None, int | None]:
    patterns = (
        r"(?P<count>\d+(?:[,.]\d+)?)(?P<suffix>[kKmM])?\+?\s*(?:sold|bought|purchased)",
        r"(?P<count>\d+(?:[,.]\d+)?)(?P<suffix>[kKmM])?\+?\s*(?:orders)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            units = _parse_compact_number(match.group("count"), match.group("suffix"))
            return match.group(0), units
    return None, None


def _parse_compact_number(count: str, suffix: str | None) -> int:
    value = float(count.replace(",", ""))
    if suffix and suffix.lower() == "k":
        value *= 1_000
    if suffix and suffix.lower() == "m":
        value *= 1_000_000
    return int(value)


def _listing_id(*, source: str, position: int, title: str) -> str:
    return f"serpapi-{_slug(source)}-{position}-{_slug(title)[:30]}"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60] or "unknown"


def _currency(raw: dict[str, Any]) -> str | None:
    currency = _clean_text(raw.get("currency"))
    if currency and len(currency) == 3:
        return currency.upper()
    price = _clean_text(raw.get("price"))
    if price and "$" in price:
        return "USD"
    return "USD"


def _market_to_gl(market: str | None) -> str:
    if not market:
        return "us"
    return market.split("-", 1)[0].lower()


def _language_to_hl(language: str | None) -> str:
    if not language:
        return "en"
    return language.split("-", 1)[0].lower()
