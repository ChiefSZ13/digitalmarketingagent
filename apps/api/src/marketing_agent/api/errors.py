"""RFC 7807-style error mapping."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette import status

from marketing_agent.infrastructure.ai.openai_perception_provider import OpenAIProviderError
from marketing_agent.infrastructure.media.image_validation import ImageValidationError


class ProblemDetails(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: str = Field(min_length=1)


class ProblemException(Exception):
    def __init__(self, *, title: str, detail: str, status_code: int, type_: str) -> None:
        self.title = title
        self.detail = detail
        self.status_code = status_code
        self.type_ = type_


def request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def problem_response(
    request: Request,
    *,
    title: str,
    detail: str,
    status_code: int,
    type_: str,
) -> JSONResponse:
    body = ProblemDetails(
        type=type_,
        title=title,
        status=status_code,
        detail=detail,
        instance=str(request.url.path),
        request_id=request_id(request),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


async def problem_exception_handler(request: Request, exc: ProblemException) -> JSONResponse:
    return problem_response(
        request,
        title=exc.title,
        detail=exc.detail,
        status_code=exc.status_code,
        type_=exc.type_,
    )


async def image_validation_exception_handler(
    request: Request,
    exc: ImageValidationError,
) -> JSONResponse:
    type_name = "payload-too-large" if exc.status_code == 413 else "invalid-image"
    if exc.status_code == 415:
        type_name = "unsupported-media-type"
    return problem_response(
        request,
        title=exc.title,
        detail=exc.detail,
        status_code=exc.status_code,
        type_=f"https://example.local/errors/{type_name}",
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return problem_response(
        request,
        title="Invalid request",
        detail=str(exc.errors()[0]["msg"]) if exc.errors() else "The request was invalid.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        type_="https://example.local/errors/validation",
    )


async def provider_exception_handler(request: Request, exc: OpenAIProviderError) -> JSONResponse:
    return problem_response(
        request,
        title="Provider failure",
        detail=str(exc),
        status_code=status.HTTP_502_BAD_GATEWAY,
        type_="https://example.local/errors/provider-failure",
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return problem_response(
        request,
        title="Internal server error",
        detail="An unexpected error occurred while processing the request.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        type_="https://example.local/errors/internal",
    )
