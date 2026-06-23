from pathlib import Path

import pytest
from typer.testing import CliRunner

from marketing_agent.cli import app
from marketing_agent.config import get_settings
from tests.conftest import make_png_bytes


def test_cli_analyze_writes_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    image_path = tmp_path / "lamp.png"
    output_path = tmp_path / "output.json"
    image_path.write_bytes(make_png_bytes())
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("PERCEPTION_PROVIDER", "mock")
    get_settings.cache_clear()

    result = CliRunner().invoke(
        app,
        [
            "analyze",
            "--image",
            str(image_path),
            "--description",
            "Portable rechargeable desk lamp",
            "--market",
            "US",
            "--language",
            "en-US",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output_path.exists()
    assert '"keyword_clusters"' in output_path.read_text(encoding="utf-8")
