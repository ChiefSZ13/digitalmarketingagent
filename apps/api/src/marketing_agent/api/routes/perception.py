"""Product perception API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from starlette import status

from marketing_agent.api.dependencies import get_pipeline, get_repository
from marketing_agent.api.errors import ProblemException
from marketing_agent.api.security import AccessKeyDep, PerceptionRateLimitDep
from marketing_agent.application.commands.analyze_product import (
    AnalyzeProductCommand,
    RawImageInput,
)
from marketing_agent.application.orchestration.perception_pipeline import PerceptionPipeline
from marketing_agent.domain.models.marketplace import (
    MarketplaceListingValidation,
    MarketplaceReviewOverride,
    MarketplaceReviewOverrideInput,
)
from marketing_agent.domain.models.run import PerceptionRun, ProductAnalysisRequest
from marketing_agent.domain.ports.artifact_repository import ArtifactRepository

router = APIRouter(prefix="/api/v1/perception-runs", tags=["perception"])

PipelineDep = Annotated[PerceptionPipeline, Depends(get_pipeline)]
RepositoryDep = Annotated[ArtifactRepository, Depends(get_repository)]


@router.post("", response_model=PerceptionRun, status_code=status.HTTP_201_CREATED)
async def create_perception_run(
    images: Annotated[list[UploadFile], File(description="One to five JPG, PNG, or WebP images")],
    description: Annotated[str, Form(min_length=1)],
    _access_key: AccessKeyDep,
    _rate_limit: PerceptionRateLimitDep,
    pipeline: PipelineDep,
    brand: Annotated[str | None, Form()] = None,
    market: Annotated[str | None, Form()] = None,
    language: Annotated[str | None, Form()] = None,
    category_hint: Annotated[str | None, Form()] = None,
    target_audience_hint: Annotated[str | None, Form()] = None,
    include_debug: Annotated[bool, Form()] = False,
) -> PerceptionRun:
    raw_images = [
        RawImageInput(
            filename=image.filename or f"upload-{index}",
            content_type=image.content_type,
            data=await image.read(),
        )
        for index, image in enumerate(images, start=1)
    ]
    command = AnalyzeProductCommand(
        request=ProductAnalysisRequest(
            description=description.strip(),
            brand=_blank_to_none(brand),
            market=_blank_to_none(market),
            language=_blank_to_none(language),
            category_hint=_blank_to_none(category_hint),
            target_audience_hint=_blank_to_none(target_audience_hint),
            include_debug=include_debug,
        ),
        images=raw_images,
    )
    return await pipeline.analyze(command)


@router.get("/{run_id}", response_model=PerceptionRun)
async def get_perception_run(
    run_id: str,
    _access_key: AccessKeyDep,
    repository: RepositoryDep,
) -> PerceptionRun:
    run = await repository.get_run(run_id)
    if run is None:
        raise ProblemException(
            title="Run not found",
            detail=f"No perception run exists for ID {run_id}.",
            status_code=404,
            type_="https://example.local/errors/not-found",
        )
    overrides = await repository.list_marketplace_overrides(run_id)
    return _with_marketplace_overrides(run, overrides)


@router.post(
    "/{run_id}/marketplace-overrides",
    response_model=MarketplaceReviewOverride,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_marketplace_override(
    run_id: str,
    payload: MarketplaceReviewOverrideInput,
    _access_key: AccessKeyDep,
    repository: RepositoryDep,
) -> MarketplaceReviewOverride:
    run = await repository.get_run(run_id)
    if run is None:
        raise ProblemException(
            title="Run not found",
            detail=f"No perception run exists for ID {run_id}.",
            status_code=404,
            type_="https://example.local/errors/not-found",
        )
    listing_ids = {
        validation.listing.listing_id for validation in run.marketplace_snapshot.validated_listings
    }
    if payload.listing_id not in listing_ids:
        raise ProblemException(
            title="Listing not found",
            detail=f"No marketplace listing exists for ID {payload.listing_id}.",
            status_code=404,
            type_="https://example.local/errors/not-found",
        )
    return await repository.save_marketplace_override(
        MarketplaceReviewOverride(
            run_id=run_id,
            listing_id=payload.listing_id,
            decision=payload.decision,
            note=payload.note,
            reviewer=payload.reviewer,
        )
    )


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _with_marketplace_overrides(
    run: PerceptionRun, overrides: list[MarketplaceReviewOverride]
) -> PerceptionRun:
    overrides_by_listing = {override.listing_id: override for override in overrides}
    validations: list[MarketplaceListingValidation] = []
    for validation in run.marketplace_snapshot.validated_listings:
        validations.append(
            validation.model_copy(
                update={"manual_override": overrides_by_listing.get(validation.listing.listing_id)}
            )
        )
    snapshot = run.marketplace_snapshot.model_copy(
        update={
            "manual_overrides": overrides,
            "validated_listings": validations,
        }
    )
    return run.model_copy(update={"marketplace_snapshot": snapshot})
