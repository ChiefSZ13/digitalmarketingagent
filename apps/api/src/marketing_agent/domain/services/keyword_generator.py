"""Generate realistic human search-query candidates from product concepts."""

from __future__ import annotations

import re
from dataclasses import dataclass

from marketing_agent.domain.models.evidence import EvidenceLinkedText
from marketing_agent.domain.models.keyword import (
    KeywordCandidate,
    KeywordCategory,
    KeywordIntent,
    MarketingTermType,
    ScoreComponents,
    SearchQueryCategory,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.keyword_normalizer import normalize_keyword
from marketing_agent.domain.services.keyword_scorer import rescore_candidate
from marketing_agent.domain.services.search_query_validator import (
    SearchQueryValidationResult,
    SearchQueryValidator,
)

GENERATOR_VERSION = "search-query-generator-v1"
CAPACITY_RE = re.compile(
    r"\b\d+(?:,\d{3})?\s?(?:btu|gb|tb|oz|ml|sq\.?\s?ft|square feet|inch|in)\b",
    re.IGNORECASE,
)
AIR_JORDAN_RE = re.compile(r"\bair\s+jordan\s+\d+\b", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
PRODUCT_TYPE_PATTERNS = (
    "window air conditioner",
    "air conditioner",
    "window ac",
    "coffee maker",
    "espresso machine",
    "xbox controller",
    "wireless controller",
    "game controller",
    "running shoes",
    "basketball shoes",
    "sneakers",
    "desk lamp",
    "table lamp",
    "floor lamp",
    "headphones",
    "backpack",
    "water bottle",
)
FEATURE_PHRASES = (
    "u shaped",
    "energy efficient",
    "smart",
    "inverter",
    "quiet",
    "portable",
    "rechargeable",
    "cordless",
    "wireless",
    "ergonomic",
    "programmable",
    "single serve",
    "thermal",
    "insulated",
    "nonstick",
    "lightweight",
    "breathable",
    "cushioned",
    "stainless steel",
)
DESCRIPTOR_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "comes",
    "designed",
    "features",
    "for",
    "from",
    "has",
    "in",
    "includes",
    "is",
    "it",
    "of",
    "on",
    "or",
    "provide",
    "provides",
    "that",
    "the",
    "this",
    "to",
    "uses",
    "with",
}
AUDIENCE_MARKERS = {
    "audience",
    "buyers",
    "customers",
    "people",
    "professionals",
    "researching",
    "shoppers",
    "users",
    "workers",
}
FAMILY_LIMITS: dict[SearchQueryCategory, int] = {
    SearchQueryCategory.BRAND_PRODUCT: 3,
    SearchQueryCategory.GENERIC_PRODUCT: 3,
    SearchQueryCategory.FEATURE: 4,
    SearchQueryCategory.USE_CASE: 3,
    SearchQueryCategory.PROBLEM_SOLUTION: 3,
    SearchQueryCategory.REVIEW: 2,
    SearchQueryCategory.COMPARISON: 2,
    SearchQueryCategory.TRANSACTIONAL: 3,
    SearchQueryCategory.LOCAL_OR_SIZE_SPECIFIC: 2,
}
FAMILY_CATEGORY: dict[SearchQueryCategory, KeywordCategory] = {
    SearchQueryCategory.BRAND_PRODUCT: KeywordCategory.PRODUCT,
    SearchQueryCategory.GENERIC_PRODUCT: KeywordCategory.PRODUCT,
    SearchQueryCategory.FEATURE: KeywordCategory.FEATURE,
    SearchQueryCategory.USE_CASE: KeywordCategory.USE_CASE,
    SearchQueryCategory.PROBLEM_SOLUTION: KeywordCategory.PROBLEM_SOLUTION,
    SearchQueryCategory.REVIEW: KeywordCategory.PRODUCT,
    SearchQueryCategory.COMPARISON: KeywordCategory.ALTERNATIVE,
    SearchQueryCategory.TRANSACTIONAL: KeywordCategory.LONG_TAIL,
    SearchQueryCategory.LOCAL_OR_SIZE_SPECIFIC: KeywordCategory.USE_CASE,
}
FAMILY_INTENT: dict[SearchQueryCategory, KeywordIntent] = {
    SearchQueryCategory.BRAND_PRODUCT: KeywordIntent.COMMERCIAL,
    SearchQueryCategory.GENERIC_PRODUCT: KeywordIntent.COMMERCIAL,
    SearchQueryCategory.FEATURE: KeywordIntent.COMMERCIAL,
    SearchQueryCategory.USE_CASE: KeywordIntent.COMMERCIAL,
    SearchQueryCategory.PROBLEM_SOLUTION: KeywordIntent.COMMERCIAL,
    SearchQueryCategory.REVIEW: KeywordIntent.COMMERCIAL,
    SearchQueryCategory.COMPARISON: KeywordIntent.COMPARISON,
    SearchQueryCategory.TRANSACTIONAL: KeywordIntent.TRANSACTIONAL,
    SearchQueryCategory.LOCAL_OR_SIZE_SPECIFIC: KeywordIntent.TRANSACTIONAL,
}


@dataclass(frozen=True)
class TermConcept:
    value: str
    evidence_ids: list[str]


@dataclass(frozen=True)
class SearchConceptSet:
    brand: TermConcept | None
    product_core: TermConcept
    product_type: TermConcept
    generic_products: list[TermConcept]
    feature_terms: list[TermConcept]
    use_case_terms: list[TermConcept]
    problem_terms: list[TermConcept]
    capacity_terms: list[TermConcept]


@dataclass(frozen=True)
class SearchQueryDraft:
    text: str
    query_family: SearchQueryCategory
    rationale: str
    evidence_ids: list[str]
    source_concepts: list[str]


def generate_keyword_candidates(profile: ProductProfile) -> list[KeywordCandidate]:
    """Return only validated search-query candidates for MVP 1B."""
    concepts = _build_concepts(profile)
    validator = SearchQueryValidator(profile)
    drafts = _build_search_query_drafts(concepts)
    candidates: list[KeywordCandidate] = []
    family_counts: dict[SearchQueryCategory, int] = {family: 0 for family in SearchQueryCategory}
    seen: set[str] = set()

    for draft in drafts:
        validation = validator.validate(draft.text, draft.source_concepts)
        normalized = validation.normalized_query
        if not normalized or normalized in seen:
            continue
        if family_counts[draft.query_family] >= FAMILY_LIMITS[draft.query_family]:
            continue
        if not validation.eligible_for_live_enrichment:
            continue
        seen.add(normalized)
        family_counts[draft.query_family] += 1
        candidates.append(_candidate_from_draft(draft, validation, profile))

    return sorted(candidates, key=lambda item: item.relevance_score, reverse=True)


def _build_concepts(profile: ProductProfile) -> SearchConceptSet:
    base_evidence = _fallback_evidence(profile)
    brand = _term_from_linked(profile.brand) if profile.brand else None
    product_source = (
        profile.marketplace_search_query
        or profile.product_name
        or profile.subcategory
        or profile.category
        or profile.summary
    )
    product_core = _term_from_linked(product_source)
    product_type = TermConcept(
        value=_product_type(product_core.value, brand.value if brand else None),
        evidence_ids=product_core.evidence_ids,
    )
    generic_products = _dedupe_concepts(
        [
            product_type,
            TermConcept(
                value=_without_brand(product_core.value, brand.value if brand else None),
                evidence_ids=product_core.evidence_ids,
            ),
            *(
                [
                    TermConcept(
                        value=_clean_phrase(profile.subcategory.value),
                        evidence_ids=profile.subcategory.evidence_ids,
                    )
                ]
                if profile.subcategory
                else []
            ),
        ]
    )
    features = _feature_concepts(profile, product_type.value, product_core.value, base_evidence)
    capacities = _capacity_concepts(profile, base_evidence)
    use_cases = _use_case_concepts(profile)
    problems = _problem_concepts(profile, product_type.value)

    return SearchConceptSet(
        brand=brand,
        product_core=product_core,
        product_type=product_type,
        generic_products=generic_products,
        feature_terms=features,
        use_case_terms=use_cases,
        problem_terms=problems,
        capacity_terms=capacities,
    )


def _build_search_query_drafts(concepts: SearchConceptSet) -> list[SearchQueryDraft]:
    drafts: list[SearchQueryDraft] = []
    base = concepts.product_type.value
    core = concepts.product_core.value
    brand_value = concepts.brand.value if concepts.brand else None
    brand_base = _join(brand_value, base)

    if brand_value:
        _add(
            drafts,
            brand_base,
            SearchQueryCategory.BRAND_PRODUCT,
            "Brand/product search query from normalized product concepts.",
            _merge_evidence(concepts.brand, concepts.product_type),
            [brand_value, base],
        )
        if core != brand_base:
            core_family = (
                SearchQueryCategory.BRAND_PRODUCT
                if brand_value and brand_value in core.split()
                else SearchQueryCategory.GENERIC_PRODUCT
            )
            _add(
                drafts,
                core,
                core_family,
                "Core named product query suitable for provider lookup.",
                concepts.product_core.evidence_ids,
                [core],
            )

    for generic in concepts.generic_products:
        _add(
            drafts,
            generic.value,
            SearchQueryCategory.GENERIC_PRODUCT,
            "Generic product query derived from product type.",
            generic.evidence_ids,
            [generic.value],
        )

    for feature in concepts.feature_terms:
        query = base if feature.value in base else _join(feature.value, base)
        _add(
            drafts,
            query,
            SearchQueryCategory.FEATURE,
            "Short feature-led search query, not a product-description sentence.",
            _merge_evidence(feature, concepts.product_type),
            [feature.value, base],
        )

    for capacity in concepts.capacity_terms:
        _add(
            drafts,
            _join(capacity.value, base),
            SearchQueryCategory.LOCAL_OR_SIZE_SPECIFIC,
            "Size-specific search query with product type.",
            _merge_evidence(capacity, concepts.product_type),
            [capacity.value, base],
        )

    for use_case in concepts.use_case_terms:
        _add(
            drafts,
            f"{base} for {use_case.value}",
            SearchQueryCategory.USE_CASE,
            "Use-case search query; audience labels stay out of keyword candidates.",
            _merge_evidence(use_case, concepts.product_type),
            [base, use_case.value],
        )
        _add(
            drafts,
            _join(use_case.value, base),
            SearchQueryCategory.USE_CASE,
            "Short use-case modifier search query.",
            _merge_evidence(use_case, concepts.product_type),
            [use_case.value, base],
        )

    for problem in concepts.problem_terms:
        _add(
            drafts,
            _join(problem.value, base),
            SearchQueryCategory.PROBLEM_SOLUTION,
            "Problem/solution query compressed from benefit concepts.",
            _merge_evidence(problem, concepts.product_type),
            [problem.value, base],
        )

    review_base = brand_base or core or base
    _add(
        drafts,
        f"{review_base} review",
        SearchQueryCategory.REVIEW,
        "Review-oriented search query.",
        concepts.product_core.evidence_ids,
        [review_base],
    )
    _add(
        drafts,
        f"{base} reviews",
        SearchQueryCategory.REVIEW,
        "Category review query.",
        concepts.product_type.evidence_ids,
        [base],
    )
    _add(
        drafts,
        f"best {base}",
        SearchQueryCategory.COMPARISON,
        "Comparison search query.",
        concepts.product_type.evidence_ids,
        [base],
    )
    _add(
        drafts,
        f"{review_base} alternatives",
        SearchQueryCategory.COMPARISON,
        "Alternative-comparison search query.",
        concepts.product_core.evidence_ids,
        [review_base],
    )
    _add(
        drafts,
        f"buy {base}",
        SearchQueryCategory.TRANSACTIONAL,
        "Transactional search query.",
        concepts.product_type.evidence_ids,
        [base],
    )
    _add(
        drafts,
        f"{base} price",
        SearchQueryCategory.TRANSACTIONAL,
        "Price-oriented search query with no fabricated CPC or volume.",
        concepts.product_type.evidence_ids,
        [base],
    )
    _add(
        drafts,
        f"{review_base} for sale",
        SearchQueryCategory.TRANSACTIONAL,
        "Commercial availability search query.",
        concepts.product_core.evidence_ids,
        [review_base],
    )
    return drafts


def _candidate_from_draft(
    draft: SearchQueryDraft,
    validation: SearchQueryValidationResult,
    profile: ProductProfile,
) -> KeywordCandidate:
    category = FAMILY_CATEGORY[draft.query_family]
    intent = FAMILY_INTENT[draft.query_family]
    evidence_ids = list(dict.fromkeys(draft.evidence_ids or _fallback_evidence(profile)))
    generation_confidence = round(
        0.45 * validation.product_relevance_score
        + 0.35 * validation.query_realism_score
        + 0.2 * validation.specificity_score,
        4,
    )
    candidate = KeywordCandidate(
        text=validation.normalized_query,
        normalized_text=validation.normalized_query,
        marketing_term_type=MarketingTermType.SEARCH_QUERY,
        query_family=draft.query_family,
        intent=intent,
        category=category,
        rationale=draft.rationale,
        source="generated_from_search_concepts",
        evidence_ids=evidence_ids,
        relevance_score=0.0,
        confidence_score=0.0,
        generation_confidence=generation_confidence,
        product_relevance_score=validation.product_relevance_score,
        query_realism_score=validation.query_realism_score,
        specificity_score=validation.specificity_score,
        commercial_intent_score=validation.commercial_intent_score,
        source_concepts=list(dict.fromkeys(draft.source_concepts)),
        origin="deterministic_search_query_generator",
        rejection_reasons=validation.rejection_reasons,
        eligible_for_live_enrichment=validation.eligible_for_live_enrichment,
        generator_version=GENERATOR_VERSION,
        score_components=ScoreComponents(
            product_match=0.0,
            intent_value=0.0,
            evidence_strength=0.0,
            audience_fit=0.0,
            specificity=0.0,
            risk_penalty=0.0,
        ),
        risk_flags=[],
    )
    return rescore_candidate(candidate, profile)


def _term_from_linked(item: EvidenceLinkedText) -> TermConcept:
    return TermConcept(value=_clean_phrase(item.value), evidence_ids=item.evidence_ids)


def _clean_phrase(value: str) -> str:
    text = re.sub(r"['\"].*?['\"]", " ", value)
    text = normalize_keyword(text)
    text = text.replace("square feet", "sq ft").replace("sq. ft", "sq ft")
    text = re.sub(r"\bu\s+shaped?\b", "u shaped", text)
    text = re.sub(r"\bretro\b.*$", " ", text) if AIR_JORDAN_RE.search(text) else text
    text = re.sub(r"\b(university blue|midnight navy|limited edition|special edition)\b", " ", text)
    return SPACE_RE.sub(" ", text).strip()


def _product_type(value: str, brand: str | None) -> str:
    clean = _without_brand(value, brand)
    jordan_match = AIR_JORDAN_RE.search(clean)
    if jordan_match:
        return jordan_match.group(0).lower()
    if "xbox" in clean and "controller" in clean:
        return "xbox controller"
    for pattern in PRODUCT_TYPE_PATTERNS:
        if pattern in clean:
            return pattern
    tokens = _meaningful_tokens(clean)
    if len(tokens) <= 3:
        return " ".join(tokens) or clean
    return " ".join(tokens[-3:])


def _without_brand(value: str, brand: str | None) -> str:
    clean = _clean_phrase(value)
    if not brand:
        return clean
    brand_tokens = brand.split()
    tokens = clean.split()
    if tokens[: len(brand_tokens)] == brand_tokens:
        tokens = tokens[len(brand_tokens) :]
    return " ".join(tokens) or clean


def _feature_concepts(
    profile: ProductProfile, product_type: str, product_core: str, fallback_evidence: list[str]
) -> list[TermConcept]:
    concepts: list[TermConcept] = []
    product_type_terms = set(product_type.split())
    for value in (product_core,):
        descriptor = _descriptor_from_text(value, product_type_terms)
        if descriptor:
            concepts.append(TermConcept(value=descriptor, evidence_ids=fallback_evidence))
    for item in [
        *profile.features,
        *profile.materials,
        *profile.colors,
        *profile.differentiators,
    ]:
        concepts.extend(_concepts_from_text(item.value, item.evidence_ids, product_type_terms))
    return _dedupe_concepts(concepts)


def _capacity_concepts(profile: ProductProfile, fallback_evidence: list[str]) -> list[TermConcept]:
    concepts: list[TermConcept] = []
    for item in _all_linked_text(profile):
        for match in CAPACITY_RE.findall(item.value):
            concepts.append(
                TermConcept(
                    value=_clean_phrase(match.replace(",", "")), evidence_ids=item.evidence_ids
                )
            )
    if not concepts and profile.product_name:
        for match in CAPACITY_RE.findall(profile.product_name.value):
            concepts.append(TermConcept(value=_clean_phrase(match), evidence_ids=fallback_evidence))
    return _dedupe_concepts(concepts)


def _use_case_concepts(profile: ProductProfile) -> list[TermConcept]:
    concepts: list[TermConcept] = []
    for item in profile.use_cases:
        shortened = _short_concept(item.value)
        if shortened and not _looks_like_audience(shortened):
            concepts.append(TermConcept(value=shortened, evidence_ids=item.evidence_ids))
    return _dedupe_concepts(concepts)


def _problem_concepts(profile: ProductProfile, product_type: str) -> list[TermConcept]:
    concepts: list[TermConcept] = []
    product_type_terms = set(product_type.split())
    for item in profile.benefits:
        lowered = _clean_phrase(item.value)
        if "without" in lowered:
            concepts.append(
                TermConcept(
                    value=_short_concept(lowered.split("without", maxsplit=1)[1]),
                    evidence_ids=item.evidence_ids,
                )
            )
            continue
        descriptor = _descriptor_from_text(lowered, product_type_terms)
        if descriptor:
            concepts.append(TermConcept(value=descriptor, evidence_ids=item.evidence_ids))
    return _dedupe_concepts([concept for concept in concepts if concept.value])


def _concepts_from_text(
    value: str, evidence_ids: list[str], product_type_terms: set[str]
) -> list[TermConcept]:
    concepts: list[TermConcept] = []
    clean = _clean_phrase(value)
    for phrase in FEATURE_PHRASES:
        if phrase in clean and phrase not in product_type_terms:
            concepts.append(TermConcept(value=phrase, evidence_ids=evidence_ids))
    descriptor = _descriptor_from_text(clean, product_type_terms)
    if descriptor:
        concepts.append(TermConcept(value=descriptor, evidence_ids=evidence_ids))
    return concepts


def _descriptor_from_text(value: str, product_type_terms: set[str]) -> str | None:
    clean = _clean_phrase(value)
    tokens = [
        token
        for token in clean.split()
        if token not in DESCRIPTOR_STOP_WORDS
        and token not in product_type_terms
        and len(token) > 1
        and not token.isdigit()
    ]
    if not tokens:
        return None
    descriptors = [token for token in tokens if token in set(" ".join(FEATURE_PHRASES).split())]
    selected = descriptors[:2] if descriptors else tokens[:2]
    if not selected:
        return None
    return " ".join(selected)


def _short_concept(value: str) -> str:
    tokens = [
        token
        for token in _clean_phrase(value).split()
        if token not in DESCRIPTOR_STOP_WORDS and len(token) > 1
    ]
    return " ".join(tokens[:3])


def _meaningful_tokens(value: str) -> list[str]:
    return [
        token
        for token in _clean_phrase(value).split()
        if token not in DESCRIPTOR_STOP_WORDS and len(token) > 1
    ]


def _all_linked_text(profile: ProductProfile) -> list[EvidenceLinkedText]:
    values: list[EvidenceLinkedText] = []
    for field in (
        profile.product_name,
        profile.brand,
        profile.category,
        profile.subcategory,
        profile.marketplace_search_query,
    ):
        if field:
            values.append(field)
    values.append(profile.summary)
    for collection in (
        profile.features,
        profile.benefits,
        profile.materials,
        profile.colors,
        profile.use_cases,
        profile.differentiators,
        profile.user_provided_facts,
        profile.inferred_attributes,
    ):
        values.extend(collection)
    return values


def _looks_like_audience(value: str) -> bool:
    return bool(set(value.split()).intersection(AUDIENCE_MARKERS))


def _dedupe_concepts(concepts: list[TermConcept]) -> list[TermConcept]:
    selected: dict[str, TermConcept] = {}
    for concept in concepts:
        value = _clean_phrase(concept.value)
        if not value:
            continue
        if len(value.split()) > 6:
            value = " ".join(value.split()[:6])
        if value not in selected:
            selected[value] = TermConcept(
                value=value,
                evidence_ids=list(dict.fromkeys(concept.evidence_ids)),
            )
    return list(selected.values())


def _add(
    drafts: list[SearchQueryDraft],
    text: str | None,
    query_family: SearchQueryCategory,
    rationale: str,
    evidence_ids: list[str],
    source_concepts: list[str],
) -> None:
    if not text:
        return
    cleaned = _clean_phrase(text)
    if cleaned:
        drafts.append(
            SearchQueryDraft(
                text=cleaned,
                query_family=query_family,
                rationale=rationale,
                evidence_ids=list(dict.fromkeys(evidence_ids)),
                source_concepts=[concept for concept in source_concepts if concept],
            )
        )


def _merge_evidence(*concepts: TermConcept | None) -> list[str]:
    evidence_ids: list[str] = []
    for concept in concepts:
        if concept:
            evidence_ids.extend(concept.evidence_ids)
    return list(dict.fromkeys(evidence_ids))


def _fallback_evidence(profile: ProductProfile) -> list[str]:
    if profile.product_name:
        return profile.product_name.evidence_ids
    return profile.summary.evidence_ids


def _join(*parts: str | None) -> str:
    return " ".join(part for part in parts if part)
