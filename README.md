# Product Perception and Keyword Intelligence

This repository contains the first working slice of an agentic digital-marketing platform: a FastAPI backend, a Next.js frontend, deterministic mock providers, and a live OpenAI perception adapter kept behind a provider port.

Current scope is MVP 0, MVP 1, and MVP 1B. Inside MVP 1, the app also includes a data-collection sub-track for Marketplace Snapshot: one to five product images and a description become an evidence-backed product profile, provider-backed marketplace and price observations, categorized and ranked keyword candidates, keyword clusters, and browser-reviewable JSON export.

## Repository Layout

```text
apps/api   FastAPI app, CLI, domain models, providers, tests
apps/web   Next.js App Router UI, fixture mode, component and e2e tests
docs       Architecture, API, data model, evaluation, threat model, ADRs
packages   Exported OpenAPI contract
scripts    OpenAPI export and evaluation runner
```

## Requirements

- Python 3.12 via `uv`
- Node.js 22 LTS
- `pnpm` 9

The local machine used to create this scaffold had newer system runtimes, so the project metadata pins the intended production/developer versions.

## Setup

```bash
make install
cp .env.example .env
```

The root `.env` is the backend profile and is also loaded by the Makefile when
starting the local frontend. Keep secrets only in this root file. For live
OpenAI-backed runs, edit `.env` like this:

```bash
APP_HOST=127.0.0.1
APP_PORT=8010
WEB_HOST=127.0.0.1
WEB_PORT=3101
CORS_ALLOWED_ORIGINS=http://127.0.0.1:3101,http://localhost:3101
APP_ACCESS_KEY=choose_a_long_random_value
RATE_LIMIT_REQUESTS=20
RATE_LIMIT_WINDOW_SECONDS=3600
PERCEPTION_PROVIDER=openai
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4.1-mini
MARKETPLACE_DATA_PROVIDER=mock
SERPAPI_API_KEY=
SERPAPI_LOCATION=United States
PRODUCT_MATCHER_VERSION=product-matcher-v2
PRODUCT_MATCH_EXACT_THRESHOLD=0.93
PRODUCT_MATCH_PROBABLE_THRESHOLD=0.84
PRODUCT_MATCH_UNCERTAIN_THRESHOLD=0.65
PRODUCT_MATCH_REQUIRE_BRAND=false
PRODUCT_MATCH_COLOR_STRICT=false
PRODUCT_MATCH_EXCLUDE_REFURBISHED=true
PRODUCT_MATCH_EXCLUDE_USED=true
AMBIGUOUS_MATCH_REVIEWER_ENABLED=false
AMBIGUOUS_MATCH_REVIEWER_PROVIDER=mock
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8010
NEXT_PUBLIC_USE_FIXTURES=false
```

Use backend mock mode for local development and CI when you do not want to call
OpenAI:

```bash
PERCEPTION_PROVIDER=mock
```

`OPENAI_API_KEY` is read only by the backend. Do not put provider keys in
`NEXT_PUBLIC_*` variables because those are exposed to browser code.

Marketplace Snapshot uses a separate provider port so the JSON shape stays
fixed even when the data vendor changes. For live Google Shopping observations,
use SerpAPI:

```bash
MARKETPLACE_DATA_PROVIDER=serpapi
SERPAPI_API_KEY=your_serpapi_key_here
SERPAPI_LOCATION=United States
```

The live provider fills `marketplace_snapshot` with observed marketplace/source
names, offer counts, review counts, price ranges, source URLs, retrieval time,
and evidence IDs. It does not claim true cross-platform total units sold unless
the provider result explicitly exposes a sold/bought signal for a listing.
Its search query comes from the normalized product profile field
`marketplace_search_query`, which the perception model is asked to set to the
core product model for broad sales and price discovery. For example, a specific
variant such as `Nike Air Jordan 5 Retro University Blue` should produce
`Nike Air Jordan 5`. Deterministic cleanup remains only as a fallback when the
model cannot provide the field; the raw human description is last resort.

Before any marketplace result enters platform rankings or price ranges, it now
passes through deterministic product validation. The matcher builds a canonical
product identity, normalizes each provider listing, applies hard conflict rules
for identifiers, model numbers, brands, accessories, conditions, variants,
bundles, and package quantities, then scores explainable similarity features.
It also verifies brand role and product relationship for official products:
provider brand/manufacturer, detected title brand, compatibility targets, and
official product-line evidence are kept separate. A phrase such as
`for Xbox` or `compatible with Microsoft Xbox` is treated as compatibility
evidence, not as proof that the listing is an official Microsoft/Xbox product.
Licensed and generic third-party compatible alternatives are excluded from the
official product price range.

Match statuses:

- `exact_match`: strong identifier or model agreement, no hard conflicts, and
  score above the exact threshold.
- `probable_match`: no hard conflicts and enough deterministic identity/title
  evidence to enter primary aggregation.
- `uncertain`: not rejected, but missing or conflicting enough evidence to
  require review; excluded from primary aggregation.
- `rejected`: hard conflict or low deterministic similarity.

