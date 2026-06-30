"""Mock-backed keyword enrichment evaluation smoke script."""

from __future__ import annotations

import asyncio
import time

from marketing_agent.domain.models.evidence import (
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.keyword_enrichment import (
    KeywordEnrichmentConfig,
    enrich_keyword_candidates,
)
from marketing_agent.domain.services.keyword_generator import generate_keyword_candidates
from marketing_agent.domain.services.keyword_normalizer import deduplicate_keywords
from marketing_agent.infrastructure.keyword_data.in_memory_keyword_metrics_cache import (
    InMemoryKeywordMetricsCache,
)
from marketing_agent.infrastructure.keyword_data.mock_keyword_metrics_provider import (
    MockKeywordMetricsProvider,
)


async def main() -> None:
    cache = InMemoryKeywordMetricsCache()
    provider = MockKeywordMetricsProvider()
    profile = _profile()
    candidates = deduplicate_keywords(generate_keyword_candidates(profile))
    config = KeywordEnrichmentConfig(
        provider="mock",
        market="US",
        language="en",
        currency="USD",
        max_keywords=20,
        batch_size=10,
        cache_ttl_seconds=3600,
        scoring_policy_version="keyword-opportunity-v1",
        matching_policy_version="keyword-provider-match-v1",
        trend_policy_version="keyword-trend-v1",
    )

    start = time.perf_counter()
    first = await enrich_keyword_candidates(
        profile=profile,
        candidates=candidates,
        provider=provider,
        cache=cache,
        config=config,
    )
    second = await enrich_keyword_candidates(
        profile=profile,
        candidates=candidates,
        provider=provider,
        cache=cache,
        config=config,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    enriched_count = sum(1 for item in first.candidates if item.enrichment.provider)
    opportunity_values = [
        item.opportunity_score for item in first.candidates if item.opportunity_score is not None
    ]
    if not enriched_count or not opportunity_values:
        raise SystemExit("FAIL: enrichment did not produce metrics and opportunity scores.")
    cache_hits = sum(1 for item in second.telemetry if item.cache_status == "hit")
    print(
        "keyword_enrichment_eval "
        f"candidates={len(candidates)} enriched={enriched_count} "
        f"opportunity_scores={len(opportunity_values)} cache_hits={cache_hits} "
        f"latency_ms={latency_ms}"
    )


def _profile() -> ProductProfile:
    evidence = [
        EvidenceRecord(
            id="ev-eval-1",
            source=EvidenceSource.USER_DESCRIPTION,
            source_reference="eval",
            observation="Evaluation description.",
            confidence=0.9,
        )
    ]
    linked = EvidenceLinkedText(
        value="Portable rechargeable desk lamp",
        evidence_ids=["ev-eval-1"],
        confidence=0.9,
    )
    return ProductProfile(
        product_name=linked,
        category=EvidenceLinkedText(
            value="Desk lamp",
            evidence_ids=["ev-eval-1"],
            confidence=0.9,
        ),
        marketplace_search_query=linked,
        summary=linked,
        features=[
            EvidenceLinkedText(
                value="rechargeable",
                evidence_ids=["ev-eval-1"],
                confidence=0.8,
            )
        ],
        use_cases=[
            EvidenceLinkedText(
                value="desk setup",
                evidence_ids=["ev-eval-1"],
                confidence=0.8,
            )
        ],
        target_audiences=[
            EvidenceLinkedText(
                value="remote workers",
                evidence_ids=["ev-eval-1"],
                confidence=0.8,
            )
        ],
        evidence=evidence,
        overall_confidence=0.9,
    )


if __name__ == "__main__":
    asyncio.run(main())
