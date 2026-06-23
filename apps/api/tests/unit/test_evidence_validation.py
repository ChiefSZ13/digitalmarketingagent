import pytest

from marketing_agent.domain.models.evidence import (
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.evidence_validator import (
    EvidenceCoverageError,
    validate_profile_evidence,
)


def test_profile_requires_valid_evidence_ids() -> None:
    profile = ProductProfile(
        product_name=EvidenceLinkedText(value="Lamp", evidence_ids=["missing"], confidence=0.8),
        summary=EvidenceLinkedText(value="Lamp summary", evidence_ids=["ev-1"], confidence=0.8),
        evidence=[
            EvidenceRecord(
                id="ev-1",
                source=EvidenceSource.USER_DESCRIPTION,
                source_reference="description",
                observation="Description",
                confidence=0.9,
            )
        ],
        overall_confidence=0.7,
    )
    with pytest.raises(EvidenceCoverageError):
        validate_profile_evidence(profile)
