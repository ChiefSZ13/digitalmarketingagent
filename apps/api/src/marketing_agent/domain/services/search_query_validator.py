"""Validate generated keyword candidates as realistic human search queries."""

from __future__ import annotations

import re
from dataclasses import dataclass

from marketing_agent.domain.models.keyword import SearchQueryRejectionReason
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.keyword_normalizer import normalize_keyword

TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
CAPACITY_RE = re.compile(r"\b\d+(?:,\d{3})?\s?(?:btu|gb|tb|oz|ml|sq\s?ft|inch|in)\b")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}
BANNED_PHRASES = {
    "features a",
    "features an",
    "comes with",
    "allows the",
    "allows users",
    "it uses",
    "includes a",
    "includes an",
    "designed to provide",
    "designed for people",
    "which makes it",
    "this product",
    "has a",
    "is designed",
    "is a",
    "that can",
    "for people who",
    "for users who",
}
SENTENCE_PUNCTUATION_RE = re.compile(r"[.!?;:]")


@dataclass(frozen=True)
class SearchQueryValidationResult:
    normalized_query: str
    word_count: int
    product_relevance_score: float
    query_realism_score: float
    specificity_score: float
    commercial_intent_score: float
    rejection_reasons: list[SearchQueryRejectionReason]

    @property
    def eligible_for_live_enrichment(self) -> bool:
        return (
            not self.rejection_reasons
            and self.product_relevance_score >= 0.55
            and self.query_realism_score >= 0.7
        )


class SearchQueryValidator:
    """Apply deterministic guardrails before a term can reach enrichment."""

    def __init__(self, profile: ProductProfile) -> None:
        self._source_text = normalize_keyword(" ".join(_profile_texts(profile)))
        self._profile_terms = _important_terms(_profile_texts(profile))

    def validate(
        self, query: str, source_concepts: list[str] | None = None
    ) -> SearchQueryValidationResult:
        normalized_query = normalize_keyword(query)
        tokens = _tokens(normalized_query)
        source_terms = _important_terms(source_concepts or [])
        product_relevance = _product_relevance(tokens, self._profile_terms.union(source_terms))
        query_realism = _query_realism_score(query, tokens)
        specificity = _specificity_score(tokens)
        commercial_intent = _commercial_intent_score(normalized_query)
        reasons: list[SearchQueryRejectionReason] = []

        if not normalized_query:
            reasons.append(SearchQueryRejectionReason.EMPTY)
        if len(tokens) < 2:
            reasons.append(SearchQueryRejectionReason.TOO_SHORT)
        if len(tokens) > 10:
            reasons.append(SearchQueryRejectionReason.TOO_LONG)
        if SENTENCE_PUNCTUATION_RE.search(query):
            reasons.append(SearchQueryRejectionReason.SENTENCE_PUNCTUATION)
        if any(phrase in normalized_query for phrase in BANNED_PHRASES):
            reasons.append(SearchQueryRejectionReason.BANNED_PHRASE)
        if _copies_source_description(tokens, self._source_text):
            reasons.append(SearchQueryRejectionReason.DESCRIPTION_COPY)
        if _is_attribute_dense(normalized_query, tokens, source_terms):
            reasons.append(SearchQueryRejectionReason.ATTRIBUTE_DENSE)
        if product_relevance < 0.55:
            reasons.append(SearchQueryRejectionReason.LOW_PRODUCT_RELEVANCE)
        if query_realism < 0.7:
            reasons.append(SearchQueryRejectionReason.LOW_QUERY_REALISM)

        return SearchQueryValidationResult(
            normalized_query=normalized_query,
            word_count=len(tokens),
            product_relevance_score=round(product_relevance, 4),
            query_realism_score=round(query_realism, 4),
            specificity_score=round(specificity, 4),
            commercial_intent_score=round(commercial_intent, 4),
            rejection_reasons=list(dict.fromkeys(reasons)),
        )


def _profile_texts(profile: ProductProfile) -> list[str]:
    values: list[str] = []
    for field in (
        profile.product_name,
        profile.brand,
        profile.category,
        profile.subcategory,
        profile.marketplace_search_query,
        profile.summary,
    ):
        if field:
            values.append(field.value)
    for collection in (
        profile.visual_attributes,
        profile.observed_facts,
        profile.user_provided_facts,
        profile.inferred_attributes,
        profile.features,
        profile.benefits,
        profile.materials,
        profile.colors,
        profile.use_cases,
        profile.target_audiences,
        profile.differentiators,
    ):
        values.extend(item.value for item in collection)
    return values


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def _important_terms(values: list[str]) -> set[str]:
    terms: set[str] = set()
    for value in values:
        for token in _tokens(normalize_keyword(value)):
            if len(token) > 1 and token not in STOP_WORDS:
                terms.add(token)
    return terms


def _product_relevance(tokens: list[str], product_terms: set[str]) -> float:
    if not tokens:
        return 0.0
    meaningful = [token for token in tokens if token not in STOP_WORDS]
    if not meaningful:
        return 0.0
    overlap = set(meaningful).intersection(product_terms)
    denominator = max(1, min(3, len(set(meaningful))))
    return min(1.0, len(overlap) / denominator)


def _query_realism_score(query: str, tokens: list[str]) -> float:
    count = len(tokens)
    if count == 0:
        score = 0.0
    elif count == 1:
        score = 0.35
    elif 2 <= count <= 6:
        score = 1.0
    elif count <= 8:
        score = 0.78
    elif count <= 10:
        score = 0.62
    else:
        score = 0.15

    normalized = normalize_keyword(query)
    if SENTENCE_PUNCTUATION_RE.search(query):
        score -= 0.25
    if any(phrase in normalized for phrase in BANNED_PHRASES):
        score -= 0.35
    if tokens:
        stop_ratio = sum(1 for token in tokens if token in STOP_WORDS) / len(tokens)
        if stop_ratio > 0.45:
            score -= 0.12
    return max(0.0, min(1.0, score))


def _specificity_score(tokens: list[str]) -> float:
    count = len(tokens)
    if count <= 1:
        return 0.1
    if count == 2:
        return 0.7
    if 3 <= count <= 5:
        return 0.95
    if count == 6:
        return 0.85
    if count <= 8:
        return 0.65
    if count <= 10:
        return 0.45
    return 0.15


def _commercial_intent_score(normalized_query: str) -> float:
    if any(term in normalized_query for term in ("buy", "shop", "price", "deal", "for sale")):
        return 0.95
    if any(term in normalized_query for term in ("best", "review", "reviews", "vs", "compare")):
        return 0.78
    if any(term in normalized_query for term in ("near me", "coupon", "discount")):
        return 0.9
    if any(term in normalized_query for term in ("how", "what", "why", "guide")):
        return 0.35
    return 0.62


def _copies_source_description(tokens: list[str], source_text: str) -> bool:
    if len(tokens) < 7:
        return False
    max_window = min(6, len(tokens))
    for window in range(max_window, 4, -1):
        for index in range(0, len(tokens) - window + 1):
            phrase = " ".join(tokens[index : index + window])
            if phrase in source_text:
                return True
    return False


def _is_attribute_dense(normalized_query: str, tokens: list[str], source_terms: set[str]) -> bool:
    if len(tokens) < 8:
        return False
    capacity_hits = len(CAPACITY_RE.findall(normalized_query))
    concept_hits = len(set(tokens).intersection(source_terms))
    digit_hits = sum(1 for token in tokens if any(character.isdigit() for character in token))
    return capacity_hits + digit_hits + concept_hits >= 5
