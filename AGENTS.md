# AGENTS.md — Product Perception & Keyword Intelligence Agent

## 1. Purpose

This repository implements the first production slice of an agentic digital-marketing platform.

The initial system accepts:

1. one or more product images;
2. a user-provided product description; and
3. optional product metadata such as brand, category, market, language, price, URL, and target audience.

It returns a structured, evidence-backed product profile and a ranked set of categorized keyword clusters suitable for later campaign planning and creative generation.

This file is the durable operating contract for Codex and other coding agents working in this repository. Read it before making changes.

---

## 2. Product Vision

The long-term platform is a closed-loop digital-marketing agent:

`product input -> perception -> keyword intelligence -> campaign memory -> creative planning -> asset generation -> publishing -> analytics -> optimization`

This repository begins with only the perception and keyword-intelligence portion. Do not prematurely implement video generation, social publishing, campaign analytics, or autonomous optimization unless a later task explicitly expands the scope.

---

## 3. MVP Roadmap

### MVP 0 — Repository Foundation

Goal: establish a clean, reproducible engineering environment for both the API and a small web client.

Deliverables:

- Python project managed with `uv`.
- Small web application managed with `pnpm`.
- Node.js 22 LTS and Next.js with TypeScript.
- Python 3.12.
- FastAPI application with `/health` and `/ready` endpoints.
- Next.js frontend that can run locally against the mock-backed API.
- CLI entry point.
- Pydantic v2 schemas.
- Ruff, Pyright, Pytest, pre-commit, and coverage configuration.
- `.env.example`; never commit secrets.
- Dockerfile and local `docker compose` for optional PostgreSQL/Redis.
- Structured logging and request IDs.
- CI workflow that runs backend and frontend linting, type checking, unit tests, integration tests, and contract tests.

Exit criteria:

- `make check` succeeds from a clean checkout.
- API and frontend start locally.
- CI passes.
- No business logic beyond a trivial example.

### MVP 1 — Perception Core

Goal: convert product images and text into a normalized product-intelligence object.

Inputs:

- one to five images in JPG, PNG, or WebP;
- product description;
- optional metadata.

Outputs:

- normalized product name;
- category and subcategory;
- visible attributes;
- likely features;
- user-facing benefits;
- materials, colors, form factor, and packaging clues;
- intended use cases;
- possible target audiences;
- differentiators;
- ambiguities and missing information;
- claim-safety flags;
- evidence references for every nontrivial assertion;
- confidence score per extracted field.

Core rule:

> Never turn a visual guess into a factual product claim. Every extracted fact must be labeled as user-provided, visually observed, inferred, or unknown.

Exit criteria:

- deterministic JSON schema;
- multimodal provider adapter;
- mock provider for offline tests;
- representative golden test cases;
- end-to-end API, CLI, and browser UI path;
- malformed and unsupported files rejected safely;
- no hallucinated certifications, ingredients, performance figures, or medical claims.

### MVP 1B — Keyword Generation and Classification

Goal: generate useful candidate keywords from the normalized product profile without depending on live search-provider access.

Outputs:

- seed keywords;
- long-tail keywords;
- problem/solution phrases;
- feature phrases;
- use-case phrases;
- audience phrases;
- comparison phrases;
- commercial-intent phrases;
- informational phrases;
- negative keywords;
- content angles;
- platform-language suggestions.

Each keyword must include:

- text;
- normalized form;
- category;
- intent;
- source;
- rationale;
- relevance score;
- confidence score;
- risk flags;
- associated product evidence IDs.

Exit criteria:

- duplicate and near-duplicate terms removed;
- keyword categories and intents validated against enums;
- score bounds enforced;
- results stable enough for snapshot testing;
- no unsupported search-volume claims.

### MVP 1C — Live Keyword Enrichment

Goal: enrich generated candidates with approved third-party keyword data.

Architecture:

- define a `KeywordDataProvider` protocol;
- keep provider-specific SDK code in infrastructure adapters;
- domain code must not depend on Google Ads, DataForSEO, SerpAPI, or any single vendor;
- allow a `null` provider and fixtures for development;
- cache provider responses;
- persist source, market, language, retrieval timestamp, and raw provider record ID.

