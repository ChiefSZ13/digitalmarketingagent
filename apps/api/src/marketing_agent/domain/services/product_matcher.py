"""Deterministic marketplace product matching and aggregation."""

from __future__ import annotations

import math
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from marketing_agent.domain.models.evidence import EvidenceRecord, EvidenceSource
from marketing_agent.domain.models.marketplace import (
    BrandRole,
    MarketplaceListingValidation,
    MarketplacePlatformEstimate,
    MarketplacePriceEstimate,
    MarketplaceSnapshot,
    MarketplaceValidationSummary,
    MatchConflict,
    MatchConflictSeverity,
    MatchFeatureScores,
    NormalizedMarketplaceListing,
    OfficialNameVerification,
    ProductCondition,
    ProductIdentity,
    ProductMatchResult,
    ProductMatchStatus,
    ProductRelationship,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.run import ProductAnalysisRequest

NORMALIZATION_VERSION = "marketplace-normalization-v2"
SCORING_POLICY_VERSION = "official-brand-role-scoring-v2"
DEFAULT_MATCHER_VERSION = "product-matcher-v2"

BRAND_ALIASES: dict[str, str] = {
    "hewlett packard": "hp",
    "hewlett-packard": "hp",
    "procter and gamble": "p&g",
    "procter & gamble": "p&g",
    "p and g": "p&g",
}

ACCESSORY_INDICATORS = (
    "replacement",
    "compatible with",
    "case for",
    "cover for",
    "charger for",
    "cable for",
    "attachment",
    "refill",
    "spare part",
    "mounting kit",
    "protective shell",
    "ear pads",
    "brush heads",
)
ACCESSORY_PRODUCT_TERMS = {
    "case",
    "cover",
    "charger",
    "cable",
    "refill",
    "replacement",
    "attachment",
    "mount",
    "kit",
    "protector",
    "pads",
    "heads",
}
BUNDLE_INDICATORS = (
    "bundle",
    "with games",
    "with lens",
    "lens kit",
    "carrier plan",
    "service plan",
    "extended warranty",
    "starter kit",
)
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "new",
    "of",
    "official",
    "on",
    "sale",
    "the",
    "to",
    "with",
}
COLOR_TERMS = {
    "black",
    "white",
    "blue",
    "red",
    "green",
    "yellow",
    "pink",
    "purple",
    "orange",
    "gray",
    "grey",
    "silver",
    "gold",
    "brown",
    "beige",
    "natural",
}
EDITION_TOKENS = {"pro", "max", "plus", "mini", "ultra", "se"}
IDENTIFIER_FIELDS = ("gtin", "upc", "ean", "isbn", "asin", "manufacturer_part_number")
MODEL_EXPLICIT_PATTERN = re.compile(
    r"\b(?:model(?:\s+number)?|style(?:\s+code)?|sku|mpn|part(?:\s+number)?|item(?:\s+number)?)"
    r"\s*[:#-]?\s*(?P<identifier>[A-Z0-9][A-Z0-9-]{2,})\b",
    flags=re.IGNORECASE,
)
MODEL_TOKEN_PATTERN = re.compile(
    r"\b(?=[A-Z0-9-]*\d)(?=[A-Z0-9-]*[A-Z])[A-Z][A-Z0-9-]{2,}\b",
    flags=re.IGNORECASE,
)
CAPACITY_PATTERN = re.compile(
    r"\b(?P<value>\d+(?:\.\d+)?)\s?(?P<unit>gb|tb|mb|ml|l|oz|ounce|ounces|inch|in|mm|cm)\b",
    flags=re.IGNORECASE,
)
PACK_PATTERNS = (
    re.compile(r"\bpack\s+of\s+(?P<count>\d{1,3})\b", flags=re.IGNORECASE),
    re.compile(r"\b(?P<count>\d{1,3})\s*[- ]?pack\b", flags=re.IGNORECASE),
    re.compile(r"\b(?P<count>\d{1,3})\s*(?:count|ct)\b", flags=re.IGNORECASE),
)
MULTIPLY_UNIT_PATTERN = re.compile(
    r"\b(?P<count>\d{1,3})\s*(?:x|×)\s*(?P<quantity>\d+(?:\.\d+)?)\s*(?P<unit>ml|l|oz|gb|tb)\b",
    flags=re.IGNORECASE,
)
UNIT_PATTERN = re.compile(
    r"\b(?P<quantity>\d+(?:\.\d+)?)\s*(?P<unit>ml|l|oz|gb|tb)\b",
    flags=re.IGNORECASE,
)
COMPATIBILITY_PHRASE_TEMPLATES = (
    "for",
    "compatible with",
    "works with",
    "designed for",
    "fits",
    "replacement for",
    "supports",
)
TITLE_BRAND_SKIP_TERMS = {
    "brand",
    "new",
    "official",
    "officially",
    "licensed",
    "genuine",
    "original",
}
RETAILER_OR_SELLER_NAMES = {
    "amazon",
    "best buy",
    "costco",
    "dell",
    "ebay",
    "newegg",
    "target",
    "walmart",
    "walmart marketplace",
}


@dataclass(frozen=True)
class SubBrandRegistryEntry:
    name: str
    aliases: tuple[str, ...]
    official_product_lines: tuple[str, ...]
    known_licensed_third_party_brands: tuple[str, ...] = ()


@dataclass(frozen=True)
class BrandRegistryEntry:
    manufacturer: str
    manufacturer_aliases: tuple[str, ...]
    sub_brands: tuple[SubBrandRegistryEntry, ...] = ()


@dataclass(frozen=True)
class RegistryMatch:
    manufacturer: str
    manufacturer_aliases: tuple[str, ...]
    sub_brand: str
    sub_brand_aliases: tuple[str, ...]
    official_product_line: str | None
    official_product_lines: tuple[str, ...]
    known_licensed_third_party_brands: tuple[str, ...]


BRAND_REGISTRY: tuple[BrandRegistryEntry, ...] = (
    BrandRegistryEntry(
        manufacturer="Microsoft",
        manufacturer_aliases=("Microsoft", "Microsoft Corporation"),
        sub_brands=(
            SubBrandRegistryEntry(
                name="Xbox",
                aliases=("Xbox", "Microsoft Xbox"),
                official_product_lines=(
                    "Xbox Wireless Controller",
                    "Xbox Elite Wireless Controller Series 2",
                ),
                known_licensed_third_party_brands=("PowerA", "PDP", "Razer"),
            ),
        ),
    ),
)


