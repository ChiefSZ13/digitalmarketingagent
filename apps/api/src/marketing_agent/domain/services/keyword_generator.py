"""Generate initial keyword candidates from a validated product profile."""

from dataclasses import dataclass

from marketing_agent.domain.models.evidence import EvidenceLinkedText
from marketing_agent.domain.models.keyword import KeywordCandidate, KeywordCategory, ScoreComponents
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.keyword_classifier import classify_intent
from marketing_agent.domain.services.keyword_normalizer import normalize_keyword
from marketing_agent.domain.services.keyword_scorer import rescore_candidate


@dataclass(frozen=True)
class KeywordDraft:
    text: str
    category: KeywordCategory
    rationale: str
    evidence_ids: list[str]
    risk_flags: list[str] | None = None


def _value(item: EvidenceLinkedText | None, fallback: str) -> str:
    return item.value if item else fallback


def _first(
    collection: list[EvidenceLinkedText], fallback: EvidenceLinkedText | None
) -> EvidenceLinkedText | None:
    return collection[0] if collection else fallback


def generate_keyword_candidates(profile: ProductProfile) -> list[KeywordCandidate]:
    """Generate a broad keyword set without search-volume or CPC claims."""
    product = _value(profile.product_name, "product")
    category = _value(profile.category, "product")
    feature = _first(profile.features, profile.product_name)
    benefit = _first(profile.benefits, profile.summary)
    use_case = _first(profile.use_cases, profile.summary)
    audience = _first(profile.target_audiences, profile.summary)

    base_evidence = profile.summary.evidence_ids
    product_evidence = profile.product_name.evidence_ids if profile.product_name else base_evidence
    category_evidence = profile.category.evidence_ids if profile.category else base_evidence

    drafts = [
        KeywordDraft(
            product,
            KeywordCategory.PRODUCT,
            "Core product name from the profile.",
            product_evidence,
        ),
        KeywordDraft(
            category, KeywordCategory.PRODUCT, "Category-level seed term.", category_evidence
        ),
        KeywordDraft(
            f"{product} for sale",
            KeywordCategory.PRODUCT,
            "Commercial phrase for later campaign planning.",
            product_evidence,
        ),
        KeywordDraft(
            f"buy {product}",
            KeywordCategory.LONG_TAIL,
            "Transactional long-tail phrase without provider metrics.",
            product_evidence,
        ),
        KeywordDraft(
            f"best {category}",
            KeywordCategory.ALTERNATIVE,
            "Comparison-style discovery phrase.",
            category_evidence,
        ),
        KeywordDraft(
            f"{product} alternatives",
            KeywordCategory.ALTERNATIVE,
            "Comparison phrase for alternative research.",
            product_evidence,
        ),
        KeywordDraft(
            f"{product} review",
            KeywordCategory.CONTENT_ANGLE,
            "Content angle for review-oriented pages.",
            product_evidence,
        ),
        KeywordDraft(
            f"how to choose {category}",
            KeywordCategory.CONTENT_ANGLE,
            "Informational content angle derived from category.",
            category_evidence,
        ),
        KeywordDraft(
            f"cheap {product}",
            KeywordCategory.NEGATIVE,
            "Negative keyword candidate to avoid low-intent bargain traffic.",
            product_evidence,
            ["price_positioning"],
        ),
        KeywordDraft(
            f"free {product}",
            KeywordCategory.NEGATIVE,
            "Negative keyword candidate to avoid unsupported free-offer traffic.",
            product_evidence,
            ["unsupported_offer"],
        ),
    ]

    if feature:
        drafts.extend(
            [
                KeywordDraft(
                    f"{feature.value} {category}",
                    KeywordCategory.FEATURE,
                    "Feature phrase grounded in profile evidence.",
                    feature.evidence_ids,
                ),
                KeywordDraft(
                    f"{product} with {feature.value}",
                    KeywordCategory.LONG_TAIL,
                    "Long-tail phrase combining product and feature.",
                    list(dict.fromkeys(product_evidence + feature.evidence_ids)),
                ),
            ]
        )
    if benefit:
        drafts.append(
            KeywordDraft(
                f"{benefit.value} {category}",
                KeywordCategory.BENEFIT,
                "Benefit-led phrase grounded in the normalized profile.",
                benefit.evidence_ids,
            )
        )
    if use_case:
        drafts.append(
            KeywordDraft(
                f"{product} for {use_case.value}",
                KeywordCategory.USE_CASE,
                "Use-case phrase tied to product evidence.",
                list(dict.fromkeys(product_evidence + use_case.evidence_ids)),
            )
        )
    if audience:
        drafts.append(
            KeywordDraft(
                f"{category} for {audience.value}",
                KeywordCategory.AUDIENCE,
                "Audience phrase from provided or inferred target audience.",
                list(dict.fromkeys(category_evidence + audience.evidence_ids)),
            )
        )

    candidates: list[KeywordCandidate] = []
    for draft in drafts:
        normalized = normalize_keyword(draft.text)
        intent = classify_intent(draft.text, draft.category)
        candidate = KeywordCandidate(
            text=draft.text,
            normalized_text=normalized,
            intent=intent,
            category=draft.category,
            rationale=draft.rationale,
            source="generated_from_product_profile",
            evidence_ids=list(dict.fromkeys(draft.evidence_ids or base_evidence)),
            relevance_score=0.0,
            confidence_score=0.0,
            score_components=ScoreComponents(
                product_match=0.0,
                intent_value=0.0,
                evidence_strength=0.0,
                audience_fit=0.0,
                specificity=0.0,
                risk_penalty=0.0,
            ),
            risk_flags=draft.risk_flags or [],
        )
        candidates.append(rescore_candidate(candidate, profile))
    return candidates
