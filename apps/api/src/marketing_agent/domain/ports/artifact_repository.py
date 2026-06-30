"""Repository port for immutable run artifacts."""

from typing import Protocol

from marketing_agent.domain.models.marketplace import MarketplaceReviewOverride
from marketing_agent.domain.models.run import PerceptionRun


class ArtifactRepository(Protocol):
    async def save_run(self, run: PerceptionRun) -> None:
        """Persist a completed run artifact."""

    async def get_run(self, run_id: str) -> PerceptionRun | None:
        """Return a persisted run artifact, if available."""

    async def save_marketplace_override(
        self, override: MarketplaceReviewOverride
    ) -> MarketplaceReviewOverride:
        """Persist a manual marketplace review decision separately from raw provider data."""
        raise NotImplementedError

    async def list_marketplace_overrides(self, run_id: str) -> list[MarketplaceReviewOverride]:
        """Return persisted manual marketplace review decisions for a run."""
        raise NotImplementedError
