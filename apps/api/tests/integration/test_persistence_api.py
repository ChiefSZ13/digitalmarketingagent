from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

from marketing_agent.api.dependencies import (
    get_keyword_metrics_cache_cached,
    get_repository_cached,
    get_sqlalchemy_repository_cached,
)
from marketing_agent.api.security import get_perception_rate_limiter
from marketing_agent.config import Settings, get_settings
from marketing_agent.infrastructure.database.models import Base
from marketing_agent.infrastructure.database.session import (
    get_database_engine_cached,
    get_database_sessionmaker_cached,
)
from marketing_agent.main import create_app
from tests.conftest import make_png_bytes


async def _create_persistent_app(
    tmp_path: Path,
    *,
    inspector_enabled: bool = False,
) -> FastAPI:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'memory.db'}"
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

    get_database_engine_cached.cache_clear()
    get_database_sessionmaker_cached.cache_clear()
    get_sqlalchemy_repository_cached.cache_clear()
    get_repository_cached.cache_clear()
    get_keyword_metrics_cache_cached.cache_clear()
    get_perception_rate_limiter().reset()
    app = create_app()
    settings_values: dict[str, Any] = {
        "artifact_dir": tmp_path / "runs",
        "perception_provider": "mock",
        "marketplace_data_provider": "mock",
        "keyword_provider": "mock",
        "app_access_key": None,
        "persistence_enabled": True,
        "database_url": database_url,
        "admin_db_inspector_enabled": inspector_enabled,
    }
    app.dependency_overrides[get_settings] = lambda: Settings(**settings_values)
    return app


def _valid_upload() -> dict[str, Any]:
    return {
        "data": {
            "description": "Portable rechargeable desk lamp for remote workers",
            "brand": "Acme",
            "market": "US",
            "language": "en-US",
            "category_hint": "Lighting",
            "target_audience_hint": "remote workers",
        },
        "files": {"images": ("lamp.png", make_png_bytes(), "image/png")},
    }


@pytest.mark.asyncio
async def test_analysis_is_persisted_and_reopenable(tmp_path: Path) -> None:
    app = await _create_persistent_app(tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/perception-runs", **_valid_upload())
        assert created.status_code == 201, created.text
        payload = created.json()
        analysis_id = payload["analysis_run_id"]
        assert analysis_id

        listed = await client.get("/api/v1/analyses")
        assert listed.status_code == 200, listed.text
        list_payload = listed.json()
        assert list_payload["total"] == 1
        assert list_payload["items"][0]["analysis_id"] == analysis_id
        assert list_payload["items"][0]["marketplace_observation_count"] > 0
        assert list_payload["items"][0]["keyword_count"] > 0

        detail = await client.get(f"/api/v1/analyses/{analysis_id}")
        assert detail.status_code == 200, detail.text
        detail_payload = detail.json()
        assert detail_payload["report"]["run_id"] == payload["run_id"]
        assert detail_payload["provider_runs"]
        assert detail_payload["marketplace_observations"]
        assert detail_payload["match_results"]

        report = await client.get(f"/api/v1/analyses/{analysis_id}/report")
        assert report.status_code == 200
        assert report.json()["run_id"] == payload["run_id"]


@pytest.mark.asyncio
async def test_manual_override_is_stored_separately_in_database(tmp_path: Path) -> None:
    app = await _create_persistent_app(tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/perception-runs", **_valid_upload())
        analysis_id = created.json()["analysis_run_id"]

        detail = await client.get(f"/api/v1/analyses/{analysis_id}")
        observation = detail.json()["marketplace_observations"][0]
        override = await client.post(
            f"/api/v1/analyses/{analysis_id}/marketplace/{observation['id']}/override",
            json={
                "override_status": "official_match",
                "reason": "Reviewed against the seeded listing.",
            },
        )
        assert override.status_code == 201, override.text
        assert override.json()["override_status"] == "official_match"

        overrides = await client.get(
            f"/api/v1/analyses/{analysis_id}/marketplace/{observation['id']}/overrides"
        )
        assert overrides.status_code == 200
        assert overrides.json()[0]["listing_id"] == observation["listing_id"]

        report = await client.get(f"/api/v1/analyses/{analysis_id}/report")
        manual_overrides = report.json()["marketplace_snapshot"]["manual_overrides"]
        assert manual_overrides[0]["listing_id"] == observation["listing_id"]


@pytest.mark.asyncio
async def test_admin_db_inspector_is_disabled_by_default(tmp_path: Path) -> None:
    app = await _create_persistent_app(tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/db/tables")

    assert response.status_code == 403
    assert response.json()["type"].endswith("admin-db-disabled")


@pytest.mark.asyncio
async def test_admin_db_inspector_lists_tables_and_rows_when_enabled(tmp_path: Path) -> None:
    app = await _create_persistent_app(tmp_path, inspector_enabled=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/perception-runs", **_valid_upload())
        assert created.status_code == 201, created.text

        tables = await client.get("/admin/db/tables")
        assert tables.status_code == 200, tables.text
        table_names = {item["name"] for item in tables.json()["tables"]}
        assert "analysis_runs" in table_names
        assert "marketplace_observations" in table_names

        rows = await client.get("/admin/db/tables/analysis_runs")
        assert rows.status_code == 200, rows.text
        assert rows.json()["total"] == 1
        assert rows.json()["rows"][0]["input_description"]
