from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from marketing_agent.config import Settings, get_settings


def make_png_bytes(size: tuple[int, int] = (8, 8)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color=(32, 96, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        artifact_dir=tmp_path / "runs",
        perception_provider="mock",
        max_image_bytes=256_000,
        max_image_pixels=1_000_000,
    )
