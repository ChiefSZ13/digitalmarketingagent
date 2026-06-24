"""FastAPI application factory."""

from collections.abc import Awaitable, Callable
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ExceptionHandler

from marketing_agent.api.errors import (
    ProblemException,
    generic_exception_handler,
    image_validation_exception_handler,
    marketplace_provider_exception_handler,
    problem_exception_handler,
    provider_exception_handler,
    request_validation_exception_handler,
)
from marketing_agent.api.routes.health import router as health_router
from marketing_agent.api.routes.perception import router as perception_router
from marketing_agent.config import get_settings
from marketing_agent.domain.ports.marketplace_data_provider import MarketplaceDataProviderError
from marketing_agent.infrastructure.ai.openai_perception_provider import OpenAIProviderError
from marketing_agent.infrastructure.media.image_validation import ImageValidationError
from marketing_agent.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_log_level)
    app = FastAPI(
        title="Product Perception and Keyword Intelligence API",
        version="0.1.0",
        openapi_version="3.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", f"req_{uuid4().hex}")
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    app.include_router(health_router)
    app.include_router(perception_router)
    _ = add_request_id
    app.add_exception_handler(ProblemException, cast(ExceptionHandler, problem_exception_handler))
    app.add_exception_handler(
        ImageValidationError,
        cast(ExceptionHandler, image_validation_exception_handler),
    )
    app.add_exception_handler(
        OpenAIProviderError, cast(ExceptionHandler, provider_exception_handler)
    )
    app.add_exception_handler(
        MarketplaceDataProviderError,
        cast(ExceptionHandler, marketplace_provider_exception_handler),
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandler, request_validation_exception_handler),
    )
    app.add_exception_handler(Exception, cast(ExceptionHandler, generic_exception_handler))
    return app


app = create_app()