Possible enrichment fields:

- average monthly searches;
- competition level;
- CPC range;
- recent trend;
- related terms;
- source-specific confidence.

Restrictions:

- do not scrape Google or Bing result pages directly;
- do not violate provider terms of service;
- do not imply that approximate metrics are exact;
- do not blend metrics from different markets without labeling them.

Exit criteria:

- at least one provider implementation plus mock provider;
- rate limiting, retries, timeouts, and caching;
- graceful degradation when provider is unavailable;
- provider contract tests.

### MVP 2 — Campaign Memory

Goal: persist products, runs, keyword clusters, prompt versions, model metadata, costs, and user edits.

Recommended storage:

- PostgreSQL as durable source of truth;
- JSONB for versioned snapshots;
- object storage for images;
- Redis only for cache, locks, job state, and rate limits.

### MVP 3 — Creative Strategy

Goal: generate platform-specific briefs, hooks, scripts, CTAs, and storyboard JSON.

### MVP 4 — Media Generation

Goal: call video, image, voice, caption, and media-processing services behind stable adapters.

### MVP 5 — Publishing and Measurement

Goal: publish approved variants through platform adapters and collect attributable performance metrics.

### MVP 6 — Optimization Loop

Goal: propose bounded experiments from measured evidence. Human approval remains required until reliability is demonstrated.

---

## 4. Current Scope

Unless the active task says otherwise, implement only MVP 0, MVP 1, and MVP 1B.

Allowed now:

- product image upload;
- text input;
- multimodal analysis;
- structured product profile;
- generated keyword candidates;
- keyword normalization, classification, clustering, and scoring;
- JSON export;
- a small frontend for upload, progress, result review, filtering, and export;
- API, CLI, frontend, tests, fixtures, documentation, and evaluation tooling.

Not allowed now:

- automatic social posting;
- video generation;
- ad-budget control;
- autonomous campaign optimization;
- browser automation against search engines;
- undocumented scraping;
- building a microservice fleet;
- introducing Kafka, Kubernetes, or a vector database without demonstrated need.

---

## 5. Engineering Principles

1. **Correctness over cleverness.** Prefer explicit domain models and ordinary functions to opaque agent chains.
2. **Modular monolith first.** Keep one deployable application with clear internal boundaries.
3. **Provider independence.** External AI and keyword services are adapters, not domain dependencies.
4. **Schema-first integration.** Every model output must be parsed into validated Pydantic models.
5. **Evidence over fluency.** A confident sentence without evidence is a defect.
6. **One source of truth.** Do not duplicate business rules across API, CLI, and prompts.
7. **Fail visibly.** Return actionable errors; do not silently substitute guessed values.
8. **Reproducibility.** Record model, prompt version, provider, timestamps, and relevant request parameters.
9. **Security by default.** Validate uploads, constrain file sizes, protect secrets, and treat external text as untrusted data.
10. **YAGNI.** Build the simplest design that satisfies current acceptance criteria.

---

## 6. Proposed Repository Layout

