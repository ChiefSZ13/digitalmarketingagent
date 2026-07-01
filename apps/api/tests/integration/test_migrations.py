from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command


def test_alembic_upgrade_creates_product_memory_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path}"
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url", database_url.replace("sqlite://", "sqlite+aiosqlite://")
    )

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "products" in tables
    assert "analysis_runs" in tables
    assert "marketplace_observations" in tables
    assert "keyword_candidates" in tables
    assert "intelligence_report_snapshots" in tables
    engine.dispose()