@dataclass(frozen=True)
class ProductMatcherConfig:
    matcher_version: str = DEFAULT_MATCHER_VERSION
    exact_threshold: float = 0.93
    probable_threshold: float = 0.84
    uncertain_threshold: float = 0.65
    require_brand: bool = False
    color_strict: bool = False
    exclude_refurbished: bool = True
    exclude_used: bool = True
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "identifier": 0.30,
            "model": 0.22,
            "brand": 0.12,
            "product_type": 0.10,
            "title": 0.10,
            "important_tokens": 0.08,
            "variant": 0.04,
            "package": 0.02,
            "condition": 0.02,
        }
    )
    official_weights: dict[str, float] = field(
        default_factory=lambda: {
            "identifier": 0.30,
            "manufacturer": 0.18,
            "brand_owner": 0.16,
            "official_product_line": 0.16,
            "model": 0.12,
            "title": 0.04,
            "product_type": 0.02,
            "variant": 0.02,
        }
    )


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("™", "").replace("®", "").replace("©", "")
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("™", "").replace("®", "").replace("©", "")
    normalized = re.sub(r"[\u2010-\u2015_/|]+", " ", normalized)
    normalized = re.sub(r"(?<=\d),(?=\d)", "", normalized)
    normalized = re.sub(r"[^\w\s&.+×-]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized.casefold()).strip()
    return normalized


def normalize_model_number(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^A-Z0-9]+", "", unicodedata.normalize("NFKC", value).upper())
    return normalized or None


def normalize_brand(value: str | None) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    return BRAND_ALIASES.get(normalized, normalized)


def normalize_identifier(value: str | None, identifier_type: str) -> str | None:
    if not value:
        return None
    if identifier_type == "asin":
        candidate = re.sub(r"[^A-Z0-9]", "", value.upper())
        return candidate if len(candidate) == 10 else None
    if identifier_type == "isbn":
        candidate = re.sub(r"[^0-9X]", "", value.upper())
        if len(candidate) == 13 and _valid_gtin(candidate):
            return candidate
        if len(candidate) == 10 and _valid_isbn10(candidate):
            return candidate
        return None
    if identifier_type == "manufacturer_part_number":
        return normalize_model_number(value)
    candidate = re.sub(r"\D", "", value)
    if len(candidate) in {8, 12, 13, 14} and _valid_gtin(candidate):
        return candidate
    return None


def extract_model_number(*values: str | None) -> str | None:
    text = " ".join(value for value in values if value)
    for match in MODEL_EXPLICIT_PATTERN.finditer(text):
        normalized = normalize_model_number(match.group("identifier"))
        if normalized:
            return normalized
    for match in MODEL_TOKEN_PATTERN.finditer(text.upper()):
        token = match.group(0)
        normalized = normalize_model_number(token)
        if normalized and not normalized.isdigit():
            return normalized
    return None


def parse_condition(*values: str | None) -> ProductCondition | None:
    text = normalize_text(" ".join(value for value in values if value))
    if not text:
        return None
    if "for parts" in text or "parts only" in text:
        return ProductCondition.FOR_PARTS
    if "open box" in text or "open-box" in text:
        return ProductCondition.OPEN_BOX
    if "refurbished" in text or "renewed" in text:
        return ProductCondition.REFURBISHED
    if "used acceptable" in text:
        return ProductCondition.USED_ACCEPTABLE
    if "used good" in text or "pre owned" in text or "pre-owned" in text:
        return ProductCondition.USED_GOOD
    if "used like new" in text or "like new" in text:
        return ProductCondition.USED_LIKE_NEW
    if "used" in text:
        return ProductCondition.USED_GOOD
    if "brand new" in text or re.search(r"\bnew\b", text):
        return ProductCondition.NEW
    return None


def parse_package(*values: str | None) -> tuple[int | None, float | None, str | None]:
    raw_text = " ".join(value for value in values if value)
    text = normalize_text(raw_text)
    pack_quantity: int | None = None
    unit_quantity: float | None = None
    unit_type: str | None = None

    multiply_match = MULTIPLY_UNIT_PATTERN.search(raw_text)
    if multiply_match:
        pack_quantity = int(multiply_match.group("count"))
        unit_quantity = float(multiply_match.group("quantity"))
        unit_type = _normalize_unit(multiply_match.group("unit"))
        return pack_quantity, unit_quantity, unit_type

    for pattern in PACK_PATTERNS:
        match = pattern.search(text)
        if match:
            pack_quantity = int(match.group("count"))
            break

    unit_match = UNIT_PATTERN.search(text)
    if unit_match:
        unit_quantity = float(unit_match.group("quantity"))
        unit_type = _normalize_unit(unit_match.group("unit"))

    return pack_quantity, unit_quantity, unit_type


def decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = re.sub(r"[^0-9.\-]", "", value)
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


def build_product_identity(
    profile: ProductProfile,
    *,
    request: ProductAnalysisRequest,
    expected_condition: ProductCondition | None = ProductCondition.NEW,
) -> ProductIdentity:
    product_name = _linked_value(profile.product_name) or request.description.strip()
    identity_text_values = [
        product_name,
        _linked_value(profile.marketplace_search_query),
        _linked_value(profile.brand),
        _linked_value(profile.category),
        _linked_value(profile.subcategory),
        *[item.value for item in profile.observed_facts],
        *[item.value for item in profile.user_provided_facts],
        *[item.value for item in profile.inferred_attributes],
    ]
    model_number = extract_model_number(*identity_text_values)
    pack_quantity, unit_quantity, unit_type = parse_package(*identity_text_values)
    color = _first_linked_value(profile.colors)
    capacity = _first_capacity_token(*identity_text_values)
    variant = capacity
    aliases = [
        value
        for value in (
            _linked_value(profile.marketplace_search_query),
            _linked_value(profile.product_name),
        )
        if value
    ]
    brand = _linked_value(profile.brand) or request.brand
    category = _linked_value(profile.category) or request.category_hint
    product_type = _linked_value(profile.subcategory) or category
    registry_match = _registry_match_for_identity(
        explicit_brand=brand,
        identity_text_values=identity_text_values,
    )
    manufacturer = brand
    sub_brand: str | None = None
    official_product_line: str | None = None
    allowed_brand_aliases = [brand] if brand else []
    allowed_manufacturer_aliases = [brand] if brand else []
    official_name_patterns: list[str] = []
    target_is_official_product = _target_looks_like_official_product(
        brand=brand,
        product_name=product_name,
        marketplace_query=_linked_value(profile.marketplace_search_query),
        registry_match=registry_match,
    )
    if registry_match:
        manufacturer = registry_match.manufacturer
        brand = registry_match.sub_brand
        sub_brand = registry_match.sub_brand
        official_product_line = registry_match.official_product_line
        allowed_brand_aliases = list(registry_match.sub_brand_aliases)
        allowed_manufacturer_aliases = list(registry_match.manufacturer_aliases)
        official_name_patterns = list(registry_match.official_product_lines)
        target_is_official_product = True

    normalized_product_name = normalize_text(product_name)
    normalized_title = normalize_text(
        " ".join(part for part in (manufacturer, brand, product_name) if part)
    )
    return ProductIdentity(
        brand=brand,
        manufacturer=manufacturer,
        sub_brand=sub_brand,
        product_name=product_name,
        normalized_product_name=normalized_product_name,
        official_product_line=official_product_line,
        product_type=product_type,
        category=category,
        model_number=model_number,
        variant=variant,
        color=color,
        material=_first_linked_value(profile.materials),
        pack_quantity=pack_quantity,
        unit_quantity=unit_quantity,
        unit_type=unit_type,
        expected_condition=expected_condition,
        normalized_title=normalized_title or normalize_text(product_name),
        allowed_brand_aliases=_dedupe_preserve_order(allowed_brand_aliases),
        allowed_manufacturer_aliases=_dedupe_preserve_order(allowed_manufacturer_aliases),
        official_name_patterns=_dedupe_preserve_order(official_name_patterns),
        target_is_official_product=target_is_official_product,
        aliases=aliases,
        excluded_terms=list(ACCESSORY_INDICATORS),
        source_evidence=profile.evidence,
    )


def derive_listing_brand_roles(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
) -> NormalizedMarketplaceListing:
    compatibility_targets, compatibility_phrases = _detect_compatibility_targets(
        product,
        listing,
    )
    provider_brand = listing.provider_brand or listing.brand
    extracted_title_brand = listing.extracted_title_brand or _extract_title_brand(
        product,
        listing,
    )
    detected_brand = provider_brand or extracted_title_brand
    detected_manufacturer = listing.manufacturer
    if detected_brand and _is_manufacturer_alias(product, detected_brand):
        detected_manufacturer = detected_manufacturer or detected_brand
    claimed_licensed = listing.claimed_licensed
    if claimed_licensed is None:
        claimed_licensed = _claims_licensed(listing)
    claimed_official = listing.claimed_official
    if claimed_official is None:
        claimed_official = _claims_official(listing)
    brand_role = listing.brand_role or _brand_role(
        product=product,
        detected_brand=detected_brand,
        compatibility_targets=compatibility_targets,
    )
    product_line = listing.product_line or _matched_official_line(product, listing)[0]
    return listing.model_copy(
        update={
            "brand": listing.brand or provider_brand,
            "provider_brand": provider_brand,
            "extracted_title_brand": extracted_title_brand,
            "manufacturer": detected_manufacturer,
            "product_line": product_line,
            "compatibility_targets": _dedupe_preserve_order(
                [*listing.compatibility_targets, *compatibility_targets]
            ),
            "compatibility_phrases": _dedupe_preserve_order(
                [*listing.compatibility_phrases, *compatibility_phrases]
            ),
            "claimed_official": claimed_official,
            "claimed_licensed": claimed_licensed,
            "brand_role": brand_role,
        }
    )


def verify_official_name(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
) -> OfficialNameVerification:
    detected_brand = listing.provider_brand or listing.brand or listing.extracted_title_brand
    detected_manufacturer = listing.manufacturer
    if detected_brand and _is_manufacturer_alias(product, detected_brand):
        detected_manufacturer = detected_manufacturer or detected_brand

    brand_as_brand = (
        listing.brand_role in {BrandRole.OFFICIAL_BRAND, BrandRole.MANUFACTURER_BRAND}
        if listing.brand_role
        else None
    )
    brand_only_compatibility = _expected_brand_only_as_compatibility_target(product, listing)
    matched_line, matched_exact_product_line = _matched_official_line(product, listing)
    official_product_line_match = matched_line is not None
    known_licensed_brand = _is_known_licensed_brand(product, detected_brand)
    third_party_brand = (
        product.target_is_official_product
        and detected_brand is not None
        and not _is_expected_brand_or_manufacturer(product, detected_brand)
        and not _is_retailer_or_seller_name(detected_brand)
    )
    reason_codes: list[str] = []
    conflicts: list[MatchConflict] = []

    if listing.brand_role == BrandRole.OFFICIAL_BRAND:
        reason_codes.append("OFFICIAL_BRAND_CONFIRMED")
    if listing.brand_role == BrandRole.MANUFACTURER_BRAND:
        reason_codes.append("OFFICIAL_MANUFACTURER_CONFIRMED")
    if official_product_line_match:
        reason_codes.append("OFFICIAL_PRODUCT_LINE_CONFIRMED")
    if brand_only_compatibility:
        reason_codes.append("EXPECTED_BRAND_ONLY_IN_COMPATIBILITY_PHRASE")
        conflicts.append(
            _conflict(
                code="EXPECTED_BRAND_ONLY_IN_COMPATIBILITY_PHRASE",
                field="brand",
                expected=_display_brand(product),
                observed=", ".join(listing.compatibility_phrases) or listing.title,
                severity=MatchConflictSeverity.HIGH,
                explanation=(
                    "The expected brand appears only as a compatibility target, not as the "
                    "listing brand."
                ),
            )
        )
    if third_party_brand:
        reason_codes.append("THIRD_PARTY_BRAND_DETECTED")
        conflicts.append(
            _conflict(
                code="THIRD_PARTY_BRAND_DETECTED",
                field="brand",
                expected=_display_brand(product),
                observed=detected_brand,
                severity=MatchConflictSeverity.HIGH,
                explanation=(
                    "The listing exposes a different product brand from the requested official "
                    "product."
                ),
            )
        )
    if detected_brand is None:
        reason_codes.append("UNKNOWN_LISTING_BRAND")
    if product.target_is_official_product and product.official_product_line and not matched_line:
        reason_codes.append("OFFICIAL_NAME_INCOMPLETE")
    if listing.claimed_licensed:
        reason_codes.append("LICENSED_THIRD_PARTY_PRODUCT")
    if known_licensed_brand:
        reason_codes.append("LICENSED_THIRD_PARTY_PRODUCT")

    if listing.claimed_licensed and third_party_brand:
        conflicts.append(
            _conflict(
                code="LICENSED_THIRD_PARTY_PRODUCT",
                field="brand",
                expected="manufactured by official brand owner",
                observed=f"{detected_brand} licensed for {_display_brand(product)}",
                severity=MatchConflictSeverity.HIGH,
                explanation=(
                    "Officially licensed means compatible or authorized, not manufactured by "
                    "the official brand owner."
                ),
            )
        )

    if third_party_brand and listing.compatibility_targets:
        relationship = (
            ProductRelationship.LICENSED_THIRD_PARTY_ALTERNATIVE
            if known_licensed_brand or listing.claimed_licensed
            else ProductRelationship.GENERIC_COMPATIBLE_ALTERNATIVE
        )
        reason_codes.append(
            "LICENSED_THIRD_PARTY_PRODUCT"
            if relationship == ProductRelationship.LICENSED_THIRD_PARTY_ALTERNATIVE
            else "GENERIC_THIRD_PARTY_PRODUCT"
        )
    elif brand_only_compatibility:
        relationship = ProductRelationship.GENERIC_COMPATIBLE_ALTERNATIVE
        reason_codes.append("COMPATIBLE_PRODUCT_NOT_OFFICIAL")
    elif official_product_line_match and brand_as_brand:
        relationship = (
            ProductRelationship.OFFICIAL_EXACT_PRODUCT
            if matched_exact_product_line and not _has_unrequested_variant(product, listing)
            else ProductRelationship.OFFICIAL_SAME_PRODUCT_FAMILY
        )
    elif product.target_is_official_product and brand_as_brand:
        relationship = ProductRelationship.OFFICIAL_EXACT_PRODUCT
    elif third_party_brand:
        relationship = ProductRelationship.UNRELATED
    else:
        relationship = ProductRelationship.UNKNOWN

    return OfficialNameVerification(
        official_name_match=(
            True
            if relationship == ProductRelationship.OFFICIAL_EXACT_PRODUCT
            else False
            if relationship
            in {
                ProductRelationship.LICENSED_THIRD_PARTY_ALTERNATIVE,
                ProductRelationship.GENERIC_COMPATIBLE_ALTERNATIVE,
                ProductRelationship.UNRELATED,
            }
            else None
        ),
        official_product_line_match=official_product_line_match,
        expected_brand_present_as_brand=brand_as_brand,
        expected_brand_present_only_as_compatibility_target=brand_only_compatibility,
        detected_listing_brand=detected_brand,
        detected_manufacturer=detected_manufacturer,
        relationship=relationship,
        reason_codes=_dedupe_preserve_order(reason_codes),
        conflicts=conflicts,
    )


def match_listing(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    *,
    config: ProductMatcherConfig | None = None,
) -> ProductMatchResult:
    matcher_config = config or ProductMatcherConfig()
    listing = derive_listing_brand_roles(product, listing)
    official_verification = verify_official_name(product, listing)
    conflicts = _detect_conflicts(product, listing, matcher_config, official_verification)
    feature_scores = _score_features(product, listing, matcher_config, official_verification)
    score = _weighted_score(
        feature_scores,
        matcher_config,
        official_target=product.target_is_official_product,
    )
    score = _apply_strong_identity_boost(score, feature_scores)
    score = _apply_brand_role_penalties(score, feature_scores)
    score = _apply_conflict_penalties(score, conflicts)
    relationship = _final_relationship(
        product=product,
        listing=listing,
        official_verification=official_verification,
        conflicts=conflicts,
        score=score,
    )
    score = _relationship_confidence(score, relationship)
    status = _classify_match(
        score,
        conflicts,
        feature_scores,
        matcher_config,
        relationship=relationship,
        target_is_official_product=product.target_is_official_product,
    )
    group = _aggregation_group(status, conflicts, relationship)
    eligible = (
        status in {ProductMatchStatus.EXACT_MATCH, ProductMatchStatus.PROBABLE_MATCH}
        and group == "primary"
        and (
            not product.target_is_official_product
            or relationship == ProductRelationship.OFFICIAL_EXACT_PRODUCT
        )
        and listing.landed_price is not None
        and listing.currency is not None
    )
    matched_fields = _matched_fields(feature_scores)
    unknown_fields = _unknown_fields(product, listing, feature_scores)
    reason_codes = _reason_codes(
        status,
        relationship,
        official_verification,
        conflicts,
        matched_fields,
        eligible,
    )
    return ProductMatchResult(
        listing_id=listing.listing_id,
        status=status,
        relationship=relationship,
        score=round(score, 3),
        matched_fields=matched_fields,
        unknown_fields=unknown_fields,
        conflicts=conflicts,
        feature_scores=feature_scores,
        official_name_verification=official_verification,
        reason_codes=reason_codes,
        human_summary=_human_summary(status, relationship, score, conflicts, group),
        eligible_for_price_aggregation=eligible,
        aggregation_group=group,
        requires_human_review=status == ProductMatchStatus.UNCERTAIN,
        matcher_version=matcher_config.matcher_version,
    )


def build_validated_marketplace_snapshot(
    *,
    request: ProductAnalysisRequest,
    profile: ProductProfile,
    listings: list[NormalizedMarketplaceListing],
    source_provider: str,
    source_query: str,
    title: str,
    summary: str,
    is_live_data: bool,
    methodology: str,
    limitations: list[str],
    base_warnings: list[str],
    retrieved_at: datetime,
    matcher_config: ProductMatcherConfig | None = None,
) -> tuple[MarketplaceSnapshot, list[EvidenceRecord]]:
    config = matcher_config or ProductMatcherConfig()
    identity = build_product_identity(profile, request=request)
    validations: list[MarketplaceListingValidation] = []
    for listing in listings:
        enriched_listing = derive_listing_brand_roles(identity, listing)
        validations.append(
            MarketplaceListingValidation(
                listing=enriched_listing,
                match_result=match_listing(identity, enriched_listing, config=config),
            )
        )
    aggregation_evidence, rankings, prices = _aggregate_primary_offers(
        validations=validations,
        source_provider=source_provider,
        source_query=source_query,
        retrieved_at=retrieved_at,
        matcher_version=config.matcher_version,
    )
    validation_summary = _validation_summary(validations, config)
    warnings = [*base_warnings]
    if validation_summary.rejected_count:
        warnings.append(
            f"{validation_summary.rejected_count} marketplace listing(s) were rejected by "
            "deterministic product validation."
        )
    if validation_summary.uncertain_count:
        warnings.append(
            f"{validation_summary.uncertain_count} marketplace listing(s) need human review and "
            "were excluded from primary price aggregation."
        )
    if validation_summary.primary_eligible_count == 0:
        warnings.append(
            "No validated primary marketplace offers were eligible for price aggregation."
        )

    snapshot = MarketplaceSnapshot(
        title=title,
        summary=summary,
        source_provider=source_provider,
        source_query=source_query,
        retrieved_at=retrieved_at,
        is_live_data=is_live_data,
        methodology=methodology,
        limitations=limitations,
        product_identity=identity,
        validation_summary=validation_summary,
        validated_listings=validations,
        platform_rankings=rankings,
        price_estimates=prices,
        warnings=warnings,
        overall_confidence=_overall_confidence(validations),
    )
    return snapshot, aggregation_evidence


def _detect_conflicts(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    config: ProductMatcherConfig,
    official_verification: OfficialNameVerification,
) -> list[MatchConflict]:
    conflicts: list[MatchConflict] = [*official_verification.conflicts]
    for field_name in IDENTIFIER_FIELDS:
        expected = normalize_identifier(getattr(product, field_name), field_name)
        observed = normalize_identifier(getattr(listing, field_name), field_name)
        if expected and observed and expected != observed:
            conflicts.append(
                _conflict(
                    code="IDENTIFIER_MISMATCH",
                    field=field_name,
                    expected=getattr(product, field_name),
                    observed=getattr(listing, field_name),
                    severity=MatchConflictSeverity.HIGH,
                    explanation=f"Expected {field_name} does not match the observed listing value.",
                )
            )

    expected_model = normalize_model_number(product.model_number)
    observed_model = normalize_model_number(listing.model_number) or extract_model_number(
        listing.title, listing.description_excerpt
    )
    if expected_model and observed_model and expected_model != observed_model:
        conflicts.append(
            _conflict(
                code="MODEL_NUMBER_MISMATCH",
                field="model_number",
                expected=product.model_number,
                observed=listing.model_number or observed_model,
                severity=MatchConflictSeverity.HIGH,
                explanation="The listing exposes a different model number.",
            )
        )

    expected_brand = normalize_brand(product.brand)
    observed_brand = normalize_brand(listing.brand)
    if (
        expected_brand
        and observed_brand
        and expected_brand != observed_brand
        and not any(conflict.code == "THIRD_PARTY_BRAND_DETECTED" for conflict in conflicts)
    ):
        conflicts.append(
            _conflict(
                code="BRAND_MISMATCH",
                field="brand",
                expected=product.brand,
                observed=listing.brand,
                severity=MatchConflictSeverity.HIGH,
                explanation="The listing brand differs from the canonical product brand.",
            )
        )

    if _is_accessory_listing(product, listing):
        conflicts.append(
            _conflict(
                code="ACCESSORY_MISMATCH",
                field="product_type",
                expected=product.product_type or product.product_name,
                observed=listing.title,
                severity=MatchConflictSeverity.HIGH,
                explanation="The listing appears to be an accessory, refill, or replacement part.",
            )
        )

    expected_pack = product.pack_quantity
    observed_pack = listing.pack_quantity
    if observed_pack and observed_pack > 1 and expected_pack in (None, 1):
        conflicts.append(
            _conflict(
                code="PACKAGE_QUANTITY_MISMATCH",
                field="pack_quantity",
                expected=expected_pack or 1,
                observed=observed_pack,
                severity=MatchConflictSeverity.MEDIUM,
                explanation=(
                    "The listing is a multipack and should not be mixed with single-unit prices."
                ),
            )
        )
    elif expected_pack and observed_pack and expected_pack != observed_pack:
        conflicts.append(
            _conflict(
                code="PACKAGE_QUANTITY_MISMATCH",
                field="pack_quantity",
                expected=expected_pack,
                observed=observed_pack,
                severity=MatchConflictSeverity.MEDIUM,
                explanation="The listing package quantity differs from the target product.",
            )
        )

    variant_conflict = _variant_conflict(product, listing, config)
    if variant_conflict:
        conflicts.append(variant_conflict)

    condition_conflict = _condition_conflict(product, listing, config)
    if condition_conflict:
        conflicts.append(condition_conflict)

    if _is_bundle_listing(listing):
        conflicts.append(
            _conflict(
                code="BUNDLE_MISMATCH",
                field="bundle",
                expected="standalone product",
                observed=listing.title,
                severity=MatchConflictSeverity.HIGH,
                explanation="The listing appears to include extra products, services, or plans.",
            )
        )
    return conflicts


def _score_features(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    config: ProductMatcherConfig,
    official_verification: OfficialNameVerification,
) -> MatchFeatureScores:
    identifier_score = _identifier_score(product, listing)
    brand_score = _brand_score(product, listing, config, official_verification)
    brand_owner_score = _brand_owner_score(product, listing, official_verification)
    manufacturer_score = _manufacturer_score(product, listing, official_verification)
    official_product_line_score = _official_product_line_score(official_verification)
    compatibility_only_penalty = (
        1.0
        if product.target_is_official_product
        and official_verification.expected_brand_present_only_as_compatibility_target
        else 0.0
    )
    third_party_brand_penalty = (
        1.0
        if product.target_is_official_product
        and (
            listing.brand_role == BrandRole.THIRD_PARTY_BRAND
            or "THIRD_PARTY_BRAND_DETECTED" in official_verification.reason_codes
        )
        else 0.0
    )
    model_score = _model_score(product, listing)
    title_score = _dice_score(_tokens(product.normalized_title), _tokens(listing.normalized_title))
    important_token_score = _important_token_score(product, listing)
    product_type_score = _product_type_score(product, listing)
    category_score = _category_score(product, listing)
    variant_score = _variant_score(product, listing, config)
    package_score = _package_score(product, listing)
    condition_score = _condition_score(product, listing)
    return MatchFeatureScores(
        identifier_score=identifier_score,
        brand_score=brand_score,
        brand_owner_score=brand_owner_score,
        manufacturer_score=manufacturer_score,
        official_product_line_score=official_product_line_score,
        compatibility_only_penalty=compatibility_only_penalty,
        third_party_brand_penalty=third_party_brand_penalty,
        model_score=model_score,
        title_score=title_score,
        important_token_score=important_token_score,
        product_type_score=product_type_score,
        category_score=category_score,
        variant_score=variant_score,
        package_score=package_score,
        condition_score=condition_score,
        image_score=None,
    )


def _weighted_score(
    scores: MatchFeatureScores,
    config: ProductMatcherConfig,
    *,
    official_target: bool,
) -> float:
    if official_target:
        values = {
            "identifier": scores.identifier_score,
            "manufacturer": scores.manufacturer_score,
            "brand_owner": scores.brand_owner_score,
            "official_product_line": scores.official_product_line_score,
            "model": scores.model_score,
            "title": scores.title_score,
            "product_type": scores.product_type_score,
            "variant": scores.variant_score,
        }
        weights = config.official_weights
    else:
        values = {
            "identifier": scores.identifier_score,
            "model": scores.model_score,
            "brand": scores.brand_score,
            "product_type": scores.product_type_score,
            "title": scores.title_score,
            "important_tokens": scores.important_token_score,
            "variant": scores.variant_score,
            "package": scores.package_score,
            "condition": scores.condition_score,
        }
        weights = config.weights
    available = [
        (weights[name], value)
        for name, value in values.items()
        if value is not None and weights.get(name, 0.0) > 0
    ]
    if not available:
        return 0.0
    weight_sum = sum(weight for weight, _ in available)
    return max(0.0, min(1.0, sum(weight * value for weight, value in available) / weight_sum))


def _apply_conflict_penalties(score: float, conflicts: list[MatchConflict]) -> float:
    penalty = 0.0
    for conflict in conflicts:
        if conflict.severity == MatchConflictSeverity.MEDIUM:
            penalty += 0.12
        elif conflict.severity == MatchConflictSeverity.LOW:
            penalty += 0.05
    return max(0.0, min(1.0, score - penalty))


def _apply_brand_role_penalties(score: float, scores: MatchFeatureScores) -> float:
    penalty = 0.0
    if scores.compatibility_only_penalty:
        penalty += 0.35 * scores.compatibility_only_penalty
    if scores.third_party_brand_penalty:
        penalty += 0.45 * scores.third_party_brand_penalty
    return max(0.0, min(1.0, score - penalty))


def _apply_strong_identity_boost(score: float, scores: MatchFeatureScores) -> float:
    if scores.identifier_score == 1.0:
        return max(score, 0.97)
    if scores.model_score == 1.0 and (scores.brand_score is None or scores.brand_score >= 0.85):
        return max(score, 0.94)
    return score


def _classify_match(
    score: float,
    conflicts: list[MatchConflict],
    scores: MatchFeatureScores,
    config: ProductMatcherConfig,
    *,
    relationship: ProductRelationship,
    target_is_official_product: bool,
) -> ProductMatchStatus:
    if relationship in {
        ProductRelationship.LICENSED_THIRD_PARTY_ALTERNATIVE,
        ProductRelationship.GENERIC_COMPATIBLE_ALTERNATIVE,
        ProductRelationship.ACCESSORY_OR_REPLACEMENT,
        ProductRelationship.UNRELATED,
    }:
        return ProductMatchStatus.REJECTED
    if any(conflict.severity == MatchConflictSeverity.HIGH for conflict in conflicts):
        return ProductMatchStatus.REJECTED
    if conflicts:
        return ProductMatchStatus.UNCERTAIN
    strong_identity = scores.identifier_score == 1.0 or scores.model_score == 1.0
    if target_is_official_product:
        if relationship == ProductRelationship.OFFICIAL_EXACT_PRODUCT:
            if strong_identity and score >= config.exact_threshold:
                return ProductMatchStatus.EXACT_MATCH
            if score >= config.probable_threshold and _has_sufficient_evidence(scores, config):
                return ProductMatchStatus.PROBABLE_MATCH
            if score >= config.uncertain_threshold:
                return ProductMatchStatus.UNCERTAIN
            return ProductMatchStatus.REJECTED
        if relationship == ProductRelationship.OFFICIAL_SAME_PRODUCT_FAMILY:
            return (
                ProductMatchStatus.PROBABLE_MATCH
                if score >= config.uncertain_threshold
                else ProductMatchStatus.UNCERTAIN
            )
        if score >= config.uncertain_threshold:
            return ProductMatchStatus.UNCERTAIN
        return ProductMatchStatus.REJECTED
    if strong_identity and score >= config.exact_threshold:
        return ProductMatchStatus.EXACT_MATCH
    if score >= config.probable_threshold and _has_sufficient_evidence(scores, config):
        return ProductMatchStatus.PROBABLE_MATCH
    if score >= config.uncertain_threshold:
        return ProductMatchStatus.UNCERTAIN
    return ProductMatchStatus.REJECTED


def _aggregate_primary_offers(
    *,
    validations: list[MarketplaceListingValidation],
    source_provider: str,
    source_query: str,
    retrieved_at: datetime,
    matcher_version: str,
) -> tuple[list[EvidenceRecord], list[MarketplacePlatformEstimate], list[MarketplacePriceEstimate]]:
    primary = [
        validation
        for validation in _dedupe_validations(validations)
        if validation.match_result.eligible_for_price_aggregation
    ]
    grouped: defaultdict[str, list[MarketplaceListingValidation]] = defaultdict(list)
    for validation in primary:
        grouped[_platform_key(validation.listing.platform)].append(validation)

    scored = sorted(
        ((_score_platform_group(group), key, group) for key, group in grouped.items()),
        reverse=True,
        key=lambda item: item[0],
    )[:10]
    evidence: list[EvidenceRecord] = []
    rankings: list[MarketplacePlatformEstimate] = []
    prices: list[MarketplacePriceEstimate] = []
    for rank, (score, _key, group) in enumerate(scored, start=1):
        listings = [validation.listing for validation in group]
        platform = listings[0].platform
        evidence_id = f"ev-marketplace-validated-{_slug(platform)}-{rank}"
        price_values = [
            listing.landed_price for listing in listings if listing.landed_price is not None
        ]
        currency = _single_currency(listings) or "USD"
        review_total = sum(listing.review_count or 0 for listing in listings)
        best_listing = min(
            listings,
            key=lambda listing: _rank_signal_value(listing, "position") or 9999,
        )
        observed_start = min(listing.observed_at for listing in listings)
        observed_end = max(listing.observed_at for listing in listings)
        price_low = float(min(price_values)) if price_values else None
        price_high = float(max(price_values)) if price_values else None
        price_median = float(statistics.median(price_values)) if price_values else None
        units_sold = _max_rank_signal(listings, "units_sold")
        sales_signal = _best_rank_signal_source(listings, "units_sold")
        evidence.append(
            EvidenceRecord(
                id=evidence_id,
                source=EvidenceSource.MARKETPLACE_PROVIDER,
                source_reference=f"{source_provider}:{platform}",
                observation=(
                    f"Validated {len(listings)} primary marketplace listing(s) for {platform}; "
                    f"price range {_price_phrase(price_low, price_high)}."
                ),
                quote=best_listing.title[:500],
                confidence=0.86,
                created_at=retrieved_at,
                provider=source_provider,
                platform=platform,
                listing_id=best_listing.listing_id,
                field_name="landed_price",
                observed_value=_price_phrase(price_low, price_high),
                observed_at=observed_end,
                provider_run_id=source_query,
                normalization_version=NORMALIZATION_VERSION,
                matcher_version=matcher_version,
            )
        )
        rankings.append(
            MarketplacePlatformEstimate(
                rank=rank,
                platform=platform,
                platform_type=_platform_type(platform),
                data_source=source_provider,
                estimated_sales_potential_score=round(score, 3),
                observed_offer_count=len(listings),
                observed_review_count=review_total,
                observed_units_sold=int(units_sold) if units_sold is not None else None,
                observed_sales_signal=sales_signal,
                sales_rank_basis=(
                    "Ranked from validated primary listings only; rejected, uncertain, "
                    "official-variant, third-party alternative, alternate-package, "
                    "alternate-condition, and rejected listings are excluded."
                ),
                listing_search_phrase=source_query,
                source_url=best_listing.source_url,
                evidence_ids=[evidence_id],
                source_count=1,
                validated_listing_count=len(listings),
                matcher_version=matcher_version,
                confidence=_group_confidence(group),
                risk_flags=["validated_primary_listings_only"],
            )
        )
        prices.append(
            MarketplacePriceEstimate(
                platform=platform,
                data_source=source_provider,
                price_low=price_low,
                price_median=price_median,
                price_high=price_high,
                currency=currency,
                observed_offer_count=len(price_values),
                source_count=1,
                observation_started_at=observed_start,
                observation_ended_at=observed_end,
                aggregation_group="primary",
                matcher_version=matcher_version,
                price_basis="Landed prices from validated primary product matches.",
                listing_search_phrase=source_query,
                source_url=best_listing.source_url,
                evidence_ids=[evidence_id],
                confidence=_group_confidence(group),
                risk_flags=["excludes_rejected_uncertain_alternative_and_alternate_offers"],
            )
        )
    return evidence, rankings, prices


def _validation_summary(
    validations: list[MarketplaceListingValidation],
    config: ProductMatcherConfig,
) -> MarketplaceValidationSummary:
    statuses = Counter(validation.match_result.status for validation in validations)
    groups = Counter(validation.match_result.aggregation_group for validation in validations)
    relationships = Counter(validation.match_result.relationship for validation in validations)
    return MarketplaceValidationSummary(
        total_candidates=len(validations),
        exact_match_count=statuses[ProductMatchStatus.EXACT_MATCH],
        probable_match_count=statuses[ProductMatchStatus.PROBABLE_MATCH],
        uncertain_count=statuses[ProductMatchStatus.UNCERTAIN],
        rejected_count=statuses[ProductMatchStatus.REJECTED],
        primary_eligible_count=sum(
            1
            for validation in validations
            if validation.match_result.eligible_for_price_aggregation
        ),
        official_match_count=relationships[ProductRelationship.OFFICIAL_EXACT_PRODUCT],
        official_variant_count=relationships[ProductRelationship.OFFICIAL_SAME_PRODUCT_FAMILY],
        licensed_alternative_count=relationships[
            ProductRelationship.LICENSED_THIRD_PARTY_ALTERNATIVE
        ],
        compatible_alternative_count=relationships[
            ProductRelationship.GENERIC_COMPATIBLE_ALTERNATIVE
        ],
        accessory_or_replacement_count=relationships[ProductRelationship.ACCESSORY_OR_REPLACEMENT],
        alternate_variant_count=groups["alternate_variant"] + groups["official_variant"],
        alternate_package_count=groups["alternate_package"],
        alternate_condition_count=groups["alternate_condition"],
        matcher_version=config.matcher_version,
        scoring_policy_version=SCORING_POLICY_VERSION,
        normalization_version=NORMALIZATION_VERSION,
    )


def _conflict(
    *,
    code: str,
    field: str,
    expected: object,
    observed: object,
    severity: MatchConflictSeverity,
    explanation: str,
) -> MatchConflict:
    return MatchConflict(
        code=code,
        field=field,
        expected=expected,
        observed=observed,
        severity=severity,
        explanation=explanation,
    )


def _identifier_score(
    product: ProductIdentity, listing: NormalizedMarketplaceListing
) -> float | None:
    matched = False
    compared = False
    for field_name in IDENTIFIER_FIELDS:
        expected = normalize_identifier(getattr(product, field_name), field_name)
        observed = normalize_identifier(getattr(listing, field_name), field_name)
        if expected and observed:
            compared = True
            matched = matched or expected == observed
    if matched:
        return 1.0
    return 0.0 if compared else None


def _brand_score(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    config: ProductMatcherConfig,
    official_verification: OfficialNameVerification,
) -> float | None:
    expected = normalize_brand(product.brand)
    if not expected:
        return None
    if official_verification.expected_brand_present_only_as_compatibility_target:
        return 0.0
    observed = normalize_brand(official_verification.detected_listing_brand or listing.brand)
    if observed:
        return 1.0 if _is_expected_brand_or_manufacturer(product, observed) else 0.0
    if expected in _tokens(_title_without_compatibility_phrases(listing)):
        return 0.85
    return 0.0 if config.require_brand else None


def _brand_owner_score(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    official_verification: OfficialNameVerification,
) -> float | None:
    if not product.target_is_official_product:
        return None
    if listing.brand_role == BrandRole.OFFICIAL_BRAND:
        return 1.0
    if listing.brand_role == BrandRole.MANUFACTURER_BRAND:
        return 0.85
    if official_verification.expected_brand_present_only_as_compatibility_target:
        return 0.0
    if listing.brand_role == BrandRole.THIRD_PARTY_BRAND:
        return 0.0
    return None


def _manufacturer_score(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    official_verification: OfficialNameVerification,
) -> float | None:
    if not product.target_is_official_product:
        return None
    manufacturer = official_verification.detected_manufacturer or listing.manufacturer
    if manufacturer:
        return 1.0 if _is_manufacturer_alias(product, manufacturer) else 0.0
    if listing.brand_role == BrandRole.MANUFACTURER_BRAND:
        return 1.0
    return None


def _official_product_line_score(
    official_verification: OfficialNameVerification,
) -> float | None:
    if official_verification.official_product_line_match is True:
        return 1.0
    if official_verification.official_product_line_match is False:
        return 0.0
    return None


def _model_score(product: ProductIdentity, listing: NormalizedMarketplaceListing) -> float | None:
    expected = normalize_model_number(product.model_number)
    if not expected:
        return None
    observed = normalize_model_number(listing.model_number) or extract_model_number(
        listing.title, listing.description_excerpt
    )
    if not observed:
        return None
    return 1.0 if expected == observed else 0.0


def _important_token_score(
    product: ProductIdentity, listing: NormalizedMarketplaceListing
) -> float:
    important = _important_tokens(product)
    if not important:
        return 0.0
    listing_tokens = _tokens(listing.normalized_title)
    covered = sum(1 for token in important if token in listing_tokens)
    return covered / len(important)


def _product_type_score(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
) -> float | None:
    product_terms = _product_noun_tokens(product)
    listing_tokens = _tokens(listing.normalized_title)
    if not product_terms:
        return None
    if not listing_tokens:
        return None
    return 1.0 if product_terms.intersection(listing_tokens) else 0.0


def _category_score(
    product: ProductIdentity, listing: NormalizedMarketplaceListing
) -> float | None:
    expected = normalize_text(product.category)
    observed = normalize_text(listing.category)
    if not expected or not observed:
        return None
    return _dice_score(_tokens(expected), _tokens(observed))


def _variant_score(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    config: ProductMatcherConfig,
) -> float | None:
    expected_capacity = _first_capacity_token(product.variant, product.product_name)
    observed_capacity = _first_capacity_token(
        listing.variant, listing.title, listing.description_excerpt
    )
    if expected_capacity and observed_capacity:
        return 1.0 if expected_capacity == observed_capacity else 0.0
    expected_edition = _edition_signature(product.product_name, product.variant)
    observed_edition = _edition_signature(listing.title, listing.variant)
    if expected_edition or observed_edition:
        return 1.0 if expected_edition == observed_edition else 0.0
    if config.color_strict and product.color:
        expected_color = normalize_text(product.color)
        observed_color = normalize_text(listing.color) or _first_color_token(listing.title)
        if expected_color and observed_color:
            return 1.0 if expected_color == observed_color else 0.0
    return None


def _package_score(product: ProductIdentity, listing: NormalizedMarketplaceListing) -> float | None:
    expected = product.pack_quantity
    observed = listing.pack_quantity
    if expected and observed:
        return 1.0 if expected == observed else 0.0
    if observed and observed > 1:
        return 0.0
    return None


def _condition_score(
    product: ProductIdentity, listing: NormalizedMarketplaceListing
) -> float | None:
    if product.expected_condition is None or listing.condition is None:
        return None
    return 1.0 if product.expected_condition == listing.condition else 0.0


def _registry_match_for_identity(
    *,
    explicit_brand: str | None,
    identity_text_values: Iterable[str | None],
) -> RegistryMatch | None:
    text = normalize_text(" ".join(value for value in identity_text_values if value))
    explicit_brand_norm = normalize_brand(explicit_brand)
    for entry in BRAND_REGISTRY:
        manufacturer_aliases_norm = {
            normalize_brand(alias) for alias in entry.manufacturer_aliases if normalize_brand(alias)
        }
        for sub_brand in entry.sub_brands:
            sub_brand_aliases_norm = {
                normalize_brand(alias) for alias in sub_brand.aliases if normalize_brand(alias)
            }
            allowed = manufacturer_aliases_norm.union(sub_brand_aliases_norm)
            if explicit_brand_norm and explicit_brand_norm not in allowed:
                continue
            sub_brand_seen = any(_contains_phrase(text, alias) for alias in sub_brand.aliases)
            line_match = _best_official_product_line(text, sub_brand.official_product_lines)
            if not sub_brand_seen and not line_match:
                continue
            return RegistryMatch(
                manufacturer=entry.manufacturer,
                manufacturer_aliases=entry.manufacturer_aliases,
                sub_brand=sub_brand.name,
                sub_brand_aliases=sub_brand.aliases,
                official_product_line=line_match,
                official_product_lines=sub_brand.official_product_lines,
                known_licensed_third_party_brands=sub_brand.known_licensed_third_party_brands,
            )
    return None


def _target_looks_like_official_product(
    *,
    brand: str | None,
    product_name: str,
    marketplace_query: str | None,
    registry_match: RegistryMatch | None,
) -> bool:
    if registry_match:
        return True
    if not brand:
        return False
    identity_text = normalize_text(
        " ".join(part for part in (product_name, marketplace_query) if part)
    )
    return _contains_phrase(identity_text, brand)


def _detect_compatibility_targets(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
) -> tuple[list[str], list[str]]:
    text = normalize_text(
        " ".join(part for part in (listing.title, listing.description_excerpt) if part)
    )
    targets: list[str] = []
    phrases: list[str] = []
    for alias in sorted(_expected_brand_aliases(product), key=len, reverse=True):
        alias_norm = normalize_text(alias)
        if not alias_norm:
            continue
        alias_pattern = re.escape(alias_norm).replace(r"\ ", r"\s+")
        for template in COMPATIBILITY_PHRASE_TEMPLATES:
            template_pattern = re.escape(template).replace(r"\ ", r"\s+")
            pattern = re.compile(rf"\b{template_pattern}\s+{alias_pattern}\b")
            for match in pattern.finditer(text):
                targets.append(alias)
                phrases.append(match.group(0))
        reverse_pattern = re.compile(rf"\b{alias_pattern}\s+compatible\b")
        for match in reverse_pattern.finditer(text):
            targets.append(alias)
            phrases.append(match.group(0))
    return _dedupe_preserve_order(targets), _dedupe_preserve_order(phrases)


def _extract_title_brand(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
) -> str | None:
    title = listing.title.strip()
    title_norm = normalize_text(title)
    known_prefixes = [
        *_expected_brand_aliases(product),
        *_known_licensed_third_party_brands(product),
    ]
    for alias in sorted(_dedupe_preserve_order(known_prefixes), key=len, reverse=True):
        if _starts_with_phrase(title_norm, alias):
            return alias

    product_terms = _product_noun_tokens(product).union(_tokens(product.normalized_product_name))
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9&.+-]*", title)
    for token in tokens[:4]:
        normalized = normalize_brand(token)
        if not normalized:
            continue
        if normalized in TITLE_BRAND_SKIP_TERMS:
            continue
        if normalized in product_terms or normalized in COLOR_TERMS:
            continue
        if _is_retailer_or_seller_name(normalized):
            continue
        return token
    return None


