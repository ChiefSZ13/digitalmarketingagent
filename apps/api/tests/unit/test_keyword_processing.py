from marketing_agent.domain.models.evidence import (
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.keyword import (
    KeywordCategory,
    KeywordMonthlyMetric,
    KeywordTrendDirection,
    MarketingTermType,
    SearchQueryCategory,
    SearchQueryRejectionReason,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.keyword_clusterer import cluster_keywords
from marketing_agent.domain.services.keyword_enrichment import (
    KeywordEnrichmentConfig,
    build_keyword_cache_key,
    calculate_trend,
    enrich_keyword_candidates,
)
from marketing_agent.domain.services.keyword_generator import generate_keyword_candidates
from marketing_agent.domain.services.keyword_normalizer import (
    are_near_duplicates,
    deduplicate_keywords,
    normalize_keyword,
)
from marketing_agent.domain.services.search_query_validator import SearchQueryValidator
from marketing_agent.infrastructure.keyword_data.in_memory_keyword_metrics_cache import (
    InMemoryKeywordMetricsCache,
)
from marketing_agent.infrastructure.keyword_data.mock_keyword_metrics_provider import (
    MockKeywordMetricsProvider,
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
    assert all(item.marketing_term_type == MarketingTermType.SEARCH_QUERY for item in deduped)
    assert all(item.eligible_for_live_enrichment for item in deduped)
    assert all(item.query_realism_score >= 0.7 for item in deduped)
    assert all(2 <= len(item.normalized_text.split()) <= 10 for item in deduped)
    assert {
        KeywordCategory.BENEFIT,
        KeywordCategory.AUDIENCE,
        KeywordCategory.NEGATIVE,
        KeywordCategory.CONTENT_ANGLE,
    }.isdisjoint({item.category for item in deduped})


def test_generator_separates_search_queries_from_audience_descriptions() -> None:
    generated = generate_keyword_candidates(_profile())
    texts = {candidate.normalized_text for candidate in generated}
    families = {candidate.query_family for candidate in generated}

    assert "rechargeable desk lamp" in texts
    assert "lighting for remote workers" not in texts
    assert SearchQueryCategory.FEATURE in families
    assert SearchQueryCategory.TRANSACTIONAL in families


def test_search_query_validator_rejects_description_copy_and_sentence_phrases() -> None:
    validator = SearchQueryValidator(_air_conditioner_profile())

    copied = validator.validate(
        "midea 12000 btu u shaped smart inverter window air conditioner",
        ["midea", "12000 btu", "u shaped", "window air conditioner"],
    )
    sentence = validator.validate(
        "this product features a u shaped design that allows the window to open",
        ["u shaped", "window air conditioner"],
    )

    assert SearchQueryRejectionReason.DESCRIPTION_COPY in copied.rejection_reasons
    assert SearchQueryRejectionReason.ATTRIBUTE_DENSE in copied.rejection_reasons
    assert not copied.eligible_for_live_enrichment
    assert SearchQueryRejectionReason.BANNED_PHRASE in sentence.rejection_reasons
    assert SearchQueryRejectionReason.TOO_LONG in sentence.rejection_reasons
    assert not sentence.eligible_for_live_enrichment


def test_realistic_queries_for_common_product_types() -> None:
    cases = [
        (
            _air_conditioner_profile(),
            {"midea window air conditioner", "u shaped window air conditioner"},
        ),
        (
            _profile(
                product_name="Xbox Wireless Controller",
                brand="Microsoft",
                category="Game controller",
                features=["wireless", "ergonomic grip"],
                use_cases=["console gaming"],
            ),
            {"microsoft xbox controller", "wireless xbox controller"},
        ),
        (
            _profile(
                product_name="Programmable Coffee Maker",
                category="Coffee maker",
                features=["programmable timer", "thermal carafe"],
                use_cases=["morning coffee"],
            ),
            {"programmable coffee maker", "coffee maker price"},
        ),
        (
            _profile(
                product_name="Lightweight Cushioned Running Shoes",
                brand="Nike",
                category="Running shoes",
                features=["lightweight", "cushioned sole"],
                use_cases=["daily running"],
            ),
            {"nike running shoes", "lightweight running shoes"},
        ),
    ]

    for profile, expected_terms in cases:
        generated = {
            candidate.normalized_text for candidate in generate_keyword_candidates(profile)
        }
        assert expected_terms.intersection(generated), generated


def test_keyword_trend_uses_recent_three_months_against_previous_three() -> None:
    direction, strength, explanation = calculate_trend(
        [
            KeywordMonthlyMetric(year=2026, month=1, searches=100),
            KeywordMonthlyMetric(year=2026, month=2, searches=110),
            KeywordMonthlyMetric(year=2026, month=3, searches=120),
            KeywordMonthlyMetric(year=2026, month=4, searches=180),
            KeywordMonthlyMetric(year=2026, month=5, searches=190),
            KeywordMonthlyMetric(year=2026, month=6, searches=200),
        ]
    )

    assert direction == KeywordTrendDirection.RISING
    assert strength is not None and strength > 0
    assert "three-month" in explanation


def test_keyword_cache_key_includes_market_language_and_provider() -> None:
    base = _enrichment_config(provider="mock", market="US", language="en")
    same_keyword_other_market = _enrichment_config(provider="mock", market="GB", language="en")

    assert build_keyword_cache_key("desk lamp", base) != build_keyword_cache_key(
        "desk lamp", same_keyword_other_market
    )
    assert build_keyword_cache_key("Desk Lamp", base) == build_keyword_cache_key("desk lamp", base)


async def test_mock_keyword_enrichment_adds_metrics_without_fabricating_missing_values() -> None:
    profile = _profile()
    generated = deduplicate_keywords(generate_keyword_candidates(profile))
    result = await enrich_keyword_candidates(
        profile=profile,
        candidates=generated,
        provider=MockKeywordMetricsProvider(scenario="missing"),
        cache=InMemoryKeywordMetricsCache(),
        config=_enrichment_config(),
    )

    assert result.intelligence.status in {"complete", "partial_success"}
    assert result.intelligence.keywords
    enriched = [keyword for keyword in result.candidates if keyword.enrichment.provider]
    assert enriched
    assert all(keyword.enrichment.cpc_low is None for keyword in enriched)
    assert all(keyword.opportunity_score is not None for keyword in enriched)
    assert any(keyword.source == "keyword_provider_related_terms" for keyword in result.candidates)


def _enrichment_config(
    *,
    provider: str = "mock",
    market: str = "US",
    language: str = "en",
) -> KeywordEnrichmentConfig:
    return KeywordEnrichmentConfig(
        provider=provider,
        market=market,
        language=language,
        currency="USD",
        max_keywords=20,
        batch_size=10,
        cache_ttl_seconds=3600,
        scoring_policy_version="keyword-opportunity-v1",
        matching_policy_version="keyword-provider-match-v1",
        trend_policy_version="keyword-trend-v1",
    )


def _profile(
    *,
    product_name: str = "Portable Desk Lamp",
    brand: str | None = None,
    category: str = "Lighting",
    features: list[str] | None = None,
    use_cases: list[str] | None = None,
    benefits: list[str] | None = None,
) -> ProductProfile:
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
    feature_values = features or ["rechargeable"]
    use_case_values = use_cases or ["desk setup"]
    benefit_values = benefits or ["supports cordless use"]
    return ProductProfile(
        product_name=EvidenceLinkedText(value=product_name, evidence_ids=linked, confidence=0.8),
        brand=(
            EvidenceLinkedText(value=brand, evidence_ids=linked, confidence=0.9) if brand else None
        ),
        category=EvidenceLinkedText(
            value=category, evidence_ids=["ev-inference-1"], confidence=0.7
        ),
        subcategory=None,
        summary=EvidenceLinkedText(
            value=f"{product_name} for {use_case_values[0]}",
            evidence_ids=linked,
            confidence=0.8,
        ),
        features=[
            EvidenceLinkedText(value=value, evidence_ids=linked, confidence=0.8)
            for value in feature_values
        ],
        benefits=[
            EvidenceLinkedText(value=value, evidence_ids=linked, confidence=0.7)
            for value in benefit_values
        ],
        use_cases=[
            EvidenceLinkedText(value=value, evidence_ids=linked, confidence=0.7)
            for value in use_case_values
        ],
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


def _air_conditioner_profile() -> ProductProfile:
    return _profile(
        product_name="Midea 12000 BTU U Shaped Smart Inverter Window Air Conditioner",
        brand="Midea",
        category="Window air conditioner",
        features=["u shaped design", "smart inverter", "quiet operation"],
        use_cases=["bedroom cooling"],
        benefits=[
            (
                "Midea 12000 BTU U Shaped Smart Inverter Window Air Conditioner "
                "keeps rooms cool while allowing the window to open."
            )
        ],
    )
