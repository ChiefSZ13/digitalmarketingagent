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
- Note: refined official-product verification inside the same validation pipeline. Compatibility language such as `for Xbox` is no longer treated as product-brand evidence, official variants and third-party alternatives are separated from primary aggregation, and the frontend now groups listings as official matches, official variants, licensed alternatives, compatible alternatives, needs review, or rejected.
- Added `make evaluate-product-matcher` with fixture coverage for exact, ambiguous, accessory, multipack, variant, condition, official Xbox, licensed third-party Xbox, generic compatible Xbox, and retailer/seller ambiguity cases.

Current limitations:

- This is live marketplace observation data, not direct seller-dashboard sales data.
- True `observed_units_sold` is only populated when a provider result explicitly exposes a sold/bought signal.
- SerpAPI live-key validation should be run with a real key before relying on it in production.
- Additional providers such as direct marketplace APIs, retailer feeds, Keepa, or eBay data can be added behind the same provider port later.
- Manual listing review decisions are now persisted as separate override records under local artifacts and merged into API responses without mutating raw provider observations or matcher results.
- Product matching is deterministic and intentionally conservative; the evaluation dataset is a small smoke benchmark, not a statistically meaningful market-wide benchmark.
- The brand/product-line registry is intentionally tiny and currently only seeds Microsoft/Xbox examples; unknown brands still use generic deterministic logic.
- Optional LLM ambiguity review is configured but not implemented or enabled.

## MVP 1B — Keyword Intelligence — In Progress

Product profile -> normalized, classified, clustered, ranked keyword output without fabricated market metrics.

Progress:

- Keyword candidates are generated from the normalized product profile.
- Keywords are normalized, deduplicated, classified, scored, clustered, and rendered in the frontend.
- Search volume, CPC, competition, and trend fields are intentionally not fabricated.
- Note: refined keyword generation so `keyword_candidates` contains only short, realistic `search_query` terms. Product features, benefits, audiences, and content ideas are kept out of the enrichment lane unless rewritten as validated search queries with query family, product relevance, query realism, generation confidence, source concepts, rejection reasons, and live-enrichment eligibility. Added `make evaluate-keyword-generation` with air conditioner, Xbox controller, coffee maker, and running shoes smoke cases.

## MVP 1C — Live Keyword Enrichment — In Progress

Provider abstraction -> licensed search-volume, competition, CPC, trend, and related-term data.

Progress:

- Added a `KeywordMetricsProvider` port, normalized provider record model, and in-memory provider-response cache.
- Added mock, null, and DataForSEO keyword metrics providers behind infrastructure adapters.
- Added deterministic provider-record matching, trend calculation, related-term validation, market-signal scoring, and opportunity scoring that keep product relevance separate from market data.
- Added `keyword_intelligence` to the API response with provider status, market/language labels, freshness, warnings, methodology, enriched keyword rows, related terms, and cluster-level opportunity summaries.
- Added provider-run telemetry for marketplace and keyword provider calls, including operation, latency, status, result count, cache status, error category, and correlation ID.
- Added frontend keyword intelligence rendering with filters for search text, intent, origin, competition, trend, and live-metric availability. Missing metrics are shown as missing or insufficient, not zero.
- Added `make evaluate-keyword-enrichment` for a mock-backed enrichment smoke evaluation and `make smoke-test-marketplace-provider` for credential-gated live marketplace provider validation.

Current limitations:

- DataForSEO live keyword data still needs credential-backed smoke testing before production use.
- The cache is in-memory for MVP 1C development and tests; Redis is still deferred to MVP 2 if needed.
- Opportunity scoring is transparent and deterministic, but not yet calibrated against campaign outcomes.

## MVP 2 — Campaign Memory — In Progress

PostgreSQL versioned snapshots, object storage, prompt/model/cost/audit records, Redis for transient coordination.

### MVP 2A — Persistent Product Intelligence Memory — In Progress

Durable product-intelligence memory for analyses, marketplace validation, keyword
intelligence, provider telemetry, and manual review decisions.

Progress:

- Added typed database settings for `DATABASE_URL`, pool sizing, database echo,
  `PERSISTENCE_ENABLED`, and `ADMIN_DB_INSPECTOR_ENABLED`.
- Added PostgreSQL local development through Docker Compose plus Make targets
  for `db-up`, `db-down`, `db-migrate`, `db-reset`, `db-shell`, and
  `seed-dev-data`.
- Added SQLAlchemy async session management and Alembic migration wiring.
- Added persistence tables for products, media assets, analysis runs, product
  profile versions, provider runs, marketplace observations, product match
  results, manual match overrides, keyword candidates, keyword metrics, and full
  intelligence report snapshots.
- Added a SQLAlchemy-backed analysis repository behind the existing
  `ArtifactRepository` port. Domain matching, perception, keyword generation,
  and provider normalization remain outside ORM models.
- Product analysis responses now include `analysis_run_id` when a run is
  created. With persistence enabled, completed runs are saved as versioned JSON
  snapshots and normalized read rows.
- Added persisted analysis APIs under `/api/v1/analyses` for listing, detail,
  report export, marketplace snapshot retrieval, keyword retrieval, and
  observation-level manual override audit records.
- Added a read-only development database inspector under `/admin/db`, disabled
  unless explicitly enabled.
- Added frontend pages for `/analyses`, `/analyses/[id]`, and `/admin/db`.
- Added seed data generation from the mock report fixture for completed and
  partial-success analyses.
- Added migration and persistence API tests covering analysis creation, history,
  report reconstruction, manual override separation, disabled inspector, enabled
  inspector, and Alembic upgrade.

Current limitations:

- The analysis pipeline is still synchronous; no background job queue or Redis
  coordination is required yet.
- Image bytes are not stored in PostgreSQL; only media metadata and content
  hashes are persisted.
- The inspector is a small read-only developer tool, not a production admin
  console.
- Full campaign memory, creative planning, publishing history, analytics, and
  optimization memory remain future MVPs.
- Object storage is still deferred until file persistence requires it.

## MVP 3 — Creative Planning — Planned

Platform briefs, hooks, scripts, CTAs, storyboards, policy and brand constraints.

## MVP 4 — Media Generation — Planned

Video/image/TTS/caption adapters, media assembly, QA, approval workflows.

## MVP 5 — Publishing and Measurement — Planned

Platform adapters, attribution IDs, metrics ingestion, commerce-event integration.

## MVP 6 — Optimization — Planned

Evidence-based experiment selection, bounded mutations, statistical evaluation, human oversight.