def _brand_role(
    *,
    product: ProductIdentity,
    detected_brand: str | None,
    compatibility_targets: list[str],
) -> BrandRole:
    if detected_brand:
        if _is_brand_alias(product, detected_brand):
            return BrandRole.OFFICIAL_BRAND
        if _is_manufacturer_alias(product, detected_brand):
            return BrandRole.MANUFACTURER_BRAND
        if not _is_retailer_or_seller_name(detected_brand):
            return BrandRole.THIRD_PARTY_BRAND
    if compatibility_targets:
        return BrandRole.COMPATIBILITY_TARGET
    return BrandRole.UNKNOWN


def _expected_brand_only_as_compatibility_target(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
) -> bool:
    if not product.target_is_official_product:
        return False
    if not listing.compatibility_targets:
        return False
    if listing.brand_role in {BrandRole.OFFICIAL_BRAND, BrandRole.MANUFACTURER_BRAND}:
        return False
    remaining = _title_without_compatibility_phrases(listing)
    return not any(_contains_phrase(remaining, alias) for alias in _expected_brand_aliases(product))


def _matched_official_line(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
) -> tuple[str | None, bool]:
    if listing.product_line:
        exact = normalize_text(listing.product_line) == normalize_text(
            product.official_product_line
        )
        return listing.product_line, exact
    text = _title_without_compatibility_phrases(listing)
    for line in product.official_name_patterns:
        line_norm = normalize_text(line)
        if _contains_phrase(text, line):
            return line, line_norm == normalize_text(product.official_product_line)
    for line in product.official_name_patterns:
        line_tokens = _tokens(line)
        if line_tokens and line_tokens.issubset(_tokens(text)):
            return line, normalize_text(line) == normalize_text(product.official_product_line)
    return None, False


