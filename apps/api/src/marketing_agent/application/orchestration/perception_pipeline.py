"""Explicit product perception pipeline."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from marketing_agent.application.commands.analyze_product import AnalyzeProductCommand
from marketing_agent.config import Settings
from marketing_agent.domain.models.provider import ProviderRunTelemetry
from marketing_agent.domain.models.run import (
    PerceptionRun,
    StageState,
    StageStatus,
)
from marketing_agent.domain.ports.artifact_repository import ArtifactRepository
from marketing_agent.domain.ports.keyword_data_provider import KeywordMetricsProvider
from marketing_agent.domain.ports.keyword_metrics_cache import KeywordMetricsCache
from marketing_agent.domain.ports.marketplace_data_provider import (
    MarketplaceDataProvider,
    MarketplaceDataProviderRequest,
)
from marketing_agent.domain.ports.perception_provider import (
    PerceptionProvider,
    PerceptionProviderRequest,
)
from marketing_agent.domain.services.evidence_validator import (
    validate_keyword_evidence,
    validate_marketplace_evidence,
    validate_profile_evidence,
)
from marketing_agent.domain.services.keyword_clusterer import cluster_keywords
from marketing_agent.domain.services.keyword_enrichment import (
    KeywordEnrichmentConfig,
    enrich_keyword_candidates,
)
from marketing_agent.domain.services.keyword_generator import generate_keyword_candidates
from marketing_agent.domain.services.keyword_normalizer import deduplicate_keywords
from marketing_agent.domain.services.product_normalizer import normalize_product_profile
from marketing_agent.infrastructure.media.image_validation import validate_images

LOGGER = logging.getLogger(__name__)


class PerceptionPipeline:
    def __init__(
        self,
        *,
        settings: Settings,
        provider: PerceptionProvider,
        marketplace_provider: MarketplaceDataProvider,
        keyword_provider: KeywordMetricsProvider,
        keyword_cache: KeywordMetricsCache,
        repository: ArtifactRepository,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.marketplace_provider = marketplace_provider
        self.keyword_provider = keyword_provider
        self.keyword_cache = keyword_cache
        self.repository = repository

    async def analyze(self, command: AnalyzeProductCommand) -> PerceptionRun:
        run_id = f"run_{uuid4().hex}"
        stages: list[StageStatus] = []
        warnings: list[str] = []

        self._complete_stage(stages, "validate_request", "Request shape accepted.")
        validated_images = validate_images(
            command.images,
            max_images=self.settings.max_images_per_request,
            max_bytes=self.settings.max_image_bytes,
            max_pixels=self.settings.max_image_pixels,
        )
        self._complete_stage(stages, "validate_images", "Images decoded and metadata stripped.")
        self._complete_stage(stages, "content_hashes", "Input image content hashes created.")

        provider_result = await self.provider.analyze(
            PerceptionProviderRequest(
                request=command.request,
                images=[image.provider_image for image in validated_images],
            )
        )
        warnings.extend(provider_result.warnings)
        self._complete_stage(
            stages, "call_perception_provider", "Provider returned structured output."
        )
        self._complete_stage(
            stages, "parse_structured_response", "Provider output parsed by Pydantic."
        )

        validate_profile_evidence(provider_result.product_profile)
        self._complete_stage(
            stages,
            "validate_evidence_coverage",
            "Profile evidence coverage verified.",
        )

        profile = normalize_product_profile(provider_result.product_profile)
        self._complete_stage(stages, "normalize_product_profile", "Profile normalized.")

        marketplace_result = await self.marketplace_provider.fetch_snapshot(
            MarketplaceDataProviderRequest(request=command.request, product_profile=profile)
        )
        warnings.extend(marketplace_result.warnings)
        provider_runs: list[ProviderRunTelemetry] = []
        if marketplace_result.telemetry is not None:
            provider_runs.append(marketplace_result.telemetry)
        profile = profile.model_copy(
            update={"evidence": [*profile.evidence, *marketplace_result.evidence]}
        )
        validate_marketplace_evidence(profile, marketplace_result.snapshot)
        self._complete_stage(
            stages,
            "fetch_and_validate_marketplace_snapshot",
            "Marketplace candidates fetched, normalized, matched, and aggregated.",
        )

        generated = generate_keyword_candidates(profile)
        self._complete_stage(
            stages, "generate_keyword_candidates", f"Generated {len(generated)} candidates."
        )

        candidates = deduplicate_keywords(generated)
        removed = len(generated) - len(candidates)
        self._complete_stage(
            stages, "normalize_and_deduplicate_keywords", f"Removed {removed} duplicates."
        )
        self._complete_stage(
            stages, "classify_keywords", "Keyword categories and intents validated."
        )

        enrichment_result = await enrich_keyword_candidates(
            profile=profile,
            candidates=candidates,
            provider=self.keyword_provider,
            cache=self.keyword_cache,
            config=KeywordEnrichmentConfig(
                provider=self.settings.keyword_provider,
                market=command.request.market or self.settings.keyword_provider_country,
                language=command.request.language or self.settings.keyword_provider_language,
                currency=self.settings.keyword_provider_currency,
                max_keywords=self.settings.keyword_provider_max_keywords,
                batch_size=self.settings.keyword_provider_batch_size,
                cache_ttl_seconds=self.settings.keyword_provider_cache_ttl_seconds,
                scoring_policy_version=self.settings.keyword_scoring_policy_version,
                matching_policy_version=self.settings.keyword_matching_policy_version,
                trend_policy_version=self.settings.keyword_trend_policy_version,
            ),
        )
        warnings.extend(enrichment_result.warnings)
        provider_runs.extend(enrichment_result.telemetry)
        profile = profile.model_copy(
            update={"evidence": [*profile.evidence, *enrichment_result.evidence]}
        )
        candidates = enrichment_result.candidates
        self._complete_stage(
            stages,
            "enrich_keywords",
            (
                "Keyword candidates enriched with provider metrics where available "
                f"({enrichment_result.intelligence.status})."
            ),
        )

        validate_keyword_evidence(profile, candidates)
        clusters = cluster_keywords(candidates)
        self._complete_stage(stages, "cluster_keywords", f"Created {len(clusters)} clusters.")
        self._complete_stage(stages, "score_keywords", "Transparent keyword scores calculated.")

        now = datetime.now(UTC)
        run = PerceptionRun(
            run_id=run_id,
            created_at=now,
            completed_at=now,
            request=command.request,
            images=[image.metadata for image in validated_images],
            product_profile=profile,
            marketplace_snapshot=marketplace_result.snapshot,
            keyword_candidates=candidates,
            keyword_clusters=clusters,
            keyword_intelligence=enrichment_result.intelligence.model_copy(
                update={
                    "clusters": enrichment_result.intelligence.clusters
                    if enrichment_result.intelligence.clusters
                    else [],
                }
            ),
            warnings=warnings,
            errors=[],
            stage_statuses=stages,
            metadata=provider_result.metadata,
            provider_runs=provider_runs,
        )
        await self.repository.save_run(run)
        self._complete_stage(stages, "persist_artifact", "Run artifact written to local storage.")
        LOGGER.info(
            "perception_run_completed",
            extra={
                "run_id": run_id,
                "provider": run.metadata.provider,
                "model": run.metadata.model,
            },
        )
        return run.model_copy(update={"stage_statuses": stages})

    @staticmethod
    def _complete_stage(stages: list[StageStatus], name: str, message: str) -> None:
        now = datetime.now(UTC)
        stages.append(
            StageStatus(
                name=name,
                state=StageState.SUCCEEDED,
                started_at=now,
                completed_at=now,
                message=message,
            )
        )