Each listing also exposes a `relationship`, such as
`official_exact_product`, `official_same_product_family`,
`licensed_third_party_alternative`, `generic_compatible_alternative`,
`accessory_or_replacement`, `unrelated`, or `unknown`.

The frontend groups listings as official matches, official alternate variants,
licensed third-party alternatives, other compatible alternatives, needs review,
and rejected. Needs-review rows have local-only review actions for this
milestone. These overrides do not mutate raw provider observations or stored
artifacts.

An optional ambiguity reviewer is configured but disabled by default:
`AMBIGUOUS_MATCH_REVIEWER_ENABLED=false`. The deterministic matcher works
without an LLM API key, and no LLM can override hard identifier, model, brand,
accessory, or condition conflicts.

For production, set `CORS_ALLOWED_ORIGINS` to the exact frontend origin. For
example, the Render backend for the Vercel app should use:

```bash
CORS_ALLOWED_ORIGINS=https://digitalmarketingagent.vercel.app
```

Do not include a trailing slash.

`APP_ACCESS_KEY` protects the API with an `X-App-Access-Key` header when set.
The browser form includes an Access key field and sends that value only with the
analysis request. In production, `APP_ACCESS_KEY` must be configured; otherwise
the API fails closed with `503`.

## Run Locally

Start the backend and frontend in two separate terminals from the repository
root:

Terminal 1:

```bash
make dev-api
```

Terminal 2:

```bash
make dev-web
```

With the example values above, the API runs at
`http://127.0.0.1:8010` and the browser app runs at
`http://127.0.0.1:3101`.

Verify the backend is ready:

```bash
curl http://127.0.0.1:8010/ready
```

Expected response:

```json
{"status":"ready"}
```

Open the frontend:

```text
http://127.0.0.1:3101
```

If you change `.env`, stop and restart both terminals. Environment variables are
read when each process starts.

### Frontend Environment Notes

When using `make dev-web`, the Makefile loads the root `.env`, so
`NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_USE_FIXTURES=false` come from the
same profile as the backend.

If you start the frontend directly from `apps/web`, create `apps/web/.env.local`
or pass the variables in the command, because Next.js does not automatically
read the repository root `.env` from that working directory:

```bash
cd apps/web
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8010 \
NEXT_PUBLIC_USE_FIXTURES=false \
pnpm dev --hostname 127.0.0.1 --port 3101
```

For the frontend fixture demo without an API key, explicitly enable fixtures:

```bash
cd apps/web
NEXT_PUBLIC_USE_FIXTURES=true pnpm dev --hostname 127.0.0.1 --port 3100
```

Fixture mode returns `public/fixtures/mock-run.json` from the frontend and does
not call the backend. Keep `NEXT_PUBLIC_USE_FIXTURES=false` for live OpenAI
runs.

## API Example

```bash
curl -X POST http://127.0.0.1:8010/api/v1/perception-runs \
  -F "images=@examples/product-front.png" \
  -F "description=Portable rechargeable desk lamp for remote workers" \
  -F "market=US" \
  -F "language=en-US"
```

The response contains a `run_id`, product profile sections, marketplace snapshot, evidence records, keyword candidates, clusters, warnings, stage statuses, and provider metadata. Search volume, CPC, competition, and trend fields are reserved for MVP 1C and remain `null` in this slice.

## CLI Example

```bash
cd apps/api
uv run marketing-agent analyze \
  --image ../../examples/product-front.png \
  --description "Portable rechargeable desk lamp for remote workers" \
  --market US \
  --language en-US \
  --output ../../output.json
```

## Checks

```bash
make format
make lint
make typecheck
make test
make test-e2e
make evaluate-product-matcher
make check
```

## Frontend Workflow

The single-page UI supports image upload, previews, image removal, required description validation, optional metadata, pending/error/success states, product profile review, marketplace snapshot review, keyword cluster cards, keyword search/filter/sort, expandable keyword evidence details, and JSON copy/download.

## Architecture

The backend is a modular monolith. Domain code defines Pydantic models and pure services. Application orchestration coordinates the pipeline through ports. Infrastructure implements the mock perception provider, OpenAI perception provider, mock marketplace provider, SerpAPI marketplace provider, image validation, and local artifact repository. API routes map HTTP requests to the same pipeline used by the CLI.

## Limitations

- Mock perception does not make factual visual claims beyond upload validity and image dimensions.
- SerpAPI-backed Marketplace Snapshot uses live Google Shopping observations, not direct marketplace seller dashboards. It can rank observed sources and price ranges, but it cannot guarantee true cross-platform total units sold.
- Mock Marketplace Snapshot is deterministic fixture data for local development and CI, not market evidence.
- Live keyword-provider enrichment is not implemented.
- PostgreSQL and Redis are optional future infrastructure only, not part of the MVP 1 runtime.
- No authentication, publishing, ad-budget control, video generation, search-engine scraping, or autonomous optimization is included.

## Recommended Next Task

MVP 1C: add a `KeywordDataProvider` implementation with rate limiting, retries, caching, provider contract tests, and clear market/language labeling for approximate metrics.