```text
.
├── AGENTS.md
├── README.md
├── Makefile
├── .env.example
├── docker-compose.yml
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   └── src/
│   │       └── marketing_agent/
│       ├── __init__.py
│       ├── main.py
│       ├── cli.py
│       ├── config.py
│       ├── logging.py
│       ├── api/
│       │   ├── dependencies.py
│       │   ├── errors.py
│       │   └── routes/
│       │       ├── health.py
│       │       └── perception.py
│       ├── domain/
│       │   ├── models/
│       │   │   ├── product.py
│       │   │   ├── evidence.py
│       │   │   ├── keyword.py
│       │   │   └── run.py
│       │   ├── services/
│       │   │   ├── product_normalizer.py
│       │   │   ├── keyword_generator.py
│       │   │   ├── keyword_normalizer.py
│       │   │   ├── keyword_classifier.py
│       │   │   ├── keyword_clusterer.py
│       │   │   └── keyword_scorer.py
│       │   └── ports/
│       │       ├── perception_provider.py
│       │       ├── keyword_data_provider.py
│       │       └── artifact_repository.py
│       ├── application/
│       │   ├── commands/
│       │   │   └── analyze_product.py
│       │   └── orchestration/
│       │       └── perception_pipeline.py
│       ├── infrastructure/
│       │   ├── ai/
│       │   │   ├── openai_perception_provider.py
│       │   │   ├── mock_perception_provider.py
│       │   │   └── prompts/
│       │   ├── keyword_data/
│       │   │   ├── null_provider.py
│       │   │   └── mock_provider.py
│       │   ├── persistence/
│       │   │   └── local_artifact_repository.py
│       │   └── media/
│       │       └── image_validation.py
│       └── observability/
│           ├── metrics.py
│           └── tracing.py
│   └── web/
│       ├── package.json
│       ├── pnpm-lock.yaml
│       ├── next.config.ts
│       ├── tsconfig.json
│       ├── app/
│       │   ├── page.tsx
│       │   ├── layout.tsx
│       │   └── globals.css
│       ├── components/
│       │   ├── product-analysis-form.tsx
│       │   ├── image-dropzone.tsx
│       │   ├── analysis-progress.tsx
│       │   ├── product-profile-panel.tsx
│       │   ├── keyword-table.tsx
│       │   ├── keyword-filters.tsx
│       │   └── json-export.tsx
│       ├── lib/
│       │   ├── api-client.ts
│       │   ├── schemas.ts
│       │   └── formatters.ts
│       └── tests/
├── packages/
│   └── contracts/
│       ├── openapi.json
│       └── generated/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── evals/
│   └── fixtures/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── data-model.md
│   ├── evaluation.md
│   ├── threat-model.md
│   └── adr/
└── scripts/
    ├── run_eval.py
    └── export_schema.py
```

Keep boundaries real:

- `domain` must not import FastAPI, OpenAI SDKs, SQLAlchemy, Redis, or vendor SDKs.
- `application` coordinates domain services through ports.
- `infrastructure` implements ports.
- `api` maps HTTP requests to application commands.

---

## 7. Domain Model Requirements

### 7.1 Evidence

Every material output should be traceable.

```python
class EvidenceSource(str, Enum):
    USER_DESCRIPTION = "user_description"
    USER_METADATA = "user_metadata"
    IMAGE_OBSERVATION = "image_observation"
    MODEL_INFERENCE = "model_inference"
    KEYWORD_PROVIDER = "keyword_provider"
```

An evidence record should contain:

- unique ID;
- source type;
- source reference, such as image index or description span;
- concise observation;
- optional quoted text no longer than necessary;
- confidence from `0.0` to `1.0`;
- timestamp.

### 7.2 Product Profile

The product profile must distinguish:

- `observed_facts`;
- `user_provided_facts`;
- `inferred_attributes`;
- `unknowns`;
- `unsafe_or_unverified_claims`.

Do not collapse all attributes into a flat dictionary.

Suggested top-level fields:

- `product_name`;
- `brand`;
- `category`;
- `subcategory`;
- `summary`;
- `visual_attributes`;
- `features`;
- `benefits`;
- `materials`;
- `colors`;
- `use_cases`;
- `target_audiences`;
- `differentiators`;
- `limitations`;
- `ambiguities`;
- `claim_flags`;
- `evidence`;
- `overall_confidence`.

### 7.3 Keyword Candidate

```python
class KeywordIntent(str, Enum):
    INFORMATIONAL = "informational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"
    COMPARISON = "comparison"
    NAVIGATIONAL = "navigational"
    UNKNOWN = "unknown"

class KeywordCategory(str, Enum):
    PRODUCT = "product"
    FEATURE = "feature"
    BENEFIT = "benefit"
    PROBLEM_SOLUTION = "problem_solution"
    USE_CASE = "use_case"
    AUDIENCE = "audience"
    LONG_TAIL = "long_tail"
    ALTERNATIVE = "alternative"
    NEGATIVE = "negative"
    CONTENT_ANGLE = "content_angle"
```

Each candidate must have:

