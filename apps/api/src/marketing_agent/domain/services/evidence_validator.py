"""Evidence coverage checks for product profiles and keywords."""

from marketing_agent.domain.models.evidence import ClaimFlag, EvidenceLinkedText
from marketing_agent.domain.models.keyword import KeywordCandidate
from marketing_agent.domain.models.product import ProductProfile


class EvidenceCoverageError(ValueError):
    """Raised when material assertions do not point to valid evidence."""


def validate_profile_evidence(profile: ProductProfile) -> None:
    evidence_ids = {record.id for record in profile.evidence}
    linked_items: list[EvidenceLinkedText] = []
    for field_name in (
        "product_name",
        "brand",
        "category",
        "subcategory",
        "summary",
    ):
        value = getattr(profile, field_name)
        if value is not None:
            linked_items.append(value)
    for field_name in (
        "visual_attributes",
        "observed_facts",
        "user_provided_facts",
        "inferred_attributes",
        "features",
        "benefits",
        "materials",
        "colors",
        "use_cases",
        "target_audiences",
        "differentiators",
        "limitations",
        "ambiguities",
        "unknowns",
    ):
        linked_items.extend(getattr(profile, field_name))
    for item in linked_items:
        missing = set(item.evidence_ids).difference(evidence_ids)
        if missing:
            raise EvidenceCoverageError(
                f"field '{item.value}' references missing evidence: {missing}"
            )

    flags: list[ClaimFlag] = profile.unsafe_or_unverified_claims + profile.claim_flags
    for flag in flags:
        missing = set(flag.evidence_ids).difference(evidence_ids)
        if missing:
            raise EvidenceCoverageError(
                f"claim flag '{flag.claim}' references missing evidence: {missing}"
            )


def validate_keyword_evidence(profile: ProductProfile, candidates: list[KeywordCandidate]) -> None:
    evidence_ids = {record.id for record in profile.evidence}
    for candidate in candidates:
        missing = set(candidate.evidence_ids).difference(evidence_ids)
        if missing:
            raise EvidenceCoverageError(
                f"keyword '{candidate.text}' references missing evidence: {missing}"
            )
