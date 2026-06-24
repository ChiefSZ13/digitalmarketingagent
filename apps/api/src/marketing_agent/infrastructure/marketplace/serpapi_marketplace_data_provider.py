"""SerpAPI-backed Google Shopping marketplace data provider."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from marketing_agent.domain.models.evidence import EvidenceRecord, EvidenceSource
from marketing_agent.domain.models.marketplace import (
    MarketplacePlatformEstimate,
    MarketplacePriceEstimate,
    MarketplaceSnapshot,
)
from marketing_agent.domain.ports.marketplace_data_provider import (
    MarketplaceDataProviderError,
    MarketplaceDataProviderRequest,
    MarketplaceDataProviderResult,
)

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


@dataclass(frozen=True)
class _ShoppingOffer:
    position: int
    title: str
    source: str
    price: float | None
    link: str | None
    rating: float | None
    reviews: int | None
    sales_signal: str | None
    units_sold: int | None


class SerpApiMarketplaceDataProvider:
    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float,
        location: str | None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.location = location
        self.transport = transport

    async def fetch_snapshot(
        self, request: MarketplaceDataProviderRequest
    ) -> MarketplaceDataProviderResult:
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

        offers = _extract_offers(payload)
        if not offers:
            raise MarketplaceDataProviderError("SerpAPI returned no Google Shopping offers")

        now = datetime.now(UTC)
        evidence, rankings, prices = _build_snapshot_parts(
            offers=offers,
            query=query,
            retrieved_at=now,
        )
        product_name = _product_name(request)
        snapshot = MarketplaceSnapshot(
            title=f"Live Marketplace Snapshot for {product_name}",
            summary=(
                "Live Google Shopping offer data grouped by merchant/source. "
                "Rank is based on observed offer presence, result position, reviews, "
                "and price coverage."
            ),
            source_provider="serpapi_google_shopping",
            source_query=query,
            retrieved_at=now,
            is_live_data=True,
            methodology=(
                "Fetched Google Shopping results through SerpAPI, grouped offers by source, "
                "then ranked sources by observed offer count, best result position, review count, "
                "and price availability."
            ),
            limitations=[
                "Google Shopping offer visibility is not equivalent to total marketplace "
                "units sold.",
                "observed_units_sold is only populated when a source result explicitly "
                "exposes a sold/bought signal.",
                "Price ranges reflect observed offers returned by the provider at retrieval time.",
            ],
            platform_rankings=rankings,
            price_estimates=prices,
            warnings=[
                "Live provider data used; verify critical sales and pricing decisions "
                "against marketplace APIs or seller dashboards."
            ],
            overall_confidence=_overall_confidence(rankings),
        )
        return MarketplaceDataProviderResult(
            snapshot=snapshot,
            evidence=evidence,
            warnings=snapshot.warnings,
        )


def _extract_offers(payload: Any) -> list[_ShoppingOffer]:
    raw_results: list[dict[str, Any]] = []
    payload_object = cast(dict[str, Any], payload) if isinstance(payload, dict) else {}
    raw_results.extend(_as_dict_list(payload_object.get("shopping_results")))
    for category in _as_dict_list(payload_object.get("categorized_shopping_results")):
        raw_results.extend(_as_dict_list(category.get("shopping_results")))

    offers: list[_ShoppingOffer] = []
    for fallback_position, raw in enumerate(raw_results, start=1):
        source = _clean_text(raw.get("source"))
        if not source:
            continue
        text_parts = [
            _clean_text(raw.get("title")),
            _clean_text(raw.get("snippet")),
            _clean_text(raw.get("tag")),
            " ".join(str(item) for item in raw.get("extensions", []) if isinstance(item, str)),
        ]
        sales_signal, units_sold = _extract_sales_signal(
            " ".join(part for part in text_parts if part)
        )
        offers.append(
            _ShoppingOffer(
                position=_int_or_default(raw.get("position"), fallback_position),
                title=_clean_text(raw.get("title")) or source,
                source=source,
                price=_float_or_none(raw.get("extracted_price")),
                link=_clean_text(raw.get("link"))
                or _clean_text(raw.get("product_link"))
                or _clean_text(raw.get("serpapi_product_api")),
                rating=_float_or_none(raw.get("rating")),
                reviews=_int_or_none(raw.get("reviews")),
                sales_signal=sales_signal,
                units_sold=units_sold,
            )
        )
    return offers


def _build_snapshot_parts(
    *,
    offers: list[_ShoppingOffer],
    query: str,
    retrieved_at: datetime,
) -> tuple[list[EvidenceRecord], list[MarketplacePlatformEstimate], list[MarketplacePriceEstimate]]:
    grouped: defaultdict[str, list[_ShoppingOffer]] = defaultdict(list)
    display_names: dict[str, str] = {}
    for offer in offers:
        key = _platform_key(offer.source)
        grouped[key].append(offer)
        display_names.setdefault(key, offer.source)

    scored = sorted(
        ((_score_group(group), key, group) for key, group in grouped.items()),
        reverse=True,
        key=lambda item: item[0],
    )[:10]

    evidence: list[EvidenceRecord] = []
    rankings: list[MarketplacePlatformEstimate] = []
    prices: list[MarketplacePriceEstimate] = []
    for rank, (score, key, group) in enumerate(scored, start=1):
        platform = display_names[key]
        evidence_id = f"ev-marketplace-serpapi-{_slug(platform)}"
        price_values = [offer.price for offer in group if offer.price is not None]
        review_total = sum(offer.reviews or 0 for offer in group)
        units_sold = _max_units_sold(group)
        best_offer = min(group, key=lambda offer: offer.position)
        price_low = min(price_values) if price_values else None
        price_high = max(price_values) if price_values else None
        evidence.append(
            EvidenceRecord(
                id=evidence_id,
                source=EvidenceSource.MARKETPLACE_PROVIDER,
                source_reference=f"serpapi_google_shopping:{platform}",
                observation=(
                    f"SerpAPI returned {len(group)} Google Shopping offer(s) for {platform}; "
                    f"best observed position {best_offer.position}; "
                    f"price range {_price_phrase(price_low, price_high)}."
                ),
                quote=best_offer.title[:500],
                confidence=0.82,
                created_at=retrieved_at,
            )
        )
        rankings.append(
            MarketplacePlatformEstimate(
                rank=rank,
                platform=platform,
                platform_type=_platform_type(platform),
                data_source="serpapi_google_shopping",
                estimated_sales_potential_score=round(score, 3),
                observed_offer_count=len(group),
                observed_review_count=review_total,
                observed_units_sold=units_sold,
                observed_sales_signal=_best_sales_signal(group),
                sales_rank_basis=(
                    "Ranked from live Google Shopping observations: offer count, best result "
                    "position, review count, and price availability. This is not total units sold."
                ),
                listing_search_phrase=query,
                source_url=best_offer.link,
                evidence_ids=[evidence_id],
                confidence=_confidence_for_group(group),
                risk_flags=_ranking_risk_flags(units_sold),
            )
        )
        prices.append(
            MarketplacePriceEstimate(
                platform=platform,
                data_source="serpapi_google_shopping",
                price_low=price_low,
                price_high=price_high,
                currency="USD",
                observed_offer_count=len(price_values),
                price_basis="Observed Google Shopping offer prices returned by SerpAPI.",
                listing_search_phrase=query,
                source_url=best_offer.link,
                evidence_ids=[evidence_id],
                confidence=_confidence_for_group(group),
                risk_flags=["live_price_observation", "verify_before_pricing_decision"],
            )
        )
    return evidence, rankings, prices


def _score_group(group: list[_ShoppingOffer]) -> float:
    offer_score = min(len(group) / 5, 1.0) * 0.35
    best_position = min(offer.position for offer in group)
    position_score = max(0.0, 1.0 - ((best_position - 1) / 40)) * 0.25
    reviews = sum(offer.reviews or 0 for offer in group)
    review_score = min(math.log10(reviews + 1) / 5, 1.0) * 0.25
    price_score = (1.0 if any(offer.price is not None for offer in group) else 0.0) * 0.15
    return offer_score + position_score + review_score + price_score


def _build_query(request: MarketplaceDataProviderRequest) -> str:
    parts = [_product_name(request)]
    if request.request.brand:
        parts.append(request.request.brand)
    if request.request.category_hint:
        parts.append(request.request.category_hint)
    return " ".join(dict.fromkeys(part for part in parts if part)).strip()


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


def _platform_key(platform: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", platform.lower()).strip("-")


def _slug(value: str) -> str:
    return _platform_key(value)[:60] or "unknown"


def _platform_type(platform: str) -> str:
    lowered = platform.lower()
    if any(name in lowered for name in ("amazon", "ebay", "aliexpress", "etsy", "temu")):
        return "marketplace"
    if any(name in lowered for name in ("walmart", "target", "best buy", "home depot")):
        return "retailer"
    if any(name in lowered for name in ("tiktok", "instagram", "facebook")):
        return "social_commerce"
    return "other"


def _max_units_sold(group: list[_ShoppingOffer]) -> int | None:
    values = [offer.units_sold for offer in group if offer.units_sold is not None]
    return max(values) if values else None


def _best_sales_signal(group: list[_ShoppingOffer]) -> str | None:
    signals = [offer.sales_signal for offer in group if offer.sales_signal]
    return signals[0] if signals else None


def _confidence_for_group(group: list[_ShoppingOffer]) -> float:
    base = 0.45
    if len(group) >= 3:
        base += 0.1
    if any(offer.price is not None for offer in group):
        base += 0.1
    if sum(offer.reviews or 0 for offer in group) > 0:
        base += 0.08
    if any(offer.units_sold is not None for offer in group):
        base += 0.1
    return round(min(base, 0.82), 3)


def _ranking_risk_flags(units_sold: int | None) -> list[str]:
    flags = ["google_shopping_visibility_not_total_sales"]
    if units_sold is None:
        flags.append("units_sold_not_exposed_by_provider")
    return flags


def _overall_confidence(rankings: list[MarketplacePlatformEstimate]) -> float:
    if not rankings:
        return 0.0
    return round(sum(item.confidence for item in rankings) / len(rankings), 3)


def _price_phrase(low: float | None, high: float | None) -> str:
    if low is None and high is None:
        return "unknown"
    if low == high:
        return f"${low:.2f}"
    return f"${low:.2f}-${high:.2f}"


def _market_to_gl(market: str | None) -> str:
    if not market:
        return "us"
    return market.split("-", 1)[0].lower()


def _language_to_hl(language: str | None) -> str:
    if not language:
        return "en"
    return language.split("-", 1)[0].lower()
