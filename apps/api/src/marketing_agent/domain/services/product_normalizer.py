"""Product profile normalization."""

from marketing_agent.domain.models.product import ProductProfile


def normalize_product_profile(profile: ProductProfile) -> ProductProfile:
    """Return a normalized profile while preserving evidence references."""
    claim_flags = profile.claim_flags or profile.unsafe_or_unverified_claims
    unsafe = profile.unsafe_or_unverified_claims or claim_flags
    return profile.model_copy(
        update={
            "claim_flags": claim_flags,
            "unsafe_or_unverified_claims": unsafe,
        }
    )
