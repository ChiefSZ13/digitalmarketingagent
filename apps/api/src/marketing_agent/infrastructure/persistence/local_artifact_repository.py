"""Local filesystem artifact repository."""

import tempfile
from pathlib import Path

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
