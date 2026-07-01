.PHONY: install dev dev-api dev-web format lint typecheck typecheck-api typecheck-web test test-api test-web test-e2e test-unit test-integration test-evals evaluate-product-matcher evaluate-keyword-generation evaluate-keyword-enrichment smoke-test-marketplace-provider check openapi docker-up docker-down db-up db-down db-migrate db-reset db-shell seed-dev-data

API_DIR := apps/api
WEB_DIR := apps/web

install:
	cd $(API_DIR) && uv sync --all-extras --dev
	cd $(WEB_DIR) && pnpm install

dev:
	@echo "Run 'make db-up db-migrate' first when PERSISTENCE_ENABLED=true."
	@echo "Then run 'make dev-api' and 'make dev-web' in separate shells."

dev-api:
	cd $(API_DIR) && if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi; uv run uvicorn marketing_agent.main:app --reload --host "$${APP_HOST:-127.0.0.1}" --port "$${APP_PORT:-8000}"

dev-web:
	cd $(WEB_DIR) && if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi; pnpm dev --hostname "$${WEB_HOST:-127.0.0.1}" --port "$${WEB_PORT:-3101}"

format:
	cd $(API_DIR) && uv run ruff format src tests
	cd $(WEB_DIR) && pnpm format

lint:
	cd $(API_DIR) && uv run ruff check src tests
	cd $(WEB_DIR) && pnpm lint

typecheck: typecheck-api typecheck-web

typecheck-api:
	cd $(API_DIR) && uv run pyright

typecheck-web:
	cd $(WEB_DIR) && pnpm typecheck

test: test-api test-web

test-api:
	cd $(API_DIR) && uv run pytest

test-web:
	cd $(WEB_DIR) && pnpm test

test-e2e:
	cd $(WEB_DIR) && pnpm test:e2e

test-unit:
	cd $(API_DIR) && uv run pytest tests/unit

test-integration:
	cd $(API_DIR) && uv run pytest tests/integration

test-evals:
	cd $(API_DIR) && uv run python ../../scripts/run_eval.py

evaluate-product-matcher:
	cd $(API_DIR) && uv run python ../../scripts/evaluate_product_matcher.py

evaluate-keyword-generation:
	cd $(API_DIR) && uv run python ../../scripts/evaluate_keyword_generation.py

evaluate-keyword-enrichment:
	cd $(API_DIR) && uv run python ../../scripts/evaluate_keyword_enrichment.py

smoke-test-marketplace-provider:
	cd $(API_DIR) && uv run python ../../scripts/smoke_test_marketplace_provider.py

openapi:
	cd $(API_DIR) && uv run python ../../scripts/export_schema.py

check: format lint typecheck test openapi

docker-up:
	docker compose up -d

docker-down:
	docker compose down

db-up:
	docker compose up -d postgres

db-down:
	docker compose stop postgres

db-migrate:
	cd $(API_DIR) && if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi; uv run alembic upgrade head

db-reset:
	docker compose down -v
	docker compose up -d postgres
	cd $(API_DIR) && if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi; uv run alembic upgrade head

db-shell:
	docker compose exec postgres psql -U postgres -d marketing_agent

seed-dev-data:
	cd $(API_DIR) && if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi; uv run python ../../scripts/seed_dev_data.py
