"""Build provider-neutral marketplace search queries from normalized product data."""

import re
import unicodedata

from marketing_agent.domain.models.evidence import EvidenceLinkedText
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.run import ProductAnalysisRequest

MIN_PROFILE_QUERY_CONFIDENCE = 0.5

_EXPLICIT_IDENTIFIER_PATTERN = re.compile(
    r"\b(?:model(?:\s+number)?|style(?:\s+code)?|sku|mpn|part(?:\s+number)?|item(?:\s+number)?)"
    r"\s*[:#-]?\s*(?P<identifier>[A-Z0-9][A-Z0-9-]{2,})\b",
    flags=re.IGNORECASE,
)
_PRODUCT_IDENTIFIER_PATTERN = re.compile(r"\b(?=[A-Z0-9-]*\d)[A-Z][A-Z0-9-]{2,}\b")
_QUOTED_VARIANT_PATTERN = re.compile(r"\s*['\"“”‘’][^'\"“”‘’]+['\"“”‘’]\s*")
_PAREN_VARIANT_PATTERN = re.compile(r"\s*\([^)]{1,80}\)\s*")
_FOOTWEAR_TERMS = (
    "shoe",
    "shoes",
    "sneaker",
    "sneakers",
    "footwear",
    "jordan",
    "air max",
    "air force",
    "yeezy",
    "dunk",
    "retro",
)


def build_marketplace_search_query(
    *, request: ProductAnalysisRequest, profile: ProductProfile
) -> str:
    """Return the cleanest product identity to send to marketplace data providers."""
    model_query = _usable_text(profile.marketplace_search_query)
    if model_query:
        return model_query

    brand = _usable_text(profile.brand)
    product_name = _core_product_name(_usable_text(profile.product_name), profile)
    identifier = _best_identifier(profile)

    if identifier and brand:
        return _dedupe_words(f"{brand} {identifier}")
    if identifier and product_name:
        return _dedupe_words(f"{product_name} {identifier}")
    if product_name and brand and not _contains_word(product_name, brand):
        return _dedupe_words(f"{brand} {product_name}")
    if product_name:
        return product_name
    if brand:
        category = _usable_text(profile.category) or _usable_text(profile.subcategory)
        if category:
            return _dedupe_words(f"{brand} {category}")

    fallback = _best_profile_phrase(profile)
    if fallback:
        return fallback

    return _normalize_spaces(request.description)


def _best_identifier(profile: ProductProfile) -> str | None:
    explicit_candidates: list[tuple[float, str]] = []
    generic_candidates: list[tuple[float, str]] = []
    for field in _identity_fields(profile):
        if field is None:
            continue
        text = _usable_text(field)
        if not text:
            continue
        for match in _EXPLICIT_IDENTIFIER_PATTERN.finditer(text):
            explicit_candidates.append(
                (field.confidence + 0.15, _clean_identifier(match.group("identifier")))
            )
        if field is profile.product_name:
            for match in _PRODUCT_IDENTIFIER_PATTERN.finditer(text):
                generic_candidates.append((field.confidence, _clean_identifier(match.group(0))))

    candidates = explicit_candidates or generic_candidates
    if not candidates:
        return None
    return sorted(candidates, reverse=True, key=lambda item: item[0])[0][1]


def _best_profile_phrase(profile: ProductProfile) -> str | None:
    candidates = [
        field
        for field in _identity_fields(profile)
        if field and field.confidence >= MIN_PROFILE_QUERY_CONFIDENCE
    ]
    if not candidates:
        return None
    return _usable_text(sorted(candidates, reverse=True, key=lambda item: item.confidence)[0])


def _identity_fields(profile: ProductProfile) -> list[EvidenceLinkedText | None]:
    return [
        profile.product_name,
        profile.brand,
        profile.category,
        profile.subcategory,
        *profile.user_provided_facts,
        *profile.observed_facts,
        *profile.inferred_attributes,
        *profile.features,
    ]


def _usable_text(field: EvidenceLinkedText | None) -> str | None:
    if field is None or field.confidence < MIN_PROFILE_QUERY_CONFIDENCE:
        return None
    value = _normalize_spaces(field.value)
    return value or None


def _core_product_name(product_name: str | None, profile: ProductProfile) -> str | None:
    if not product_name:
        return None
    cleaned = _normalize_spaces(
        _PAREN_VARIANT_PATTERN.sub(" ", _QUOTED_VARIANT_PATTERN.sub(" ", product_name))
    )
    if not _is_footwear_like(cleaned, profile):
        return cleaned

    tokens = cleaned.split(" ")
    for index, token in enumerate(tokens):
        if index < 2 or index == len(tokens) - 1:
            continue
        if re.fullmatch(r"\d+[A-Z]?", token, flags=re.IGNORECASE):
            return " ".join(tokens[: index + 1])
    return cleaned


def _is_footwear_like(product_name: str, profile: ProductProfile) -> bool:
    text = " ".join(
        value
        for value in (
            product_name,
            _usable_text(profile.brand),
            _usable_text(profile.category),
            _usable_text(profile.subcategory),
        )
        if value
    ).casefold()
    return any(term in text for term in _FOOTWEAR_TERMS)


def _normalize_spaces(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip()


def _clean_identifier(value: str) -> str:
    return _normalize_spaces(value).upper()


def _contains_word(text: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE))


def _dedupe_words(value: str) -> str:
    words: list[str] = []
    seen: set[str] = set()
    for word in _normalize_spaces(value).split(" "):
        key = word.casefold()
        if key in seen:
            continue
        words.append(word)
        seen.add(key)
    return " ".join(words)