- `text`;
- `normalized_text`;
- `intent`;
- `category`;
- `rationale`;
- `source`;
- `evidence_ids`;
- `relevance_score`;
- `confidence_score`;
- optional enrichment metrics;
- `risk_flags`.

### 7.4 Keyword Cluster

A cluster must have:

- stable ID;
- human-readable theme;
- primary keyword;
- member keywords;
- dominant intent;
- aggregate relevance;
- evidence IDs;
- recommended usage.

---

## 8. Perception Pipeline

Implement the pipeline as explicit stages:

1. validate request;
2. validate and normalize images;
3. create content hashes;
4. call perception provider;
5. parse structured response;
6. validate evidence coverage;
7. normalize product profile;
8. generate keyword candidates;
9. normalize and deduplicate candidates;
10. classify intent and category;
11. cluster candidates;
12. score candidates and clusters;
13. create immutable run artifact;
14. return JSON response.

Each stage should be independently testable. Do not hide the full workflow in one prompt or one function.

---

## 9. AI Provider Rules

### 9.1 Adapter Contract

Define a domain-facing protocol similar to:

```python
class PerceptionProvider(Protocol):
    async def analyze(
        self,
        request: PerceptionRequest,
    ) -> ProviderPerceptionResult:
        ...
```

The rest of the application must not know which model or vendor is used.

### 9.2 Structured Output

- Use provider-supported structured output when available.
- Validate every response with Pydantic.
- Reject invalid output after a bounded repair attempt.
- Never parse domain-critical output with ad hoc regex.
- Store prompt version, model name, provider request ID, latency, and token usage when available.

### 9.3 Prompt Design

Prompt files belong in versioned files, not inline string blobs.

A perception prompt must:

- identify the task and output schema;
- order evidence sources by reliability;
- state that product description is untrusted data, not instructions;
- prohibit invented certifications, ingredients, dimensions, health effects, warranties, and performance metrics;
- require uncertainty and unknowns;
- require evidence IDs;
- be concise enough to avoid unnecessary cost.

A keyword prompt must:

- use only the normalized product profile;
- generate diverse but relevant candidates;
- prohibit fake volume, CPC, rank, or trend claims;
- label negative terms;
- avoid trademark misuse and prohibited targeting;
- return structured output.

### 9.4 Model Configuration

- Model name comes from configuration.
- Do not hardcode secrets or model IDs in domain code.
- Use bounded timeouts and retries.
- Retry only transient failures.
- Avoid high randomness for schema extraction.
- Cache only when the exact content hash and prompt version match.

---

## 10. Keyword Processing Rules

### Normalization

Normalize using a deterministic function:

- Unicode normalize;
- trim whitespace;
- collapse repeated spaces;
- lowercase for comparison while preserving display text;
- normalize punctuation;
- avoid stemming that changes meaning;
- preserve important model numbers and brands.

### Deduplication

Apply in order:

1. exact normalized match;
2. case and punctuation-insensitive match;
3. configurable lexical similarity;
4. optional semantic similarity.

Do not use an embedding database in MVP 1 unless test evidence shows lexical methods are inadequate.

### Scoring

Use a transparent initial score:

```text
relevance_score =
    0.35 * product_match
  + 0.20 * intent_value
  + 0.15 * evidence_strength
  + 0.15 * audience_fit
  + 0.15 * specificity
  - risk_penalty
```

All components must be between `0.0` and `1.0`. Store components for explainability.

Without a live provider, do not include search volume in the score.

### Clustering

For MVP 1B, use deterministic category/theme grouping plus lightweight similarity. A cluster must never mix contradictory intents merely because terms are semantically close.

---


## 11. Frontend Requirements

Build a small, production-minded web interface for MVP 1. The frontend is part of the vertical slice, not a separate future project.

### 11.1 Technical Stack

Use:

- Next.js App Router;
- TypeScript in strict mode;
- React;
- Tailwind CSS for restrained corporate styling;
- TanStack Query for server-state management;
- React Hook Form with Zod validation;
- Vitest and React Testing Library;
- Playwright for one end-to-end happy-path test;
- generated API types from the backend OpenAPI document where practical.

