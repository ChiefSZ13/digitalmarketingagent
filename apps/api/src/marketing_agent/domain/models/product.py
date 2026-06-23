"""Validated product profile returned by perception providers."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from marketing_agent.domain.models.evidence import (
    ClaimFlag,
    EvidenceLinkedText,
    EvidenceRecord,
)


def _linked_text_list() -> list[EvidenceLinkedText]:
    return []


def _claim_flag_list() -> list[ClaimFlag]:
    return []


class ProductProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_name: EvidenceLinkedText | None = None
    brand: EvidenceLinkedText | None = None
    category: EvidenceLinkedText | None = None
    subcategory: EvidenceLinkedText | None = None
    summary: EvidenceLinkedText
    visual_attributes: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    observed_facts: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    user_provided_facts: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    inferred_attributes: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    features: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    benefits: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    materials: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    colors: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    use_cases: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    target_audiences: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    differentiators: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    limitations: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    ambiguities: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    unknowns: list[EvidenceLinkedText] = Field(default_factory=_linked_text_list)
    unsafe_or_unverified_claims: list[ClaimFlag] = Field(default_factory=_claim_flag_list)
    claim_flags: list[ClaimFlag] = Field(default_factory=_claim_flag_list)
    evidence: list[EvidenceRecord] = Field(min_length=1)
    overall_confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("claim_flags", mode="after")
    @classmethod
    def mirror_claim_flags(cls, flags: list[ClaimFlag]) -> list[ClaimFlag]:
        return flags
