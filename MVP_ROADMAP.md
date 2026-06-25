# MVP Roadmap

Status labels:

- `Complete`: implemented and covered by the normal project checks.
- `In progress`: usable slice exists, but follow-up work is still expected.
- `Planned`: not started or only described architecturally.

## MVP 0 — Foundation — Complete

Reproducible Python/FastAPI repository, validation tooling, CI, observability skeleton, mockable providers.

Progress:

- Backend and frontend local development commands are available through the Makefile.
- Mockable provider architecture is in place.
- OpenAPI contract export and normal quality gates are available through `make check`.

## MVP 1 — Product Perception — In Progress

Image + description -> evidence-backed structured product profile.

Progress:

- Product analysis accepts one to five images plus a description.
- OpenAI and mock perception providers return schema-validated product profiles.
- Evidence records distinguish user-provided facts, image observations, model inferences, unknowns, and unverified claims.
- Frontend displays the product profile and lets users inspect/export the JSON response.

### MVP 1 Data Collection Sub-Track — In Progress

Product profile -> fixed marketplace data schema -> provider-backed marketplace/source ranking and observed price ranges.

Progress:

- Added a fixed `marketplace_snapshot` output shape to the API response.
- Added a provider abstraction so different market-data vendors can fill the same JSON fields.
- Added a mock marketplace provider for local development, CI, and frontend fixture mode.
- Added a SerpAPI Google Shopping provider for live observed offer/source/price/review data.
- Marketplace provider queries now prefer the model-generated `marketplace_search_query` field, which is intended to contain the normalized core product model instead of raw human descriptions or narrow variant descriptors.
- Added marketplace evidence records so provider observations can be traced.
- Added frontend rendering for platform rankings, observed offer/review signals, price ranges, methodology, limitations, and non-live data warnings.
- Added a deterministic-first product-validation pipeline between marketplace provider results and aggregation.
- Added canonical product identity, normalized marketplace listing, match conflict, feature-score, match-result, and validation-summary models.
- Added hard validation rules for identifiers, model numbers, brands, accessories, bundles, package quantities, variants, and non-new conditions.
- Primary marketplace rankings and price ranges now use only exact/probable primary matches; rejected, uncertain, alternate package, alternate variant, and alternate condition listings remain visible but excluded from primary aggregation.
- Added frontend product-validation groups, conflict explanations, match scores, and local-only review actions for uncertain listings.
- Added `make evaluate-product-matcher` with fixture coverage for exact, ambiguous, accessory, multipack, variant, and condition cases.

Current limitations:

- This is live marketplace observation data, not direct seller-dashboard sales data.
- True `observed_units_sold` is only populated when a provider result explicitly exposes a sold/bought signal.
- SerpAPI live-key validation should be run with a real key before relying on it in production.
- Additional providers such as direct marketplace APIs, retailer feeds, Keepa, or eBay data can be added behind the same provider port later.
- Manual listing review decisions are frontend-local for now and are not persisted as separate override records.
- Product matching is deterministic and intentionally conservative; the evaluation dataset is a small smoke benchmark, not a statistically meaningful market-wide benchmark.
- Optional LLM ambiguity review is configured but not implemented or enabled.

## MVP 1B — Keyword Intelligence — In Progress

Product profile -> normalized, classified, clustered, ranked keyword output without fabricated market metrics.

Progress:

- Keyword candidates are generated from the normalized product profile.
- Keywords are normalized, deduplicated, classified, scored, clustered, and rendered in the frontend.
- Search volume, CPC, competition, and trend fields are intentionally not fabricated.

## MVP 1C — Live Keyword Enrichment — Planned

Provider abstraction -> licensed search-volume, competition, CPC, trend, and related-term data.

## MVP 2 — Campaign Memory — Planned

PostgreSQL versioned snapshots, object storage, prompt/model/cost/audit records, Redis for transient coordination.

## MVP 3 — Creative Planning — Planned

Platform briefs, hooks, scripts, CTAs, storyboards, policy and brand constraints.

## MVP 4 — Media Generation — Planned

Video/image/TTS/caption adapters, media assembly, QA, approval workflows.

## MVP 5 — Publishing and Measurement — Planned

Platform adapters, attribution IDs, metrics ingestion, commerce-event integration.

## MVP 6 — Optimization — Planned

Evidence-based experiment selection, bounded mutations, statistical evaluation, human oversight.
