# Data Model

The MVP uses Pydantic v2 models as the source of truth.

- `EvidenceRecord` distinguishes `user_description`, `user_metadata`, `image_observation`, `model_inference`, and reserved `keyword_provider` sources.
- `EvidenceLinkedText` is used for every material product assertion and stores confidence plus evidence IDs.
- `ProductProfile` separates observed facts, user-provided facts, inferred attributes, unknowns, ambiguities, limitations, and claim warnings.
- `KeywordCandidate` stores normalized search-query text, query family, category, intent, rationale, evidence IDs, transparent score components, product relevance, query realism, generation confidence, source concepts, live-enrichment eligibility, risk flags, and null enrichment metrics.
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
- `PerceptionRun` stores schema version, run ID, durable `analysis_run_id`,
  UTC timestamps, image metadata, prompt version, provider metadata, warnings,
  errors, and stage statuses.

## Persistent Memory Tables

MVP 2A adds PostgreSQL-backed memory using SQLAlchemy async ORM and Alembic.
The exact historical API output is retained in
`intelligence_report_snapshots.report_json`, while frequently inspected facts
are normalized into tables:

- `products`: canonical product identity for a run.
- `analysis_runs`: synchronous run lifecycle, status, input payload, duration,
  errors, and schema version.
- `media_assets`: uploaded image metadata and hashes; image bytes are not stored
  in PostgreSQL.
- `product_profile_versions`: versioned product-profile JSON snapshots.
- `provider_runs`: perception, marketplace, and keyword provider telemetry.
- `marketplace_observations`: normalized marketplace listings and offer facts.
- `product_match_results`: deterministic validation results separate from raw
  observations.
- `manual_match_overrides`: human review decisions stored separately from raw
  observations and automated match results.
- `keyword_candidates`: generated internal keyword candidates and score inputs.
- `keyword_metrics`: live keyword enrichment metrics when available.
- `intelligence_report_snapshots`: full versioned product-intelligence reports.

Provider payload storage is intentionally conservative: secrets and auth-like
fields are redacted, large strings are truncated, and raw provider records are
stored as sanitized JSON or references. Manual overrides are applied as latest
effective review decisions when reports are reopened, but they do not mutate
provider observations or automated match rows.

Marketplace evidence records may include provider, platform, listing ID, field
name, observed value, observation time, provider run ID, normalization version,
and matcher version.

Keyword candidate `confidence_score` and `generation_confidence` indicate
confidence that the system generated a realistic product-relevant search query.
They do not indicate search volume, CPC, rank, competition, or trend.

The schema version for this slice is `2026-06-26.live_keyword_enrichment.v1`.
