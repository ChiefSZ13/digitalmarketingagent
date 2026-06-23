"""Rule-based keyword intent and category classification for MVP 1B."""

from marketing_agent.domain.models.keyword import KeywordCategory, KeywordIntent
from marketing_agent.domain.services.keyword_normalizer import normalize_keyword


def classify_intent(text: str, category: KeywordCategory | None = None) -> KeywordIntent:
    normalized = normalize_keyword(text)
    if category == KeywordCategory.NEGATIVE:
        return KeywordIntent.UNKNOWN
    if any(token in normalized for token in ("vs", " versus ", "alternative", "compare", "best")):
        return KeywordIntent.COMPARISON
    if any(token in normalized for token in ("buy", "price", "deal", "shop", "near me")):
        return KeywordIntent.TRANSACTIONAL
    if any(token in normalized for token in ("for sale", "review", "top", "premium")):
        return KeywordIntent.COMMERCIAL
    if any(token in normalized for token in ("how", "what", "why", "guide", "ideas")):
        return KeywordIntent.INFORMATIONAL
    if category in {
        KeywordCategory.PRODUCT,
        KeywordCategory.FEATURE,
        KeywordCategory.BENEFIT,
        KeywordCategory.USE_CASE,
        KeywordCategory.AUDIENCE,
        KeywordCategory.LONG_TAIL,
    }:
        return KeywordIntent.COMMERCIAL
    return KeywordIntent.UNKNOWN


def classify_category(text: str, fallback: KeywordCategory | None = None) -> KeywordCategory:
    normalized = normalize_keyword(text)
    if fallback is not None:
        return fallback
    if any(token in normalized for token in ("cheap", "free", "used", "broken")):
        return KeywordCategory.NEGATIVE
    if any(token in normalized for token in ("vs", "alternative", "compare")):
        return KeywordCategory.ALTERNATIVE
    if any(token in normalized for token in ("how", "guide", "ideas")):
        return KeywordCategory.CONTENT_ANGLE
    if "for " in normalized:
        return KeywordCategory.USE_CASE
    return KeywordCategory.PRODUCT
