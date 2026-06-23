from pathlib import Path

import httpx
import pytest

from marketing_agent.api.dependencies import get_repository_cached
from marketing_agent.config import Settings, get_settings
from marketing_agent.main import create_app
from tests.conftest import make_png_bytes


@pytest.mark.asyncio
async def test_create_and_get_perception_run(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        artifact_dir=tmp_path / "runs",
        perception_provider="mock",
    )
    get_repository_cached.cache_clear()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/perception-runs",
            data={
                "description": "Portable rechargeable desk lamp for remote workers",
                "brand": "Acme",
                "market": "US",
                "language": "en-US",
                "category_hint": "Lighting",
                "target_audience_hint": "remote workers",
            },
            files={"images": ("lamp.png", make_png_bytes(), "image/png")},
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["product_profile"]["product_name"]
        assert payload["keyword_clusters"]
        assert payload["warnings"]

        fetched = await client.get(f"/api/v1/perception-runs/{payload['run_id']}")
        assert fetched.status_code == 200
        assert fetched.json()["run_id"] == payload["run_id"]


@pytest.mark.asyncio
async def test_invalid_image_problem_response(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        artifact_dir=tmp_path / "runs",
        perception_provider="mock",
    )
    get_repository_cached.cache_clear()
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