def _best_official_product_line(text: str, lines: Iterable[str]) -> str | None:
    text_tokens = _tokens(text)
    for line in lines:
        if _contains_phrase(text, line):
            return line
    for line in lines:
        line_tokens = _tokens(line)
        if line_tokens and line_tokens.issubset(text_tokens):
            return line
    return None


def _final_relationship(
    *,
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    official_verification: OfficialNameVerification,
    conflicts: list[MatchConflict],
    score: float,
) -> ProductRelationship:
    codes = {conflict.code for conflict in conflicts}
    if "ACCESSORY_MISMATCH" in codes:
        return ProductRelationship.ACCESSORY_OR_REPLACEMENT
    if official_verification.relationship != ProductRelationship.UNKNOWN:
        return official_verification.relationship
    if "BUNDLE_MISMATCH" in codes:
        return ProductRelationship.UNRELATED
    if not product.target_is_official_product:
        return ProductRelationship.UNKNOWN
    if product.target_is_official_product and score >= 0.45:
        return ProductRelationship.UNKNOWN
    if score < 0.35:
        return ProductRelationship.UNRELATED
    return ProductRelationship.UNKNOWN


def _relationship_confidence(score: float, relationship: ProductRelationship) -> float:
    floors = {
        ProductRelationship.LICENSED_THIRD_PARTY_ALTERNATIVE: 0.96,
        ProductRelationship.GENERIC_COMPATIBLE_ALTERNATIVE: 0.94,
        ProductRelationship.ACCESSORY_OR_REPLACEMENT: 0.96,
        ProductRelationship.UNRELATED: 0.9,
        ProductRelationship.OFFICIAL_EXACT_PRODUCT: 0.82,
        ProductRelationship.OFFICIAL_SAME_PRODUCT_FAMILY: 0.88,
    }
    return max(score, floors.get(relationship, score))


