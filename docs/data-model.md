# Data Model

The MVP uses Pydantic v2 models as the source of truth.

- `EvidenceRecord` distinguishes `user_description`, `user_metadata`, `image_observation`, `model_inference`, and reserved `keyword_provider` sources.
- `EvidenceLinkedText` is used for every material product assertion and stores confidence plus evidence IDs.
- `ProductProfile` separates observed facts, user-provided facts, inferred attributes, unknowns, ambiguities, limitations, and claim warnings.
- `KeywordCandidate` stores normalized text, category, intent, rationale, evidence IDs, transparent score components, relevance/confidence scores, risk flags, and null enrichment metrics.
- `KeywordCluster` groups compatible category/intent candidates and stores aggregate relevance.
- `ProductIdentity` is the canonical marketplace-matching identity derived from
  the product profile without guessing unknown identifiers.
- `NormalizedMarketplaceListing` is the provider-neutral listing shape used by
  the matcher.
- `ProductMatchResult` records status, score, matched fields, unknown fields,
  conflicts, reason codes, aggregation eligibility, group, and matcher version.
- `MarketplaceSnapshot` stores the canonical identity, validation summary,
  listing-level validation records, validated platform rankings, and validated
  price estimates.
- `PerceptionRun` stores schema version, run ID, UTC timestamps, image metadata, prompt version, provider metadata, warnings, errors, and stage statuses.

Marketplace evidence records may include provider, platform, listing ID, field
name, observed value, observation time, provider run ID, normalization version,
and matcher version.

The schema version for this slice is `2026-06-25.marketplace_validation.v2`.
