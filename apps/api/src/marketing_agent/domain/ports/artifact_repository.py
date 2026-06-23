"""Repository port for immutable run artifacts."""

from typing import Protocol

from marketing_agent.domain.models.run import PerceptionRun


class ArtifactRepository(Protocol):
    async def save_run(self, run: PerceptionRun) -> None:
        """Persist a completed run artifact."""

    async def get_run(self, run_id: str) -> PerceptionRun | None:
        """Return a persisted run artifact, if available."""