def _claims_licensed(listing: NormalizedMarketplaceListing) -> bool:
    text = normalize_text(
        " ".join(part for part in (listing.title, listing.description_excerpt) if part)
    )
    return "officially licensed" in text or "licensed for" in text


def _claims_official(listing: NormalizedMarketplaceListing) -> bool:
    text = normalize_text(
        " ".join(part for part in (listing.title, listing.description_excerpt) if part)
    )
    return "official" in text and "officially licensed" not in text


def _has_unrequested_variant(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
) -> bool:
    if product.color:
        return False
    listing_color = normalize_text(listing.color) or _first_color_token(listing.title)
    return bool(listing_color)


def _expected_brand_aliases(product: ProductIdentity) -> list[str]:
    return _dedupe_preserve_order(
        [
            *(product.allowed_brand_aliases or []),
            *(product.allowed_manufacturer_aliases or []),
            product.brand,
            product.manufacturer,
            product.sub_brand,
        ]
    )


def _known_licensed_third_party_brands(product: ProductIdentity) -> list[str]:
    expected_aliases = {normalize_brand(alias) for alias in _expected_brand_aliases(product)}
    licensed: list[str] = []
    for entry in BRAND_REGISTRY:
        manufacturer_aliases = {
            normalize_brand(alias) for alias in entry.manufacturer_aliases if normalize_brand(alias)
        }
        for sub_brand in entry.sub_brands:
            sub_aliases = {
                normalize_brand(alias) for alias in sub_brand.aliases if normalize_brand(alias)
            }
            if expected_aliases.intersection(manufacturer_aliases.union(sub_aliases)):
                licensed.extend(sub_brand.known_licensed_third_party_brands)
    return _dedupe_preserve_order(licensed)


