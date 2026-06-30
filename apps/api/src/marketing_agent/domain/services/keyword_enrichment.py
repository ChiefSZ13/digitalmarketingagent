"""Live keyword metric enrichment and opportunity scoring."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from marketing_agent.domain.models.evidence import EvidenceRecord, EvidenceSource
from marketing_agent.domain.models.keyword import (
    EnrichmentMetrics,
    KeywordCandidate,
    KeywordCluster,
    KeywordCompetition,
    KeywordEnrichmentStatus,
    KeywordIntelligence,
    KeywordIntelligenceCluster,
    KeywordIntelligenceKeyword,
    KeywordIntelligenceMethodology,
    KeywordMarketMetrics,
    KeywordMonthlyMetric,
    KeywordOpportunityScoreComponents,
    KeywordOrigin,
    KeywordTrendDirection,
    MarketingTermType,
    ProviderMatchType,
    ScoreComponents,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.provider import (
    CacheStatus,
    ProviderRunStatus,
    ProviderRunTelemetry,
    build_provider_telemetry,
)
from marketing_agent.domain.ports.keyword_data_provider import (
    KeywordEnrichmentRequest,
    KeywordMetricsProvider,
    KeywordMetricsProviderError,
    KeywordProviderRecord,
)
from marketing_agent.domain.ports.keyword_metrics_cache import KeywordMetricsCache
from marketing_agent.domain.services.keyword_clusterer import cluster_keywords
from marketing_agent.domain.services.keyword_normalizer import (
    deduplicate_keywords,
    normalize_keyword,
)
from marketing_agent.domain.services.search_query_validator import SearchQueryValidator

TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
POLICY_NOTES = [
    "Provider metrics are approximate and scoped to the configured market and language.",
    "Missing provider fields remain null and are not treated as zero.",
    "Opportunity score is separate from product relevance and uses only available metrics.",
]


@dataclass(frozen=True)
class KeywordEnrichmentConfig:
    provider: str
    market: str
    language: str
    currency: str
    max_keywords: int
    batch_size: int
    cache_ttl_seconds: int
    scoring_policy_version: str
    matching_policy_version: str
    trend_policy_version: str
    include_related_terms: bool = True
    cache_namespace_version: str = "keyword-metrics-cache-v1"


@dataclass(frozen=True)
class KeywordEnrichmentPipelineResult:
    candidates: list[KeywordCandidate]
    intelligence: KeywordIntelligence
    evidence: list[EvidenceRecord]
    warnings: list[str]
    telemetry: list[ProviderRunTelemetry]


async def enrich_keyword_candidates(
    *,
    profile: ProductProfile,
    candidates: list[KeywordCandidate],
    provider: KeywordMetricsProvider,
    cache: KeywordMetricsCache,
    config: KeywordEnrichmentConfig,
) -> KeywordEnrichmentPipelineResult:
    """Enrich eligible search-query candidates with provider-backed market metrics."""
    selected = [
        candidate
        for candidate in candidates
        if candidate.marketing_term_type == MarketingTermType.SEARCH_QUERY
        and candidate.eligible_for_live_enrichment
    ][: config.max_keywords]
    warnings: list[str] = []
    telemetry: list[ProviderRunTelemetry] = []
    provider_records: dict[str, KeywordProviderRecord] = {}
    started_at = datetime.now(UTC)

    if config.provider.lower() in {"none", "null", "disabled"}:
        intelligence = _build_keyword_intelligence(
            candidates=candidates,
            clusters=cluster_keywords(candidates),
            config=config,
            status=KeywordEnrichmentStatus.SKIPPED,
            warnings=["Keyword enrichment provider is disabled."],
        )
        return KeywordEnrichmentPipelineResult(
            candidates=candidates,
            intelligence=intelligence,
            evidence=[],
            warnings=intelligence.warnings,
            telemetry=[
                build_provider_telemetry(
                    provider=config.provider,
                    operation="keyword_enrichment",
                    started_at=started_at,
                    status=ProviderRunStatus.SKIPPED,
                    result_count=0,
                    cache_status=CacheStatus.BYPASS,
                    correlation_id="keyword-enrichment-disabled",
                )
            ],
        )

    if not selected:
        intelligence = _build_keyword_intelligence(
            candidates=candidates,
            clusters=cluster_keywords(candidates),
            config=config,
            status=KeywordEnrichmentStatus.SKIPPED,
            warnings=["No keyword candidates were eligible for live enrichment."],
        )
        return KeywordEnrichmentPipelineResult(
            candidates=candidates,
            intelligence=intelligence,
            evidence=[],
            warnings=intelligence.warnings,
            telemetry=[
                build_provider_telemetry(
                    provider=config.provider,
                    operation="keyword_enrichment",
                    started_at=started_at,
                    status=ProviderRunStatus.SKIPPED,
                    result_count=0,
                    cache_status=CacheStatus.BYPASS,
                    correlation_id="keyword-enrichment-empty",
                )
            ],
        )

    misses: list[KeywordCandidate] = []
    cached_count = 0
    for candidate in selected:
        cache_key = build_keyword_cache_key(candidate.normalized_text, config)
        cached = await cache.get(cache_key)
        if cached is None:
            misses.append(candidate)
            continue
        cached_count += 1
        provider_records[normalize_keyword(cached.keyword)] = cached

    if misses:
        for batch in _batches(misses, max(1, config.batch_size)):
            try:
                provider_result = await provider.enrich(
                    KeywordEnrichmentRequest(
                        keywords=[candidate.text for candidate in batch],
                        market=config.market,
                        language=config.language,
                        currency=config.currency,
                        max_keywords=len(batch),
                    )
                )
            except KeywordMetricsProviderError as exc:
                warnings.append(f"Keyword provider failed: {exc}")
                telemetry.append(
                    build_provider_telemetry(
                        provider=config.provider,
                        operation="keyword_enrichment",
                        started_at=started_at,
                        status=ProviderRunStatus.FAILED,
                        result_count=len(provider_records),
                        cache_status=CacheStatus.PARTIAL_HIT if cached_count else CacheStatus.MISS,
                        error_category="provider_error",
                        correlation_id="keyword-enrichment-provider-error",
                    )
                )
                continue

            cache_status = CacheStatus.PARTIAL_HIT if cached_count else CacheStatus.MISS
            telemetry.append(
                provider_result.telemetry.model_copy(update={"cache_status": cache_status})
            )
            warnings.extend(provider_result.warnings)
            for record in provider_result.records:
                normalized = normalize_keyword(record.keyword)
                provider_records[normalized] = record
                await cache.set(
                    build_keyword_cache_key(normalized, config),
                    record,
                    config.cache_ttl_seconds,
                )
    else:
        telemetry.append(
            build_provider_telemetry(
                provider=config.provider,
                operation="keyword_enrichment",
                started_at=started_at,
                status=ProviderRunStatus.SUCCEEDED,
                result_count=cached_count,
                cache_status=CacheStatus.HIT,
                correlation_id="keyword-enrichment-cache-hit",
            )
        )

    enriched_candidates, evidence = _merge_provider_records(
        profile=profile,
        candidates=candidates,
        selected=selected,
        provider_records=list(provider_records.values()),
        config=config,
    )
    clusters = cluster_keywords(enriched_candidates)
    matched_count = sum(
        1 for candidate in enriched_candidates if candidate.enrichment.provider is not None
    )
    status = KeywordEnrichmentStatus.COMPLETE
    if matched_count < len(selected) or warnings:
        status = KeywordEnrichmentStatus.PARTIAL_SUCCESS
    if provider_records and matched_count == 0:
        status = KeywordEnrichmentStatus.FAILED
        warnings.append(
            "Keyword provider returned records that did not match generated candidates."
        )

    intelligence = _build_keyword_intelligence(
        candidates=enriched_candidates,
        clusters=clusters,
        config=config,
        status=status,
        warnings=warnings,
    )
    return KeywordEnrichmentPipelineResult(
        candidates=enriched_candidates,
        intelligence=intelligence,
        evidence=evidence,
        warnings=warnings,
        telemetry=telemetry,
    )


def build_keyword_cache_key(normalized_keyword: str, config: KeywordEnrichmentConfig) -> str:
    material = "|".join(
        [
            config.cache_namespace_version,
            config.provider.lower(),
            normalize_keyword(normalized_keyword),
            config.market.upper(),
            config.language.lower(),
            config.currency.upper(),
            config.matching_policy_version,
            config.trend_policy_version,
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def calculate_trend(
    history: list[KeywordMonthlyMetric],
) -> tuple[KeywordTrendDirection, float | None, str]:
    ordered = sorted(history, key=lambda item: (item.year, item.month))
    if len(ordered) < 6:
        return (
            KeywordTrendDirection.INSUFFICIENT_DATA,
            None,
            "Fewer than six monthly points were available.",
        )
    recent = ordered[-3:]
    previous = ordered[-6:-3]
    recent_average = sum(item.searches for item in recent) / 3
    previous_average = sum(item.searches for item in previous) / 3
    if previous_average == 0:
        if recent_average == 0:
            return KeywordTrendDirection.FLAT, 0.0, "Recent and previous demand were both zero."
        return KeywordTrendDirection.RISING, 1.0, "Recent demand appeared after a zero baseline."
    change = (recent_average - previous_average) / previous_average
    strength = round(min(1.0, abs(change)), 4)
    if change >= 0.15:
        return (
            KeywordTrendDirection.RISING,
            strength,
            "Recent three-month average is meaningfully above the previous three months.",
        )
    if change <= -0.15:
        return (
            KeywordTrendDirection.DECLINING,
            strength,
            "Recent three-month average is meaningfully below the previous three months.",
        )
    return (
        KeywordTrendDirection.FLAT,
        strength,
        "Recent and previous three-month averages are broadly similar.",
    )


def _merge_provider_records(
    *,
    profile: ProductProfile,
    candidates: list[KeywordCandidate],
    selected: list[KeywordCandidate],
    provider_records: list[KeywordProviderRecord],
    config: KeywordEnrichmentConfig,
) -> tuple[list[KeywordCandidate], list[EvidenceRecord]]:
    evidence: list[EvidenceRecord] = []
    selected_by_norm = {candidate.normalized_text: candidate for candidate in selected}
    enriched_by_norm: dict[str, KeywordCandidate] = {}
    now = datetime.now(UTC)

    for candidate in candidates:
        if candidate.normalized_text not in selected_by_norm:
            enriched_by_norm[candidate.normalized_text] = candidate
            continue
        match = _best_record_match(candidate, provider_records)
        if match is None:
            enriched_by_norm[candidate.normalized_text] = candidate
            continue
        record, match_type, match_confidence = match
        trend_direction, trend_strength, trend_explanation = calculate_trend(record.monthly_history)
        metrics = KeywordMarketMetrics(
            provider=record.provider,
            provider_record_id=record.provider_record_id,
            keyword=candidate.text,
            matched_provider_term=record.keyword,
            provider_match_type=match_type,
            provider_match_confidence=match_confidence,
            average_monthly_searches=record.average_monthly_searches,
            competition=record.competition,
            competition_index=record.competition_index,
            cpc_low=record.cpc_low,
            cpc_high=record.cpc_high,
            currency=record.currency or config.currency,
            monthly_history=record.monthly_history,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            trend_explanation=trend_explanation,
            market=config.market,
            language=config.language,
            retrieved_at=now,
            source_confidence=record.source_confidence or match_confidence,
        )
        components, opportunity, market_signal = _score_opportunity(candidate, metrics, config)
        evidence_id = _provider_evidence_id(candidate.normalized_text)
        evidence.append(
            EvidenceRecord(
                id=evidence_id,
                source=EvidenceSource.KEYWORD_PROVIDER,
                source_reference=f"{record.provider}:{record.keyword}",
                observation=(
                    "Keyword provider returned market metrics for "
                    f"'{candidate.text}' in {config.market}/{config.language}."
                ),
                confidence=record.source_confidence or match_confidence,
                provider=record.provider,
                field_name="keyword_metrics",
                observed_value=record.keyword,
                observed_at=now,
                provider_run_id=record.provider_record_id,
            )
        )
        updated = candidate.model_copy(
            update={
                "evidence_ids": list(dict.fromkeys([*candidate.evidence_ids, evidence_id])),
                "enrichment": EnrichmentMetrics(
                    average_monthly_searches=metrics.average_monthly_searches,
                    competition_level=metrics.competition.value if metrics.competition else None,
                    cpc_low=metrics.cpc_low,
                    cpc_high=metrics.cpc_high,
                    trend=metrics.trend_direction.value,
                    source_confidence=metrics.source_confidence,
                    provider=metrics.provider,
                    provider_record_id=metrics.provider_record_id,
                    provider_match_type=metrics.provider_match_type,
                    provider_match_confidence=metrics.provider_match_confidence,
                    matched_provider_term=metrics.matched_provider_term,
                    market=metrics.market,
                    language=metrics.language,
                    currency=metrics.currency,
                    retrieved_at=metrics.retrieved_at,
                ),
                "market_signal_score": market_signal,
                "opportunity_score": opportunity,
                "opportunity_components": components,
                "scoring_policy_version": config.scoring_policy_version,
            }
        )
        enriched_by_norm[candidate.normalized_text] = updated

    related = (
        _build_related_candidates(
            profile=profile,
            base_candidates=list(enriched_by_norm.values()),
            provider_records=provider_records,
            evidence=evidence,
            config=config,
        )
        if config.include_related_terms
        else []
    )
    merged = deduplicate_keywords([*enriched_by_norm.values(), *related])
    return merged, evidence


def _build_related_candidates(
    *,
    profile: ProductProfile,
    base_candidates: list[KeywordCandidate],
    provider_records: list[KeywordProviderRecord],
    evidence: list[EvidenceRecord],
    config: KeywordEnrichmentConfig,
) -> list[KeywordCandidate]:
    validator = SearchQueryValidator(profile)
    existing = {candidate.normalized_text for candidate in base_candidates}
    record_by_norm = {normalize_keyword(record.keyword): record for record in provider_records}
    related_candidates: list[KeywordCandidate] = []
    evidence_ids = {record.id for record in evidence}
    now = datetime.now(UTC)

    for base in base_candidates:
        record = record_by_norm.get(normalize_keyword(base.enrichment.matched_provider_term or ""))
        if record is None:
            continue
        for related_term in record.related_terms[:3]:
            validation = validator.validate(related_term, [base.text])
            if not validation.eligible_for_live_enrichment:
                continue
            if validation.normalized_query in existing:
                continue
            existing.add(validation.normalized_query)
            evidence_id = _provider_evidence_id(f"related-{validation.normalized_query}")
            if evidence_id not in evidence_ids:
                evidence_ids.add(evidence_id)
                evidence.append(
                    EvidenceRecord(
                        id=evidence_id,
                        source=EvidenceSource.KEYWORD_PROVIDER,
                        source_reference=f"{record.provider}:{record.keyword}:related_terms",
                        observation=(
                            "Keyword provider returned a related term that passed "
                            "search-query validation."
                        ),
                        confidence=record.source_confidence or 0.7,
                        provider=record.provider,
                        field_name="related_terms",
                        observed_value=validation.normalized_query,
                        observed_at=now,
                        provider_run_id=record.provider_record_id,
                    )
                )
            components = ScoreComponents(
                product_match=validation.product_relevance_score,
                intent_value=base.score_components.intent_value,
                evidence_strength=record.source_confidence or 0.7,
                audience_fit=base.score_components.audience_fit,
                specificity=validation.specificity_score,
                risk_penalty=0.0,
            )
            candidate = KeywordCandidate(
                text=validation.normalized_query,
                normalized_text=validation.normalized_query,
                marketing_term_type=MarketingTermType.SEARCH_QUERY,
                query_family=base.query_family,
                intent=base.intent,
                category=base.category,
                rationale=f"Provider-related term discovered from '{base.text}'.",
                source="keyword_provider_related_terms",
                evidence_ids=[evidence_id],
                relevance_score=components.relevance(),
                confidence_score=round(
                    min(
                        1.0,
                        0.45 * validation.product_relevance_score
                        + 0.35 * validation.query_realism_score
                        + 0.20 * (record.source_confidence or 0.7),
                    ),
                    4,
                ),
                generation_confidence=0.0,
                product_relevance_score=validation.product_relevance_score,
                query_realism_score=validation.query_realism_score,
                specificity_score=validation.specificity_score,
                commercial_intent_score=validation.commercial_intent_score,
                source_concepts=[base.text],
                origin="keyword_provider_related_terms",
                origins=[KeywordOrigin.PROVIDER_RELATED_TERM],
                rejection_reasons=[],
                eligible_for_live_enrichment=True,
                generator_version="keyword-provider-related-v1",
                score_components=components,
                scoring_policy_version=config.scoring_policy_version,
                risk_flags=[],
            )
            related_candidates.append(candidate)
    return related_candidates[: min(8, config.max_keywords)]


def _score_opportunity(
    candidate: KeywordCandidate,
    metrics: KeywordMarketMetrics,
    config: KeywordEnrichmentConfig,
) -> tuple[KeywordOpportunityScoreComponents | None, float | None, float | None]:
    market_demand = _market_demand(metrics.average_monthly_searches)
    competition_advantage = _competition_advantage(metrics.competition)
    cpc_efficiency = _cpc_efficiency(metrics.cpc_low, metrics.cpc_high)
    trend_signal = _trend_signal(metrics.trend_direction, metrics.trend_strength)
    provider_values = [market_demand, competition_advantage, cpc_efficiency, trend_signal]
    available_provider_values = [value for value in provider_values if value is not None]
    if not available_provider_values:
        return None, None, None

    data_completeness = round(len(available_provider_values) / len(provider_values), 4)
    components = KeywordOpportunityScoreComponents(
        product_relevance=candidate.product_relevance_score,
        market_demand=market_demand,
        competition_advantage=competition_advantage,
        commercial_intent=candidate.commercial_intent_score,
        cpc_efficiency=cpc_efficiency,
        trend_signal=trend_signal,
        data_completeness=data_completeness,
        risk_penalty=min(0.5, 0.12 * len(candidate.risk_flags)),
    )
    market_signal_values = [
        value for value in (market_demand, competition_advantage, trend_signal) if value is not None
    ]
    market_signal = (
        round(sum(market_signal_values) / len(market_signal_values), 4)
        if market_signal_values
        else None
    )
    weighted_values = [
        (0.35, components.product_relevance),
        (0.10, components.commercial_intent),
    ]
    if market_demand is not None:
        weighted_values.append((0.25, market_demand))
    if competition_advantage is not None:
        weighted_values.append((0.15, competition_advantage))
    if cpc_efficiency is not None:
        weighted_values.append((0.05, cpc_efficiency))
    if trend_signal is not None:
        weighted_values.append((0.10, trend_signal))
    weight_total = sum(weight for weight, _ in weighted_values)
    opportunity = round(
        max(
            0.0,
            min(
                1.0,
                sum(weight * value for weight, value in weighted_values) / weight_total
                - components.risk_penalty,
            ),
        ),
        4,
    )
    return components, opportunity, market_signal


def _market_demand(searches: int | None) -> float | None:
    if searches is None:
        return None
    return round(min(1.0, math.log1p(searches) / math.log1p(100_000)), 4)


def _competition_advantage(competition: KeywordCompetition | None) -> float | None:
    if competition is None or competition == KeywordCompetition.UNKNOWN:
        return None
    return {
        KeywordCompetition.LOW: 0.85,
        KeywordCompetition.MEDIUM: 0.55,
        KeywordCompetition.HIGH: 0.25,
    }[competition]


def _cpc_efficiency(low: float | None, high: float | None) -> float | None:
    values = [value for value in (low, high) if value is not None]
    if not values:
        return None
    midpoint = sum(values) / len(values)
    return round(max(0.0, min(1.0, 1.0 - min(midpoint, 20.0) / 20.0)), 4)


def _trend_signal(
    direction: KeywordTrendDirection,
    strength: float | None,
) -> float | None:
    if direction in {KeywordTrendDirection.UNKNOWN, KeywordTrendDirection.INSUFFICIENT_DATA}:
        return None
    base = {
        KeywordTrendDirection.RISING: 0.7,
        KeywordTrendDirection.FLAT: 0.55,
        KeywordTrendDirection.DECLINING: 0.35,
        KeywordTrendDirection.SEASONAL: 0.5,
    }[direction]
    if strength is None:
        return base
    adjustment = min(0.2, 0.2 * strength)
    if direction == KeywordTrendDirection.RISING:
        return round(min(1.0, base + adjustment), 4)
    if direction == KeywordTrendDirection.DECLINING:
        return round(max(0.0, base - adjustment), 4)
    return round(base, 4)


def _build_keyword_intelligence(
    *,
    candidates: list[KeywordCandidate],
    clusters: list[KeywordCluster],
    config: KeywordEnrichmentConfig,
    status: KeywordEnrichmentStatus,
    warnings: list[str],
) -> KeywordIntelligence:
    intelligence_keywords = [_to_intelligence_keyword(candidate) for candidate in candidates]
    by_text = {keyword.text: keyword for keyword in intelligence_keywords}
    intelligence_clusters: list[KeywordIntelligenceCluster] = []
    for cluster in clusters:
        opportunities: list[float] = []
        for text in cluster.member_keywords:
            keyword = by_text.get(text)
            if keyword is not None and keyword.opportunity_score is not None:
                opportunities.append(keyword.opportunity_score)
        aggregate_opportunity = (
            round(sum(opportunities) / len(opportunities), 4) if opportunities else None
        )
        intelligence_clusters.append(
            KeywordIntelligenceCluster(
                id=cluster.id,
                theme=cluster.theme,
                primary_keyword=cluster.primary_keyword,
                member_keywords=cluster.member_keywords,
                dominant_intent=cluster.dominant_intent,
                aggregate_relevance=cluster.aggregate_relevance,
                aggregate_opportunity=aggregate_opportunity,
                keyword_count=len(cluster.member_keywords),
            )
        )
    return KeywordIntelligence(
        status=status,
        provider=config.provider,
        market=config.market,
        language=config.language,
        collected_at=datetime.now(UTC),
        keywords=intelligence_keywords,
        clusters=intelligence_clusters,
        warnings=list(dict.fromkeys(warnings)),
        methodology=KeywordIntelligenceMethodology(
            scoring_policy_version=config.scoring_policy_version,
            matching_policy_version=config.matching_policy_version,
            trend_policy_version=config.trend_policy_version,
            notes=POLICY_NOTES,
        ),
    )


def _to_intelligence_keyword(candidate: KeywordCandidate) -> KeywordIntelligenceKeyword:
    metrics = _candidate_metrics(candidate)
    return KeywordIntelligenceKeyword(
        text=candidate.text,
        normalized_text=candidate.normalized_text,
        origins=candidate.origins,
        intent=candidate.intent,
        category=candidate.category,
        query_family=candidate.query_family,
        product_relevance_score=candidate.product_relevance_score,
        confidence_score=candidate.confidence_score,
        market_signal_score=candidate.market_signal_score,
        opportunity_score=candidate.opportunity_score,
        opportunity_components=candidate.opportunity_components,
        scoring_policy_version=candidate.scoring_policy_version,
        metrics=metrics,
        rationale=candidate.rationale,
        evidence_ids=candidate.evidence_ids,
        risk_flags=candidate.risk_flags,
        source=candidate.source,
        related_to=candidate.source_concepts[0]
        if KeywordOrigin.PROVIDER_RELATED_TERM in candidate.origins and candidate.source_concepts
        else None,
    )


def _candidate_metrics(candidate: KeywordCandidate) -> KeywordMarketMetrics | None:
    enrichment = candidate.enrichment
    if enrichment.provider is None or enrichment.matched_provider_term is None:
        return None
    competition = (
        KeywordCompetition(enrichment.competition_level) if enrichment.competition_level else None
    )
    trend = (
        KeywordTrendDirection(enrichment.trend)
        if enrichment.trend
        else KeywordTrendDirection.UNKNOWN
    )
    return KeywordMarketMetrics(
        provider=enrichment.provider,
        provider_record_id=enrichment.provider_record_id,
        keyword=candidate.text,
        matched_provider_term=enrichment.matched_provider_term,
        provider_match_type=enrichment.provider_match_type or ProviderMatchType.NONE,
        provider_match_confidence=enrichment.provider_match_confidence or 0.0,
        average_monthly_searches=enrichment.average_monthly_searches,
        competition=competition,
        cpc_low=enrichment.cpc_low,
        cpc_high=enrichment.cpc_high,
        currency=enrichment.currency,
        trend_direction=trend,
        market=enrichment.market or "US",
        language=enrichment.language or "en",
        retrieved_at=enrichment.retrieved_at or datetime.now(UTC),
        source_confidence=enrichment.source_confidence,
    )


def _best_record_match(
    candidate: KeywordCandidate,
    records: list[KeywordProviderRecord],
) -> tuple[KeywordProviderRecord, ProviderMatchType, float] | None:
    best: tuple[KeywordProviderRecord, ProviderMatchType, float] | None = None
    for record in records:
        match_type, confidence = _match_provider_term(candidate.text, record.keyword)
        if match_type == ProviderMatchType.NONE:
            continue
        if best is None or confidence > best[2]:
            best = (record, match_type, confidence)
    return best


def _match_provider_term(left: str, right: str) -> tuple[ProviderMatchType, float]:
    if left.casefold() == right.casefold():
        return ProviderMatchType.EXACT, 1.0
    left_norm = normalize_keyword(left)
    right_norm = normalize_keyword(right)
    if left_norm == right_norm:
        return ProviderMatchType.NORMALIZED, 0.97
    left_compact = _compact(left_norm)
    right_compact = _compact(right_norm)
    if left_compact == right_compact:
        return ProviderMatchType.PUNCTUATION_INSENSITIVE, 0.94
    if _singularize(left_norm) == _singularize(right_norm):
        return ProviderMatchType.SINGULAR_PLURAL, 0.88
    left_tokens = set(TOKEN_RE.findall(left_norm))
    right_tokens = set(TOKEN_RE.findall(right_norm))
    if not left_tokens or not right_tokens:
        return ProviderMatchType.NONE, 0.0
    overlap = len(left_tokens.intersection(right_tokens)) / max(len(left_tokens), len(right_tokens))
    if overlap >= 0.8:
        return ProviderMatchType.TOKEN_OVERLAP, round(0.72 + 0.18 * overlap, 4)
    return ProviderMatchType.NONE, 0.0


def _compact(value: str) -> str:
    return value.replace(" ", "").replace("-", "")


def _singularize(value: str) -> str:
    tokens = [
        token[:-1] if token.endswith("s") and len(token) > 3 else token for token in value.split()
    ]
    return " ".join(tokens)


def _provider_evidence_id(value: str) -> str:
    digest = hashlib.sha1(normalize_keyword(value).encode("utf-8")).hexdigest()[:12]
    return f"ev-keyword-provider-{digest}"


def _batches(items: list[KeywordCandidate], batch_size: int) -> list[list[KeywordCandidate]]:
    grouped: list[list[KeywordCandidate]] = []
    for index in range(0, len(items), batch_size):
        grouped.append(items[index : index + batch_size])
    return grouped
