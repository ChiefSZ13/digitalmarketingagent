"""Product perception API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from starlette import status

from marketing_agent.api.dependencies import get_pipeline, get_repository
from marketing_agent.api.errors import ProblemException
from marketing_agent.application.commands.analyze_product import (
    AnalyzeProductCommand,
    RawImageInput,
)
from marketing_agent.application.orchestration.perception_pipeline import PerceptionPipeline
from marketing_agent.domain.models.run import PerceptionRun, ProductAnalysisRequest
from marketing_agent.domain.ports.artifact_repository import ArtifactRepository

router = APIRouter(prefix="/api/v1/perception-runs", tags=["perception"])

PipelineDep = Annotated[PerceptionPipeline, Depends(get_pipeline)]
RepositoryDep = Annotated[ArtifactRepository, Depends(get_repository)]


@router.post("", response_model=PerceptionRun, status_code=status.HTTP_201_CREATED)
async def create_perception_run(
    images: Annotated[list[UploadFile], File(description="One to five JPG, PNG, or WebP images")],
    description: Annotated[str, Form(min_length=1)],
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
    return run


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
