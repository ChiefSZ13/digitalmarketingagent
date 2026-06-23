# Product Perception and Keyword Intelligence

This repository contains the first working slice of an agentic digital-marketing platform: a FastAPI backend, a Next.js frontend, deterministic mock providers, and a live OpenAI perception adapter kept behind a provider port.

Current scope is MVP 0, MVP 1, and MVP 1B only. The app accepts one to five product images and a description, returns an evidence-backed product profile, generates categorized and ranked keyword candidates, clusters them, and lets a user inspect and export the result in the browser.

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
PERCEPTION_PROVIDER=openai
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4.1-mini
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

The response contains a `run_id`, product profile sections, evidence records, keyword candidates, clusters, warnings, stage statuses, and provider metadata. Search volume, CPC, competition, ranking, and trend fields are reserved for MVP 1C and remain `null` in this slice.

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
make check
```

## Frontend Workflow

The single-page UI supports image upload, previews, image removal, required description validation, optional metadata, pending/error/success states, product profile review, keyword cluster cards, keyword search/filter/sort, expandable keyword evidence details, and JSON copy/download.

## Architecture

The backend is a modular monolith. Domain code defines Pydantic models and pure services. Application orchestration coordinates the pipeline through ports. Infrastructure implements the mock provider, OpenAI provider, image validation, and local artifact repository. API routes map HTTP requests to the same pipeline used by the CLI.

## Limitations

- Mock perception does not make factual visual claims beyond upload validity and image dimensions.
- Live keyword-provider enrichment is not implemented.
- PostgreSQL and Redis are optional future infrastructure only, not part of the MVP 1 runtime.
- No authentication, publishing, ad-budget control, video generation, search-engine scraping, or autonomous optimization is included.

## Recommended Next Task

MVP 1C: add a `KeywordDataProvider` implementation with rate limiting, retries, caching, provider contract tests, and clear market/language labeling for approximate metrics.
