"""Local filesystem artifact repository."""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from marketing_agent.domain.models.marketplace import MarketplaceReviewOverride
from marketing_agent.domain.models.run import PerceptionRun
from marketing_agent.domain.ports.artifact_repository import ArtifactRepository


class LocalArtifactRepository(ArtifactRepository):
    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = artifact_dir

    async def save_run(self, run: PerceptionRun) -> None:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        target = self.artifact_dir / f"{run.run_id}.json"
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.artifact_dir,
            delete=False,
            prefix=f".{run.run_id}.",
            suffix=".tmp",
        ) as tmp:
            tmp.write(run.model_dump_json(indent=2))
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)

    async def get_run(self, run_id: str) -> PerceptionRun | None:
        if not run_id.startswith("run_"):
            return None
        target = self.artifact_dir / f"{run_id}.json"
        if not target.exists():
            return None
        return PerceptionRun.model_validate_json(target.read_text(encoding="utf-8"))

    async def save_marketplace_override(
        self, override: MarketplaceReviewOverride
    ) -> MarketplaceReviewOverride:
        existing = await self.list_marketplace_overrides(override.run_id)
        now = datetime.now(UTC)
        merged: list[MarketplaceReviewOverride] = []
        found = False
        for item in existing:
            if item.listing_id == override.listing_id:
                found = True
                merged.append(
                    override.model_copy(
                        update={
                            "created_at": item.created_at,
                            "updated_at": now,
                        }
                    )
                )
            else:
                merged.append(item)
        if not found:
            merged.append(override.model_copy(update={"updated_at": now}))
        await self._write_overrides(override.run_id, merged)
        for item in merged:
            if item.listing_id == override.listing_id:
                return item
        raise RuntimeError("saved marketplace override was not found")

    async def list_marketplace_overrides(self, run_id: str) -> list[MarketplaceReviewOverride]:
        if not run_id.startswith("run_"):
            return []
        target = self._override_path(run_id)
        if not target.exists():
            return []
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        overrides: list[MarketplaceReviewOverride] = []
        for item in cast(list[Any], raw):
            if isinstance(item, dict):
                overrides.append(
                    MarketplaceReviewOverride.model_validate(cast(dict[str, Any], item))
                )
        return overrides

    async def _write_overrides(
        self, run_id: str, overrides: list[MarketplaceReviewOverride]
    ) -> None:
        target = self._override_path(run_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=target.parent,
            delete=False,
            prefix=f".{run_id}.",
            suffix=".tmp",
        ) as tmp:
            tmp.write(json.dumps([item.model_dump(mode="json") for item in overrides], indent=2))
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)

    def _override_path(self, run_id: str) -> Path:
        return self.artifact_dir / "marketplace-overrides" / f"{run_id}.json"
