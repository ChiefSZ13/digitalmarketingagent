"""Deterministic cluster construction for keyword candidates."""

import re
from collections import defaultdict

from marketing_agent.domain.models.keyword import KeywordCandidate, KeywordCluster


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "cluster"


def cluster_keywords(candidates: list[KeywordCandidate]) -> list[KeywordCluster]:
    grouped: dict[tuple[str, str], list[KeywordCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[(candidate.query_family.value, candidate.intent.value)].append(candidate)

    clusters: list[KeywordCluster] = []
    for (family, intent), members in grouped.items():
        ordered = sorted(members, key=lambda item: item.relevance_score, reverse=True)
        primary = ordered[0]
        evidence_ids = list(
            dict.fromkeys(evidence_id for member in ordered for evidence_id in member.evidence_ids)
        )
        aggregate = round(sum(member.relevance_score for member in ordered) / len(ordered), 4)
        theme = f"{primary.query_family.value.replace('_', ' ').title()} - {intent.title()}"
        clusters.append(
            KeywordCluster(
                id=f"kwc-{_slug(family)}-{_slug(intent)}",
                theme=theme,
                primary_keyword=primary.text,
                member_keywords=[member.text for member in ordered],
                dominant_intent=primary.intent,
                category=primary.category,
                aggregate_relevance=aggregate,
                evidence_ids=evidence_ids,
                recommended_usage=_recommended_usage(family, intent),
            )
        )
    return sorted(clusters, key=lambda item: item.aggregate_relevance, reverse=True)


def _recommended_usage(category: str, intent: str) -> str:
    if category in {"review", "comparison"}:
        return "Use for review and comparison planning after live metric enrichment."
    if category == "local_or_size_specific":
        return "Use for size or local-intent keyword checks when market data is enabled."
    if intent in {"transactional", "commercial"}:
        return "Use for campaign seed terms and live keyword-metric enrichment."
    if intent == "informational":
        return "Use for educational content briefs and FAQ planning."
    if intent == "comparison":
        return "Use for comparison content and positioning research."
    return "Use for exploratory keyword review."