def _is_known_licensed_brand(product: ProductIdentity, value: str | None) -> bool:
    observed = normalize_brand(value)
    if not observed:
        return False
    return observed in {
        normalize_brand(alias)
        for alias in _known_licensed_third_party_brands(product)
        if normalize_brand(alias)
    }


def _is_expected_brand_or_manufacturer(product: ProductIdentity, value: str | None) -> bool:
    return _is_brand_alias(product, value) or _is_manufacturer_alias(product, value)


def _is_brand_alias(product: ProductIdentity, value: str | None) -> bool:
    observed = normalize_brand(value)
    if not observed:
        return False
    aliases = [*(product.allowed_brand_aliases or []), product.brand, product.sub_brand]
    return observed in {normalize_brand(alias) for alias in aliases if normalize_brand(alias)}


def _is_manufacturer_alias(product: ProductIdentity, value: str | None) -> bool:
    observed = normalize_brand(value)
    if not observed:
        return False
    aliases = [*(product.allowed_manufacturer_aliases or []), product.manufacturer]
    return observed in {normalize_brand(alias) for alias in aliases if normalize_brand(alias)}


def _is_retailer_or_seller_name(value: str | None) -> bool:
    normalized = normalize_brand(value)
    return bool(normalized and normalized in RETAILER_OR_SELLER_NAMES)


