from marketing_agent.domain.models.evidence import (
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.keyword_clusterer import cluster_keywords
from marketing_agent.domain.services.keyword_generator import generate_keyword_candidates
from marketing_agent.domain.services.keyword_normalizer import (
    are_near_duplicates,
    deduplicate_keywords,
    normalize_keyword,
)


def test_normalize_keyword_preserves_model_numbers() -> None:
    assert normalize_keyword("  Lamp—Model X-12!! ") == "lamp-model x-12"


def test_near_duplicate_detection() -> None:
    assert are_near_duplicates("Portable Desk Lamp", "portable desk-lamp")


def test_generation_dedup_scoring_and_clustering() -> None:
    profile = _profile()
    generated = generate_keyword_candidates(profile)
    deduped = deduplicate_keywords(generated + generated[:2])
    clusters = cluster_keywords(deduped)
    assert len(deduped) < len(generated) + 2
    assert all(0.0 <= item.relevance_score <= 1.0 for item in deduped)
    assert all(item.enrichment.average_monthly_searches is None for item in deduped)
    assert clusters
    assert all(cluster.member_keywords for cluster in clusters)


def _profile() -> ProductProfile:
    evidence = [
        EvidenceRecord(
            id="ev-description-1",
            source=EvidenceSource.USER_DESCRIPTION,
            source_reference="description",
            observation="User description",
            confidence=0.9,
        ),
        EvidenceRecord(
            id="ev-inference-1",
            source=EvidenceSource.MODEL_INFERENCE,
            source_reference="mock",
            observation="Safe inference",
            confidence=0.7,
        ),
    ]
    linked = ["ev-description-1"]
    return ProductProfile(
        product_name=EvidenceLinkedText(
            value="Portable Desk Lamp", evidence_ids=linked, confidence=0.8
        ),
        brand=None,
        category=EvidenceLinkedText(
            value="Lighting", evidence_ids=["ev-inference-1"], confidence=0.7
        ),
        subcategory=None,
        summary=EvidenceLinkedText(
            value="Portable desk lamp for desk setup", evidence_ids=linked, confidence=0.8
        ),
        features=[EvidenceLinkedText(value="rechargeable", evidence_ids=linked, confidence=0.8)],
        benefits=[
            EvidenceLinkedText(value="supports cordless use", evidence_ids=linked, confidence=0.7)
        ],
        use_cases=[EvidenceLinkedText(value="desk setup", evidence_ids=linked, confidence=0.7)],
        target_audiences=[
            EvidenceLinkedText(
                value="remote workers", evidence_ids=["ev-inference-1"], confidence=0.7
            )
        ],
        limitations=[],
        ambiguities=[],
        unknowns=[
            EvidenceLinkedText(
                value="exact dimensions unknown", evidence_ids=["ev-inference-1"], confidence=1.0
            )
        ],
        evidence=evidence,
        overall_confidence=0.76,
    )
