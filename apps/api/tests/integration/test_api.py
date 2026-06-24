from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from marketing_agent.api.dependencies import get_repository_cached
from marketing_agent.api.security import ACCESS_KEY_HEADER, get_perception_rate_limiter
from marketing_agent.config import Settings, get_settings
from marketing_agent.main import create_app
from tests.conftest import make_png_bytes


def _create_test_app(tmp_path: Path, **settings_overrides: Any) -> FastAPI:
    app = create_app()
    settings_values: dict[str, Any] = {
        "artifact_dir": tmp_path / "runs",
        "perception_provider": "mock",
        "marketplace_data_provider": "mock",
        "serpapi_api_key": None,
        "app_access_key": None,
    }
    settings_values.update(settings_overrides)
    app.dependency_overrides[get_settings] = lambda: Settings(**settings_values)
    get_repository_cached.cache_clear()
    get_perception_rate_limiter().reset()
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
async def test_create_and_get_perception_run(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/perception-runs", **_valid_upload())
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["product_profile"]["product_name"]
        assert len(payload["marketplace_snapshot"]["platform_rankings"]) == 10
        assert payload["marketplace_snapshot"]["is_live_data"] is False
        assert payload["keyword_clusters"]
        assert payload["warnings"]

        fetched = await client.get(f"/api/v1/perception-runs/{payload['run_id']}")
        assert fetched.status_code == 200
        assert fetched.json()["run_id"] == payload["run_id"]


@pytest.mark.asyncio
async def test_invalid_image_problem_response(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/perception-runs",
            data={"description": "Portable lamp"},
            files={"images": ("lamp.jpg", b"not-image", "image/jpeg")},
        )
        assert response.status_code == 415
        payload = response.json()
        assert payload["request_id"]
        assert payload["type"].endswith("unsupported-media-type")


@pytest.mark.asyncio
async def test_access_key_is_required_when_configured(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path, app_access_key="secret")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/perception-runs", **_valid_upload())

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "ApiKey"
    payload = response.json()
    assert payload["type"].endswith("authentication")
    assert ACCESS_KEY_HEADER in payload["detail"]


@pytest.mark.asyncio
async def test_valid_access_key_allows_create_and_get(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path, app_access_key="secret")
    transport = httpx.ASGITransport(app=app)
    headers = {ACCESS_KEY_HEADER: "secret"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/perception-runs", headers=headers, **_valid_upload())
        assert created.status_code == 201, created.text

        run_id = created.json()["run_id"]
        unauthorized_get = await client.get(f"/api/v1/perception-runs/{run_id}")
        assert unauthorized_get.status_code == 401

        authorized_get = await client.get(f"/api/v1/perception-runs/{run_id}", headers=headers)
        assert authorized_get.status_code == 200
        assert authorized_get.json()["run_id"] == run_id


@pytest.mark.asyncio
async def test_production_fails_closed_without_access_key(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path, app_env="production", app_access_key=None)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/perception-runs", **_valid_upload())

    assert response.status_code == 503
    payload = response.json()
    assert payload["type"].endswith("authentication")
    assert "APP_ACCESS_KEY" in payload["detail"]


@pytest.mark.asyncio
async def test_perception_post_is_rate_limited(tmp_path: Path) -> None:
    app = _create_test_app(
        tmp_path,
        app_access_key="secret",
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
    )
    transport = httpx.ASGITransport(app=app)
    headers = {ACCESS_KEY_HEADER: "secret"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/v1/perception-runs", headers=headers, **_valid_upload())
        second = await client.post("/api/v1/perception-runs", headers=headers, **_valid_upload())

    assert first.status_code == 201, first.text
    assert second.status_code == 429
    assert second.headers["retry-after"]
    assert second.headers["x-ratelimit-limit"] == "1"
    payload = second.json()
    assert payload["type"].endswith("rate-limit")