def _title_without_compatibility_phrases(listing: NormalizedMarketplaceListing) -> str:
    text = normalize_text(
        " ".join(part for part in (listing.title, listing.description_excerpt) if part)
    )
    for phrase in listing.compatibility_phrases:
        text = re.sub(rf"\b{re.escape(normalize_text(phrase))}\b", " ", text)
    return normalize_text(text)


def _contains_phrase(text: str, phrase: str | None) -> bool:
    phrase_norm = normalize_text(phrase)
    text_norm = normalize_text(text)
    if not phrase_norm or not text_norm:
        return False
    return re.search(rf"(?<!\w){re.escape(phrase_norm)}(?!\w)", text_norm) is not None


def _starts_with_phrase(text: str, phrase: str | None) -> bool:
    phrase_norm = normalize_text(phrase)
    text_norm = normalize_text(text)
    if not phrase_norm or not text_norm:
        return False
    return re.match(rf"^{re.escape(phrase_norm)}(?:\b|\s)", text_norm) is not None


def _display_brand(product: ProductIdentity) -> str:
    return product.brand or product.manufacturer or product.product_name


def _dedupe_preserve_order(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if not value:
            continue
        normalized = normalize_text(value)
        if not normalized or normalized in seen:
            continue
        deduped.append(value)
        seen.add(normalized)
    return deduped


def _variant_conflict(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    config: ProductMatcherConfig,
) -> MatchConflict | None:
    expected_capacity = _first_capacity_token(product.variant, product.product_name)
    observed_capacity = _first_capacity_token(
        listing.variant, listing.title, listing.description_excerpt
    )
    if expected_capacity and observed_capacity and expected_capacity != observed_capacity:
        return _conflict(
            code="VARIANT_MISMATCH",
            field="variant",
            expected=expected_capacity,
            observed=observed_capacity,
            severity=MatchConflictSeverity.MEDIUM,
            explanation="The listing differs in capacity, size, storage, or another variant token.",
        )
    expected_edition = _edition_signature(product.product_name, product.variant)
    observed_edition = _edition_signature(listing.title, listing.variant)
    if expected_edition != observed_edition and (expected_edition or observed_edition):
        return _conflict(
            code="VARIANT_MISMATCH",
            field="variant",
            expected=" ".join(sorted(expected_edition)) or "base",
            observed=" ".join(sorted(observed_edition)) or "base",
            severity=MatchConflictSeverity.MEDIUM,
            explanation="The listing differs in edition, such as base, Pro, Max, Plus, or Mini.",
        )
    if config.color_strict and product.color:
        expected_color = normalize_text(product.color)
        observed_color = normalize_text(listing.color) or _first_color_token(listing.title)
        if expected_color and observed_color and expected_color != observed_color:
            return _conflict(
                code="VARIANT_MISMATCH",
                field="color",
                expected=product.color,
                observed=listing.color or observed_color,
                severity=MatchConflictSeverity.MEDIUM,
                explanation="The listing color differs while color-strict matching is enabled.",
            )
    return None


def _condition_conflict(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    config: ProductMatcherConfig,
) -> MatchConflict | None:
    if listing.condition is None or listing.condition in {
        ProductCondition.NEW,
        ProductCondition.UNKNOWN,
    }:
        return None
    if listing.condition == ProductCondition.REFURBISHED and not config.exclude_refurbished:
        return None
    if (
        listing.condition
        in {
            ProductCondition.OPEN_BOX,
            ProductCondition.USED_LIKE_NEW,
            ProductCondition.USED_GOOD,
            ProductCondition.USED_ACCEPTABLE,
            ProductCondition.FOR_PARTS,
        }
        and not config.exclude_used
    ):
        return None
    expected = product.expected_condition or ProductCondition.NEW
    return _conflict(
        code="CONDITION_MISMATCH",
        field="condition",
        expected=expected,
        observed=listing.condition,
        severity=MatchConflictSeverity.HIGH,
        explanation="The listing condition is not eligible for new-product price aggregation.",
    )


def _aggregation_group(
    status: ProductMatchStatus,
    conflicts: list[MatchConflict],
    relationship: ProductRelationship,
) -> str | None:
    if relationship == ProductRelationship.LICENSED_THIRD_PARTY_ALTERNATIVE:
        return "licensed_alternative"
    if relationship == ProductRelationship.GENERIC_COMPATIBLE_ALTERNATIVE:
        return "compatible_alternative"
    if relationship == ProductRelationship.ACCESSORY_OR_REPLACEMENT:
        return "accessory_or_replacement"
    if relationship == ProductRelationship.OFFICIAL_SAME_PRODUCT_FAMILY:
        return "official_variant"
    codes = {conflict.code for conflict in conflicts}
    if "PACKAGE_QUANTITY_MISMATCH" in codes:
        return "alternate_package"
    if "CONDITION_MISMATCH" in codes:
        return "alternate_condition"
    if "VARIANT_MISMATCH" in codes:
        return "alternate_variant"
    if "BUNDLE_MISMATCH" in codes:
        return "alternate_bundle"
    if status in {ProductMatchStatus.EXACT_MATCH, ProductMatchStatus.PROBABLE_MATCH}:
        return "primary"
    return None


def _matched_fields(scores: MatchFeatureScores) -> list[str]:
    fields = {
        "identifier": scores.identifier_score,
        "brand": scores.brand_score,
        "brand_owner": scores.brand_owner_score,
        "manufacturer": scores.manufacturer_score,
        "official_product_line": scores.official_product_line_score,
        "model_number": scores.model_score,
        "title": scores.title_score,
        "important_tokens": scores.important_token_score,
        "product_type": scores.product_type_score,
        "category": scores.category_score,
        "variant": scores.variant_score,
        "package": scores.package_score,
        "condition": scores.condition_score,
    }
    return [name for name, value in fields.items() if value is not None and value >= 0.8]


def _unknown_fields(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
    scores: MatchFeatureScores,
) -> list[str]:
    unknown: list[str] = []
    if product.model_number and scores.model_score is None:
        unknown.append("model_number")
    if product.brand and scores.brand_score is None:
        unknown.append("brand")
    if not any(
        getattr(product, field_name) and getattr(listing, field_name)
        for field_name in IDENTIFIER_FIELDS
    ):
        unknown.append("identifier")
    if scores.variant_score is None and (product.variant or listing.variant):
        unknown.append("variant")
    if scores.package_score is None and (product.pack_quantity or listing.pack_quantity):
        unknown.append("pack_quantity")
    if scores.condition_score is None and (product.expected_condition or listing.condition):
        unknown.append("condition")
    return unknown


def _reason_codes(
    status: ProductMatchStatus,
    relationship: ProductRelationship,
    official_verification: OfficialNameVerification,
    conflicts: list[MatchConflict],
    matched_fields: list[str],
    eligible: bool,
) -> list[str]:
    codes = [*official_verification.reason_codes, *[conflict.code for conflict in conflicts]]
    codes.append(status.upper())
    codes.append(relationship.upper())
    if matched_fields:
        codes.append("MATCHED_" + "_".join(field.upper() for field in matched_fields[:3]))
    if eligible:
        codes.append("ELIGIBLE_FOR_PRIMARY_PRICE_AGGREGATION")
    return codes


def _human_summary(
    status: ProductMatchStatus,
    relationship: ProductRelationship,
    score: float,
    conflicts: list[MatchConflict],
    group: str | None,
) -> str:
    if relationship == ProductRelationship.LICENSED_THIRD_PARTY_ALTERNATIVE:
        return (
            "Licensed third-party compatible alternative; excluded from official product price "
            f"aggregation. Confidence {score:.2f}."
        )
    if relationship == ProductRelationship.GENERIC_COMPATIBLE_ALTERNATIVE:
        return (
            "Compatible third-party alternative; excluded from official product price "
            f"aggregation. Confidence {score:.2f}."
        )
    if relationship == ProductRelationship.OFFICIAL_SAME_PRODUCT_FAMILY:
        return (
            "Official product-family variant; separated from exact official price aggregation. "
            f"Confidence {score:.2f}; aggregation group {group or 'none'}."
        )
    if relationship == ProductRelationship.ACCESSORY_OR_REPLACEMENT:
        return (
            "Accessory or replacement part; excluded from product price aggregation. "
            f"Confidence {score:.2f}."
        )
    if conflicts:
        main = conflicts[0]
        return (
            f"{status.value.replace('_', ' ').title()} because {main.explanation} "
            f"Score {score:.2f}; aggregation group {group or 'none'}."
        )
    if status == ProductMatchStatus.EXACT_MATCH:
        return f"Exact product match with strong identifier or model agreement. Score {score:.2f}."
    if status == ProductMatchStatus.PROBABLE_MATCH:
        return (
            "Probable product match based on deterministic title and identity signals. "
            f"Score {score:.2f}."
        )
    if status == ProductMatchStatus.UNCERTAIN:
        return f"Needs review because identity evidence is incomplete. Score {score:.2f}."
    return f"Rejected because deterministic similarity is too low. Score {score:.2f}."


def _has_sufficient_evidence(scores: MatchFeatureScores, config: ProductMatcherConfig) -> bool:
    if config.require_brand and scores.brand_score is None:
        return False
    if scores.brand_score is not None and scores.brand_score < 0.5:
        return False
    return (
        scores.model_score == 1.0
        or scores.identifier_score == 1.0
        or (scores.title_score >= 0.78 and scores.important_token_score >= 0.65)
        or (
            scores.title_score >= 0.74
            and scores.important_token_score >= 0.74
            and scores.product_type_score == 1.0
        )
    )


def _is_accessory_listing(
    product: ProductIdentity,
    listing: NormalizedMarketplaceListing,
) -> bool:
    product_text = normalize_text(
        " ".join(
            part for part in (product.product_name, product.product_type, product.category) if part
        )
    )
    if ACCESSORY_PRODUCT_TERMS.intersection(_tokens(product_text)):
        return False
    listing_text = normalize_text(" ".join([listing.title, listing.description_excerpt or ""]))
    return any(indicator in listing_text for indicator in ACCESSORY_INDICATORS)


def _is_bundle_listing(listing: NormalizedMarketplaceListing) -> bool:
    text = normalize_text(" ".join([listing.title, listing.description_excerpt or ""]))
    return any(indicator in text for indicator in BUNDLE_INDICATORS)


def _dedupe_validations(
    validations: list[MarketplaceListingValidation],
) -> list[MarketplaceListingValidation]:
    seen: set[str] = set()
    deduped: list[MarketplaceListingValidation] = []
    for validation in validations:
        listing = validation.listing
        key = listing.source_url or f"{listing.provider}:{listing.platform}:{listing.listing_id}"
        if key in seen:
            continue
        deduped.append(validation)
        seen.add(key)
    return deduped


def _score_platform_group(group: list[MarketplaceListingValidation]) -> float:
    listings = [validation.listing for validation in group]
    offer_score = min(len(listings) / 5, 1.0) * 0.35
    positions = [_rank_signal_value(listing, "position") for listing in listings]
    numeric_positions = [position for position in positions if position is not None]
    best_position = min(numeric_positions) if numeric_positions else 20.0
    position_score = max(0.0, 1.0 - ((best_position - 1) / 40)) * 0.25
    reviews = sum(listing.review_count or 0 for listing in listings)
    review_score = min(math.log10(reviews + 1) / 5, 1.0) * 0.25
    price_score = (
        1.0 if any(listing.landed_price is not None for listing in listings) else 0.0
    ) * 0.15
    return offer_score + position_score + review_score + price_score


def _group_confidence(group: list[MarketplaceListingValidation]) -> float:
    if not group:
        return 0.0
    average_match_score = sum(item.match_result.score for item in group) / len(group)
    coverage_bonus = 0.05 if len(group) > 1 else 0.0
    return round(min(0.92, average_match_score * 0.8 + 0.1 + coverage_bonus), 3)


def _overall_confidence(validations: list[MarketplaceListingValidation]) -> float:
    eligible = [
        item.match_result.score
        for item in validations
        if item.match_result.eligible_for_price_aggregation
    ]
    if eligible:
        return round(min(0.9, sum(eligible) / len(eligible)), 3)
    if not validations:
        return 0.0
    return round(sum(item.match_result.score for item in validations) / len(validations), 3)


def _rank_signal_value(listing: NormalizedMarketplaceListing, name: str) -> float | None:
    for signal in listing.raw_rank_signals:
        if signal.name == name:
            return signal.value
    return None


def _max_rank_signal(listings: list[NormalizedMarketplaceListing], name: str) -> float | None:
    values = [
        signal.value
        for listing in listings
        for signal in listing.raw_rank_signals
        if signal.name == name
    ]
    return max(values) if values else None


def _best_rank_signal_source(listings: list[NormalizedMarketplaceListing], name: str) -> str | None:
    for listing in listings:
        for signal in listing.raw_rank_signals:
            if signal.name == name and signal.source:
                return signal.source
    return None


def _single_currency(listings: list[NormalizedMarketplaceListing]) -> str | None:
    currencies = {listing.currency for listing in listings if listing.currency}
    if len(currencies) == 1:
        return currencies.pop()
    return None


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.split(r"\s+", normalize_text(value))
        if token and token not in STOPWORDS
    }


