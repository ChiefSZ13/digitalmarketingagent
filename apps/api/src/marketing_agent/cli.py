"""CLI entry point for product analysis."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from marketing_agent.application.commands.analyze_product import (
    AnalyzeProductCommand,
    RawImageInput,
)
from marketing_agent.application.orchestration.perception_pipeline import PerceptionPipeline
from marketing_agent.config import get_settings
from marketing_agent.domain.models.run import ProductAnalysisRequest
from marketing_agent.infrastructure.ai.mock_perception_provider import MockPerceptionProvider
from marketing_agent.infrastructure.ai.openai_perception_provider import OpenAIPerceptionProvider
from marketing_agent.infrastructure.marketplace.mock_marketplace_data_provider import (
    MockMarketplaceDataProvider,
)
from marketing_agent.infrastructure.marketplace.serpapi_marketplace_data_provider import (
    SerpApiMarketplaceDataProvider,
)
from marketing_agent.infrastructure.media.image_validation import content_type_from_path
from marketing_agent.infrastructure.persistence.local_artifact_repository import (
    LocalArtifactRepository,
)

app = typer.Typer(help="Product perception and keyword intelligence CLI.")


@app.callback()
def main() -> None:
    """Run product perception commands."""


@app.command()
def analyze(
    image: Annotated[list[Path], typer.Option("--image", exists=True, readable=True)],
    description: Annotated[str, typer.Option("--description", help="Product description.")],
    output: Annotated[
        Path | None, typer.Option("--output", help="Write JSON to this file.")
    ] = None,
    brand: Annotated[str | None, typer.Option("--brand")] = None,
    market: Annotated[str | None, typer.Option("--market")] = None,
    language: Annotated[str | None, typer.Option("--language")] = None,
    category_hint: Annotated[str | None, typer.Option("--category-hint")] = None,
    target_audience_hint: Annotated[str | None, typer.Option("--target-audience-hint")] = None,
) -> None:
    """Analyze product images and emit a run artifact."""
    result = asyncio.run(
        _analyze(
            image=image,
            description=description,
            output=output,
            brand=brand,
            market=market,
            language=language,
            category_hint=category_hint,
            target_audience_hint=target_audience_hint,
        )
    )
    typer.echo(result)


async def _analyze(
    *,
    image: list[Path],
    description: str,
    output: Path | None,
    brand: str | None,
    market: str | None,
    language: str | None,
    category_hint: str | None,
    target_audience_hint: str | None,
) -> str:
    settings = get_settings()
    provider = (
        OpenAIPerceptionProvider(
            api_key=settings.openai_api_key or "",
            model=settings.openai_model,
            timeout_seconds=settings.perception_timeout_seconds,
        )
        if settings.perception_provider.lower() == "openai"
        else MockPerceptionProvider()
    )
    if settings.perception_provider.lower() == "openai" and not settings.openai_api_key:
        raise typer.BadParameter("OPENAI_API_KEY is required when PERCEPTION_PROVIDER=openai")
    marketplace_provider = (
        SerpApiMarketplaceDataProvider(
            api_key=settings.serpapi_api_key or "",
            timeout_seconds=settings.marketplace_timeout_seconds,
            location=settings.serpapi_location,
        )
        if settings.marketplace_data_provider.lower() == "serpapi"
        else MockMarketplaceDataProvider()
    )
    if settings.marketplace_data_provider.lower() == "serpapi" and not settings.serpapi_api_key:
        raise typer.BadParameter(
            "SERPAPI_API_KEY is required when MARKETPLACE_DATA_PROVIDER=serpapi"
        )
    pipeline = PerceptionPipeline(
        settings=settings,
        provider=provider,
        marketplace_provider=marketplace_provider,
        repository=LocalArtifactRepository(settings.artifact_dir),
    )
    command = AnalyzeProductCommand(
        request=ProductAnalysisRequest(
            description=description,
            brand=brand,
            market=market,
            language=language,
            category_hint=category_hint,
            target_audience_hint=target_audience_hint,
        ),
        images=[
            RawImageInput(
                filename=path.name,
                content_type=content_type_from_path(path),
                data=path.read_bytes(),
            )
            for path in image
        ],
    )
    run = await pipeline.analyze(command)
    json_output = run.model_dump_json(indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json_output, encoding="utf-8")
        return f"Wrote {output}"
    return json_output