Do not introduce Redux, a large design system, authentication, or a separate backend-for-frontend for this MVP.

### 11.2 User Flow

The first screen must support one complete workflow:

1. upload one to five product images using drag-and-drop or file selection;
2. preview and remove selected images;
3. enter the required product description;
4. optionally enter brand, market, language, category hint, and audience hint;
5. submit the analysis request;
6. display a clear pending/progress state;
7. show a structured product profile;
8. show keyword clusters and keyword candidates;
9. filter and sort keywords by category, intent, relevance, confidence, and text;
10. inspect evidence, rationale, confidence, and risk flags;
11. copy or download the complete JSON result;
12. reset the workflow and analyze another product.

### 11.3 Required Screens and Components

For MVP 1, a single responsive page is sufficient. It should contain:

- page header and short explanation;
- product-analysis form;
- image dropzone with previews and validation messages;
- optional metadata section;
- submit and reset controls;
- analysis status panel;
- product profile summary;
- tabs or sections for facts, inferred attributes, unknowns, and claim warnings;
- keyword cluster summary cards;
- searchable and sortable keyword table;
- expandable detail row or side panel for rationale and evidence;
- JSON preview/download action;
- empty, loading, success, partial-success, and error states.

### 11.4 Frontend Architecture Rules

- The frontend must not contain keyword scoring, classification, clustering, or perception business logic.
- Treat the API response as the source of truth.
- Keep API access in one typed client module.
- Use an environment variable such as `NEXT_PUBLIC_API_BASE_URL`.
- Add a development mock mode using saved fixtures so frontend work does not require an OpenAI key.
- Display backend RFC 7807 errors in user-friendly language while preserving the request ID for support.
- Do not expose provider metadata, prompts, or secrets unless a development-only debug flag is enabled.
- Avoid persisting uploaded images in browser storage.
- Revoke object URLs created for previews.
- Meet basic accessibility requirements: labels, keyboard navigation, focus states, error associations, and sufficient contrast.

### 11.5 Visual Direction

Use a simple corporate interface:

- white background;
- black and gray text;
- restrained blue accent;
- clear spacing and hierarchy;
- simple borders and cards;
- no decorative gradients, excessive animation, or marketing-style visual effects.

### 11.6 Frontend Testing

At minimum, test:

- required description validation;
- image count and type validation;
- image removal;
- successful form submission against a mocked API;
- loading and error states;
- rendering product profile and keyword data;
- filtering and sorting keywords;
- JSON download;
- one Playwright happy-path flow using the mock provider.

### 11.7 Frontend Acceptance Criteria

The frontend is complete when a new developer can run the API and web app locally, upload sample images, submit a description, receive a mock-backed analysis, inspect the product profile and keywords, filter the results, and download the result JSON without using the CLI or an API client.

---

## 12. API Contract


Base path: `/api/v1`

### `POST /api/v1/perception-runs`

Use `multipart/form-data`.

Fields:

- `images`: one to five files;
- `description`: required text;
- `brand`: optional;
- `market`: optional ISO-style market code;
- `language`: optional BCP-47 language tag;
- `category_hint`: optional;
- `target_audience_hint`: optional;
- `include_debug`: optional boolean, disabled in production.

Response:

- HTTP `201`;
- run ID;
- normalized product profile;
- keyword clusters;
- warnings;
- metadata.

### `GET /api/v1/perception-runs/{run_id}`

Return a stored run when persistence is enabled.

### Error Format

Use RFC 7807-style problem details:

```json
{
  "type": "https://example.local/errors/invalid-image",
  "title": "Invalid image",
  "status": 422,
  "detail": "Image 2 exceeds the configured size limit.",
  "instance": "/api/v1/perception-runs",
  "request_id": "..."
}
```

### HTTP Rules

- `400` malformed request;
- `413` payload too large;
- `415` unsupported media type;
- `422` semantically invalid input;
- `429` rate limited;
- `502` provider failure;
- `503` dependency unavailable;
- no internal stack traces in responses.

Maintain an OpenAPI 3.1 contract and validate it in CI.