def _important_tokens(product: ProductIdentity) -> set[str]:
    tokens: set[str] = set()
    if product.brand:
        tokens.update(_tokens(product.brand))
    if product.manufacturer:
        tokens.update(_tokens(product.manufacturer))
    if product.model_number:
        normalized_model = normalize_model_number(product.model_number)
        if normalized_model:
            tokens.add(normalized_model.casefold())
    for value in (product.product_name, product.variant):
        tokens.update(_tokens(value or ""))
    return {token for token in tokens if len(token) > 1 and token not in STOPWORDS}


def _product_noun_tokens(product: ProductIdentity) -> set[str]:
    candidates = _tokens(
        " ".join(part for part in (product.product_name, product.product_type) if part)
    )
    for alias in _expected_brand_aliases(product):
        candidates.difference_update(_tokens(alias))
    if product.model_number:
        normalized_model = normalize_model_number(product.model_number)
        if normalized_model:
            candidates.discard(normalized_model.casefold())
    return {token for token in candidates if len(token) > 2 and token not in COLOR_TERMS}


def _dice_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return (2 * len(left.intersection(right))) / (len(left) + len(right))


def _first_capacity_token(*values: str | None) -> str | None:
    text = " ".join(value for value in values if value)
    for match in CAPACITY_PATTERN.finditer(text):
        return f"{match.group('value').lower()}{_normalize_unit(match.group('unit'))}"
    return None


def _first_color_token(*values: str | None) -> str | None:
    for token in _tokens(" ".join(value for value in values if value)):
        if token in COLOR_TERMS:
            return token
    return None


def _edition_signature(*values: str | None) -> set[str]:
    return {
        token
        for token in _tokens(" ".join(value for value in values if value))
        if token in EDITION_TOKENS
    }


def _linked_value(value: object) -> str | None:
    if value is None:
        return None
    raw = getattr(value, "value", None)
    return raw if isinstance(raw, str) and raw.strip() else None


def _first_linked_value(values: Iterable[object]) -> str | None:
    for value in values:
        linked = _linked_value(value)
        if linked:
            return linked
    return None


def _normalize_unit(value: str) -> str:
    normalized = value.casefold()
    if normalized in {"ounce", "ounces"}:
        return "oz"
    if normalized == "in":
        return "inch"
    return normalized


def _valid_gtin(value: str) -> bool:
    if not value.isdigit() or len(value) not in {8, 12, 13, 14}:
        return False
    digits = [int(char) for char in value]
    check_digit = digits.pop()
    total = 0
    for index, digit in enumerate(reversed(digits), start=1):
        total += digit * (3 if index % 2 == 1 else 1)
    return (10 - (total % 10)) % 10 == check_digit


def _valid_isbn10(value: str) -> bool:
    if len(value) != 10:
        return False
    total = 0
    for index, char in enumerate(value, start=1):
        if char == "X" and index == 10:
            digit = 10
        elif char.isdigit():
            digit = int(char)
        else:
            return False
        total += index * digit
    return total % 11 == 0


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


def _price_phrase(low: float | None, high: float | None) -> str:
    if low is None and high is None:
        return "unknown"
    if low == high:
        return f"${low:.2f}"
    return f"${low:.2f}-${high:.2f}"
