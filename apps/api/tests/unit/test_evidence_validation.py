import pytest

from marketing_agent.domain.models.evidence import (
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.marketplace import (
    MarketplacePlatformEstimate,
    MarketplacePriceEstimate,
    MarketplaceSnapshot,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.evidence_validator import (
    EvidenceCoverageError,
    validate_marketplace_evidence,
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


def test_marketplace_snapshot_requires_valid_evidence_ids() -> None:
    profile = ProductProfile(
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
    snapshot = MarketplaceSnapshot(
        title="Marketplace Snapshot",
        summary="Estimated marketplace fit.",
        source_provider="mock",
        source_query="lamp US",
        is_live_data=False,
        methodology="Model estimate only.",
        limitations=["No live data."],
        platform_rankings=[
            MarketplacePlatformEstimate(
                rank=1,
                platform="Amazon",
                platform_type="marketplace",
                data_source="mock_marketplace_provider",
                estimated_sales_potential_score=0.8,
                observed_offer_count=1,
                observed_review_count=10,
                observed_units_sold=None,
                observed_sales_signal=None,
                sales_rank_basis="Model estimate.",
                listing_search_phrase="lamp Amazon",
                source_url=None,
                evidence_ids=["missing"],
                confidence=0.4,
                risk_flags=["unverified_sales_rank"],
            )
        ],
        price_estimates=[
            MarketplacePriceEstimate(
                platform="Amazon",
                data_source="mock_marketplace_provider",
                price_low=10,
                price_high=20,
                currency="USD",
                observed_offer_count=1,
                price_basis="Model estimate.",
                listing_search_phrase="lamp Amazon",
                source_url=None,
                evidence_ids=["ev-1"],
                confidence=0.4,
                risk_flags=["unverified_price"],
            )
        ],
        warnings=["Use for validation planning only."],
        overall_confidence=0.4,
    )
    with pytest.raises(EvidenceCoverageError):
        validate_marketplace_evidence(profile, snapshot)