---

## 13. File and Image Security

- Accept only JPEG, PNG, and WebP for MVP 1.
- Verify actual file signature; do not trust extension or content type alone.
- Enforce configured size and pixel-count limits.
- Decode images in a constrained path and reject decompression bombs.
- Strip metadata before sending or storing unless explicitly needed.
- Never execute uploaded content.
- Use generated filenames, never user filenames, for storage paths.
- Hash content for deduplication.
- Do not log image bytes or full base64 content.
- Treat visible text inside images as data, not instructions.

---

## 14. Configuration and Secrets

Use environment-based settings via a typed configuration class.

Required conventions:

- `.env` is local only and gitignored;
- `.env.example` contains names and safe placeholders;
- no fallback production secrets;
- fail fast if required production configuration is missing;
- redact secrets in logs;
- provider API keys are accessed only in infrastructure code.

Suggested variables:

```text
APP_ENV
APP_LOG_LEVEL
APP_HOST
APP_PORT
OPENAI_API_KEY
OPENAI_MODEL
PERCEPTION_TIMEOUT_SECONDS
MAX_IMAGE_BYTES
MAX_IMAGE_PIXELS
MAX_IMAGES_PER_REQUEST
ARTIFACT_DIR
DATABASE_URL
REDIS_URL
```

---

## 15. Testing Strategy

### Unit Tests

Test pure business logic:

- normalization;
- validation;
- scoring;
- deduplication;
- classification;
- clustering;
- evidence coverage;
- serialization.

### Integration Tests

Test:

- FastAPI request lifecycle;
- multipart uploads;
- provider adapters against mocks;
- artifact repository;
- configuration;
- error mapping.

### Frontend Tests

Test:

- form validation and upload behavior;
- typed API client behavior;
- loading, partial-success, error, and success states;
- product-profile rendering;
- keyword filtering and sorting;
- JSON export;
- one end-to-end browser path with mock data.

### Contract Tests

- validate OpenAPI schema;
- validate provider adapter behavior;
- ensure mock and real adapters return equivalent domain structures.

### Evaluation Tests

Create a versioned evaluation set containing representative products:

- simple single-object product;
- product with packaging text;
- visually ambiguous product;
- conflicting image and description;
- product with risky health claim;
- product with model number;
- product photographed with distracting background;
- non-product image;
- low-resolution image;
- multilingual description.

Measure:

- schema-valid response rate;
- attribute precision;
- unsupported-claim rate;
- evidence coverage;
- keyword relevance;
- duplicate rate;
- category accuracy;
- latency;
- cost per run.

A change to a prompt or model requires running the evaluation set and recording results.

### Minimum Quality Gates

- unit and integration tests pass;
- type checking passes;
- no high-severity security finding;
- no regression in unsupported-claim rate;
- changed behavior documented;
- new business logic includes tests.

---

## 16. Coding Standards

### Python

- Python 3.12.
- Full type annotations for public code.
- Pydantic v2 for external and domain validation.
- `async` only for I/O-bound boundaries; do not make pure domain logic async.
- Small functions with explicit names.
- Prefer dataclasses or Pydantic models over untyped dictionaries.
- Avoid global mutable state.
- Avoid broad `except Exception` unless translating at an application boundary and re-raising with context.
- Use `pathlib`.
- Use timezone-aware UTC timestamps.
- Use `Decimal` for money if introduced later.

### TypeScript and React

- TypeScript strict mode must remain enabled.
- Prefer server components by default and client components only where interactivity requires them.
- Keep components small and accessible.
- Do not duplicate backend schemas manually when generated types are available.
- Validate untrusted API payloads at the client boundary when using saved fixtures or mocks.
- Do not place secrets in `NEXT_PUBLIC_*` variables.
- Avoid business logic in React components.

### Naming

- files and functions: `snake_case`;
- classes and Pydantic models: `PascalCase`;
- constants: `UPPER_SNAKE_CASE`;
- API JSON: `snake_case` consistently.

### Documentation

- explain why, not obvious syntax;
- public modules and nontrivial public functions need docstrings;
- update README and relevant docs when changing behavior;
- significant architectural decisions require an ADR.

