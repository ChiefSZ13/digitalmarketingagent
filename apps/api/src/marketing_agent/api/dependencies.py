"""FastAPI dependency construction."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from marketing_agent.application.orchestration.perception_pipeline import PerceptionPipeline
from marketing_agent.config import Settings, get_settings
from marketing_agent.domain.ports.artifact_repository import ArtifactRepository
from marketing_agent.domain.ports.marketplace_data_provider import MarketplaceDataProvider
from marketing_agent.domain.ports.perception_provider import PerceptionProvider
from marketing_agent.domain.services.product_matcher import ProductMatcherConfig
from marketing_agent.infrastructure.ai.mock_perception_provider import MockPerceptionProvider
from marketing_agent.infrastructure.ai.openai_perception_provider import OpenAIPerceptionProvider
from marketing_agent.infrastructure.marketplace.mock_marketplace_data_provider import (
    MockMarketplaceDataProvider,
)
from marketing_agent.infrastructure.marketplace.serpapi_marketplace_data_provider import (
    SerpApiMarketplaceDataProvider,
)
from marketing_agent.infrastructure.persistence.local_artifact_repository import (
    LocalArtifactRepository,
)


@lru_cache
def get_repository_cached(artifact_dir: str) -> LocalArtifactRepository:
    from pathlib import Path

    return LocalArtifactRepository(Path(artifact_dir))


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_repository(settings: SettingsDep) -> ArtifactRepository:
    return get_repository_cached(str(settings.artifact_dir))


def get_provider(settings: SettingsDep) -> PerceptionProvider:
    if settings.perception_provider.lower() == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when PERCEPTION_PROVIDER=openai")
        return OpenAIPerceptionProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout_seconds=settings.perception_timeout_seconds,
        )
    return MockPerceptionProvider()


def get_marketplace_provider(settings: SettingsDep) -> MarketplaceDataProvider:
    matcher_config = ProductMatcherConfig(
        matcher_version=settings.product_matcher_version,
        exact_threshold=settings.product_match_exact_threshold,
        probable_threshold=settings.product_match_probable_threshold,
        uncertain_threshold=settings.product_match_uncertain_threshold,
        require_brand=settings.product_match_require_brand,
        color_strict=settings.product_match_color_strict,
        exclude_refurbished=settings.product_match_exclude_refurbished,
        exclude_used=settings.product_match_exclude_used,
    )
    if settings.marketplace_data_provider.lower() == "serpapi":
        if not settings.serpapi_api_key:
            raise RuntimeError("SERPAPI_API_KEY is required when MARKETPLACE_DATA_PROVIDER=serpapi")
        return SerpApiMarketplaceDataProvider(
            api_key=settings.serpapi_api_key,
            timeout_seconds=settings.marketplace_timeout_seconds,
            location=settings.serpapi_location,
            matcher_config=matcher_config,
        )
    return MockMarketplaceDataProvider(matcher_config=matcher_config)


def get_pipeline(
    settings: SettingsDep,
    provider: Annotated[PerceptionProvider, Depends(get_provider)],
    marketplace_provider: Annotated[MarketplaceDataProvider, Depends(get_marketplace_provider)],
    repository: Annotated[ArtifactRepository, Depends(get_repository)],
) -> PerceptionPipeline:
    return PerceptionPipeline(
        settings=settings,
        provider=provider,
        marketplace_provider=marketplace_provider,
        repository=repository,
    )
