"""Transparent keyword scoring."""

from marketing_agent.domain.models.keyword import KeywordCandidate, KeywordIntent, ScoreComponents
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.keyword_normalizer import normalize_keyword

INTENT_VALUE: dict[KeywordIntent, float] = {
    KeywordIntent.TRANSACTIONAL: 0.95,
    KeywordIntent.COMMERCIAL: 0.85,
    KeywordIntent.COMPARISON: 0.7,
    KeywordIntent.INFORMATIONAL: 0.6,
    KeywordIntent.NAVIGATIONAL: 0.45,
    KeywordIntent.UNKNOWN: 0.35,
}


def _profile_terms(profile: ProductProfile) -> set[str]:
    fields = [
        profile.product_name.value if profile.product_name else "",
        profile.brand.value if profile.brand else "",
        profile.category.value if profile.category else "",
        profile.subcategory.value if profile.subcategory else "",
    ]
    for collection in (
        profile.features,
        profile.benefits,
        profile.use_cases,
        profile.target_audiences,
    ):
        fields.extend(item.value for item in collection)
    terms: set[str] = set()
    for field in fields:
        terms.update(normalize_keyword(field).split())
    return {term for term in terms if len(term) > 2}


def build_score_components(
    candidate_text: str,
    intent: KeywordIntent,
    evidence_strength: float,
    audience_fit: float,
    risk_flags: list[str],
    profile: ProductProfile,
) -> ScoreComponents:
    keyword_terms = set(normalize_keyword(candidate_text).split())
    profile_terms = _profile_terms(profile)
    overlap = keyword_terms.intersection(profile_terms)
    product_match = min(1.0, len(overlap) / max(1, min(4, len(keyword_terms))))
    specificity = min(1.0, max(0.2, len(keyword_terms) / 6))
    risk_penalty = min(0.5, 0.12 * len(risk_flags))
    return ScoreComponents(
        product_match=round(product_match, 4),
        intent_value=INTENT_VALUE[intent],
        evidence_strength=round(evidence_strength, 4),
        audience_fit=round(audience_fit, 4),
        specificity=round(specificity, 4),
        risk_penalty=round(risk_penalty, 4),
    )


def rescore_candidate(candidate: KeywordCandidate, profile: ProductProfile) -> KeywordCandidate:
    evidence_by_id = {record.id: record for record in profile.evidence}
    strengths = [
        evidence_by_id[evidence_id].confidence
        for evidence_id in candidate.evidence_ids
        if evidence_id in evidence_by_id
    ]
    evidence_strength = sum(strengths) / len(strengths) if strengths else 0.4
    audience_terms = [normalize_keyword(item.value) for item in profile.target_audiences]
    audience_fit = (
        0.75 if any(term in candidate.normalized_text for term in audience_terms) else 0.55
    )
    components = build_score_components(
        candidate.text,
        candidate.intent,
        evidence_strength,
        audience_fit,
        candidate.risk_flags,
        profile,
    )
    confidence = round(
        max(0.0, min(1.0, 0.65 * evidence_strength + 0.35 * components.product_match)), 4
    )
    return candidate.model_copy(
        update={
            "score_components": components,
            "relevance_score": components.relevance(),
            "confidence_score": confidence,
        }
    )