---

## 17. Logging and Observability

Every request should include a request ID and, after creation, a run ID.

Log structured fields:

- event name;
- request ID;
- run ID;
- pipeline stage;
- provider;
- model;
- latency;
- retry count;
- result status;
- token or request usage when available;
- error code.

Never log:

- secrets;
- raw image bytes;
- full user descriptions at info level;
- provider authorization headers;
- unredacted personal data.

Create basic metrics for:

- request count;
- success/failure count;
- stage latency;
- provider latency;
- validation failures;
- retries;
- generated keyword count;
- duplicate-removal count.

---

## 18. Reliability Rules

- Set explicit connect and read timeouts.
- Retry transient provider errors with exponential backoff and jitter.
- Do not retry validation errors.
- Bound retry attempts.
- Use idempotency for persisted runs when a client supplies an idempotency key.
- Preserve the original error as chained context internally.
- Degrade gracefully when optional keyword enrichment is unavailable.
- A partially valid result must include warnings and stage status; never pretend the full pipeline succeeded.

---

## 19. Review Checklist

Before considering a task complete, verify:

### Scope

- Is the implementation within the active MVP?
- Did the change avoid speculative infrastructure?

### Architecture

- Are domain and infrastructure concerns separated?
- Does vendor-specific code stay behind a port?
- Is there a simpler design?

### Correctness

- Are schemas explicit and validated?
- Are uncertainties represented?
- Does every claim have evidence?
- Are scores explainable?

### Security

- Are uploads validated by content?
- Are secrets protected?
- Is untrusted text prevented from becoming instructions?
- Are logs safe?

### Tests

- Are normal, error, and edge cases covered?
- Are tests behavioral rather than implementation-coupled?
- Do offline tests avoid real paid API calls?

### Operations

- Are timeouts, retries, and error codes sensible?
- Are meaningful logs and metrics emitted?
- Can the feature be disabled or mocked?

### Documentation

- Are README, API docs, examples, and ADRs updated?
- Is the exact validation command recorded?

---

## 20. Working Protocol for Codex

For every nontrivial task:

1. Read this file and relevant docs.
2. Inspect the repository before proposing changes.
3. Restate the task in one sentence.
4. Identify the active MVP and acceptance criteria.
5. Produce a brief implementation plan.
6. Make the smallest coherent change.
7. Add or update tests in the same change.
8. Run formatter, linter, type checker, and relevant tests.
9. Review the diff for security, accidental scope expansion, and dead code.
10. Report:
    - files changed;
    - architecture decisions;
    - commands run;
    - test results;
    - known limitations;
    - suggested next task.

Do not claim a check passed unless it was run. If a command cannot run, explain exactly why.

---

## 21. Expected Commands

Prefer a `Makefile` that exposes stable commands:

```text
make install
make dev
make dev-api
make dev-web
make format
make lint
make typecheck
make typecheck-api
make typecheck-web
make test
make test-api
make test-web
make test-e2e
make test-unit
make test-integration
make test-evals
make check
make openapi
make docker-up
make docker-down
```

Codex should use existing project commands rather than inventing replacements. If commands do not exist during MVP 0, create them.

---

## 22. Definition of Done for MVP 1B

MVP 1B is complete only when:

- a user can submit valid images and a description through the browser UI, API, and CLI;
- the system returns a schema-valid product profile;
- the system returns categorized and ranked keyword clusters;
- outputs distinguish observed, provided, inferred, and unknown information;
- every material result links to evidence;
- invalid uploads are safely rejected;
- the pipeline can run entirely with mock providers in CI;
- the live AI provider is isolated behind an adapter;
- evaluation fixtures cover at least ten distinct scenarios;
- tests, lint, type checking, and OpenAPI validation pass;
- README includes setup for both apps, example request, example response, screenshots or UI description, architecture, and limitations;
- the frontend can render, filter, inspect, and export mock-backed results;
- frontend unit tests and one mock-backed browser end-to-end test pass;
- no social publishing, video generation, or live search scraping is included.
