"""Seed local PostgreSQL with product-intelligence memory examples."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import typer

from marketing_agent.config import get_settings
from marketing_agent.domain.models.run import PerceptionRun
from marketing_agent.infrastructure.database.session import get_database_sessionmaker_cached
from marketing_agent.infrastructure.persistence.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    fixture_path = root / "apps" / "web" / "public" / "fixtures" / "mock-run.json"
    run = PerceptionRun.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    settings = get_settings()
    sessionmaker = get_database_sessionmaker_cached(
        settings.database_url,
        settings.database_echo,
        settings.database_pool_size,
        settings.database_max_overflow,
    )
    repository = SqlAlchemyAnalysisRepository(sessionmaker)

    completed = run.model_copy(
        update={
            "run_id": f"run_seed_completed_{uuid4().hex[:8]}",
            "analysis_run_id": str(uuid4()),
            "created_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
        },
        deep=True,
    )
    partial = run.model_copy(
        update={
            "run_id": f"run_seed_partial_{uuid4().hex[:8]}",
            "analysis_run_id": str(uuid4()),
            "created_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
            "warnings": [*run.warnings, "Seeded partial-success sample with provider warning."],
            "errors": ["Seeded example: keyword provider timed out after marketplace matching."],
        },
        deep=True,
    )
    await repository.save_run(completed)
    await repository.save_run(partial)
    typer.echo("Seeded 2 persisted product-intelligence analyses.")


if __name__ == "__main__":
    asyncio.run(main())
