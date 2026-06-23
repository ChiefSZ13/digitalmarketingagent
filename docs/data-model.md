# Data Model

The MVP uses Pydantic v2 models as the source of truth.

- `EvidenceRecord` distinguishes `user_description`, `user_metadata`, `image_observation`, `model_inference`, and reserved `keyword_provider` sources.
- `EvidenceLinkedText` is used for every material product assertion and stores confidence plus evidence IDs.
- `ProductProfile` separates observed facts, user-provided facts, inferred attributes, unknowns, ambiguities, limitations, and claim warnings.
- `KeywordCandidate` stores normalized text, category, intent, rationale, evidence IDs, transparent score components, relevance/confidence scores, risk flags, and null enrichment metrics.
- `KeywordCluster` groups compatible category/intent candidates and stores aggregate relevance.
- `PerceptionRun` stores schema version, run ID, UTC timestamps, image metadata, prompt version, provider metadata, warnings, errors, and stage statuses.

The schema version for this slice is `2026-06-23.mvp1b.v1`.

