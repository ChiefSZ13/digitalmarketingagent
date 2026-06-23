"""Deterministic keyword normalization and duplicate removal."""

import re
import unicodedata
from difflib import SequenceMatcher

from marketing_agent.domain.models.keyword import KeywordCandidate

PUNCTUATION_RE = re.compile(r"[^\w\s-]", re.UNICODE)
SPACE_RE = re.compile(r"\s+")


def normalize_keyword(text: str) -> str:
    """Normalize keyword text for comparison while preserving model numbers."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("–", "-").replace("—", "-")
    normalized = PUNCTUATION_RE.sub(" ", normalized)
    normalized = SPACE_RE.sub(" ", normalized).strip().lower()
    return normalized


def are_near_duplicates(left: str, right: str, threshold: float = 0.92) -> bool:
    left_norm = normalize_keyword(left)
    right_norm = normalize_keyword(right)
    if left_norm == right_norm:
        return True
    compact_left = left_norm.replace(" ", "").replace("-", "")
    compact_right = right_norm.replace(" ", "").replace("-", "")
    if compact_left == compact_right:
        return True
    return SequenceMatcher(None, left_norm, right_norm).ratio() >= threshold


def deduplicate_keywords(candidates: list[KeywordCandidate]) -> list[KeywordCandidate]:
    """Keep the strongest candidate for exact and near-duplicate terms."""
    selected: list[KeywordCandidate] = []
    for candidate in sorted(
        candidates,
        key=lambda item: (item.relevance_score, item.confidence_score, len(item.text)),
        reverse=True,
    ):
        if any(
            are_near_duplicates(candidate.normalized_text, seen.normalized_text)
            for seen in selected
        ):
            continue
        selected.append(candidate)
    return sorted(selected, key=lambda item: item.relevance_score, reverse=True)
