"""OpenAI Responses API perception provider."""

import asyncio
import base64
import json
from datetime import UTC, datetime
from importlib.resources import files
from time import perf_counter
from typing import Any, cast

from pydantic import ValidationError

from marketing_agent.domain.models.evidence import (
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.run import ProviderMetadata, ProviderUsage
from marketing_agent.domain.ports.perception_provider import (
    PerceptionProviderRequest,
    ProviderPerceptionResult,
)

PROMPT_VERSION = "perception_v1"


class OpenAIProviderError(RuntimeError):
    """Raised for live provider failures."""


class OpenAIPerceptionProvider:
    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def analyze(self, request: PerceptionProviderRequest) -> ProviderPerceptionResult:
        from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, timeout=self.timeout_seconds, max_retries=0)
        prompt = _read_prompt()
        schema = _to_openai_strict_json_schema(ProductProfile.model_json_schema())
        payload = _build_payload(request)
        last_error: Exception | None = None
        started = perf_counter()
        response = None
        for attempt in range(2):
            content = [{"type": "input_text", "text": _build_text(prompt, payload, attempt)}]
            content.extend(_image_content(request))
            try:
                response = await client.responses.create(
                    model=self.model,
                    input=cast(Any, [{"role": "user", "content": content}]),
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "product_profile",
                            "schema": schema,
                            "strict": True,
                        }
                    },
                    temperature=0.1,
                )
                profile = ProductProfile.model_validate_json(response.output_text)
                profile, evidence_warnings = _ensure_declared_evidence(profile)
                latency_ms = int((perf_counter() - started) * 1000)
                return ProviderPerceptionResult(
                    product_profile=profile,
                    metadata=ProviderMetadata(
                        provider="openai",
                        model=self.model,
                        request_id=getattr(response, "id", None),
                        latency_ms=latency_ms,
                        prompt_version=PROMPT_VERSION,
                        usage=_usage(response),
                    ),
                    warnings=evidence_warnings,
                )
            except ValidationError as exc:
                last_error = exc
                continue
            except (APITimeoutError, APIConnectionError) as exc:
                last_error = exc
                await asyncio.sleep(0.4 * (attempt + 1))
            except APIStatusError as exc:
                if exc.status_code in {408, 409, 429, 500, 502, 503, 504} and attempt == 0:
                    last_error = exc
                    await asyncio.sleep(0.4)
                    continue
                raise OpenAIProviderError(
                    f"OpenAI provider returned status {exc.status_code}: "
                    f"{_status_error_detail(exc)}"
                ) from exc
        raise OpenAIProviderError("OpenAI provider returned schema-invalid output") from last_error


def _read_prompt() -> str:
    prompt_file = files("marketing_agent.infrastructure.ai.prompts").joinpath("perception_v1.md")
    return prompt_file.read_text(encoding="utf-8")


def _build_payload(request: PerceptionProviderRequest) -> str:
    return json.dumps(
        {
            "description": request.request.description,
            "brand": request.request.brand,
            "market": request.request.market,
            "language": request.request.language,
            "category_hint": request.request.category_hint,
            "target_audience_hint": request.request.target_audience_hint,
            "images": [image.input.model_dump(mode="json") for image in request.images],
        },
        ensure_ascii=True,
    )


def _build_text(prompt: str, payload: str, attempt: int) -> str:
    repair = ""
    if attempt == 1:
        repair = "\nPrevious output failed schema validation. Return corrected JSON only."
    return f"{prompt}{repair}\n\nInput JSON:\n{payload}"


def _image_content(request: PerceptionProviderRequest) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for image in request.images:
        encoded = base64.b64encode(image.data).decode("ascii")
        items.append(
            {
                "type": "input_image",
                "image_url": f"data:{image.mime_type};base64,{encoded}",
                "detail": "auto",
            }
        )
    return items


def _to_openai_strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert Pydantic JSON Schema into OpenAI's strict structured-output subset."""
    strict_schema = cast(dict[str, object], dict(schema))
    _make_objects_strict(strict_schema)
    return cast(dict[str, Any], strict_schema)


def _status_error_detail(exc: object) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return "No response body was returned."
    text = getattr(response, "text", "")
    if not isinstance(text, str) or not text.strip():
        return "No response body was returned."
    return text.strip()[:1000]


def _make_objects_strict(value: object) -> None:
    if isinstance(value, dict):
        schema_object = cast(dict[str, object], value)
        properties_value = schema_object.get("properties")
        if isinstance(properties_value, dict):
            properties = cast(dict[str, object], properties_value)
            schema_object["required"] = list(properties.keys())
            schema_object.setdefault("additionalProperties", False)
        schema_object.pop("default", None)
        for child in list(schema_object.values()):
            _make_objects_strict(child)
    elif isinstance(value, list):
        for child in cast(list[object], value):
            _make_objects_strict(child)


def _ensure_declared_evidence(profile: ProductProfile) -> tuple[ProductProfile, list[str]]:
    declared_ids = {record.id for record in profile.evidence}
    missing_ids = sorted(_referenced_evidence_ids(profile).difference(declared_ids))
    if not missing_ids:
        return profile, []

    created_at = datetime.now(UTC)
    repaired_evidence = [
        EvidenceRecord(
            id=evidence_id,
            source=EvidenceSource.MODEL_INFERENCE,
            source_reference="openai_provider_evidence_repair",
            observation=(
                f"OpenAI response cited undeclared evidence ID '{evidence_id}'. "
                "The ID was retained and labeled as model inference for explicit coverage."
            ),
            quote=None,
            confidence=0.35,
            created_at=created_at,
        )
        for evidence_id in missing_ids
    ]
    warning = (
        "OpenAI response referenced undeclared evidence IDs; added model-inference "
        f"evidence records for: {', '.join(missing_ids)}."
    )
    repaired_profile = profile.model_copy(
        update={"evidence": [*profile.evidence, *repaired_evidence]}
    )
    return repaired_profile, [warning]


def _referenced_evidence_ids(profile: ProductProfile) -> set[str]:
    referenced: set[str] = set()
    linked_items: list[EvidenceLinkedText] = []
    for field_name in (
        "product_name",
        "brand",
        "category",
        "subcategory",
        "summary",
    ):
        value = getattr(profile, field_name)
        if isinstance(value, EvidenceLinkedText):
            linked_items.append(value)
    for field_name in (
        "visual_attributes",
        "observed_facts",
        "user_provided_facts",
        "inferred_attributes",
        "features",
        "benefits",
        "materials",
        "colors",
        "use_cases",
        "target_audiences",
        "differentiators",
        "limitations",
        "ambiguities",
        "unknowns",
    ):
        linked_items.extend(cast(list[EvidenceLinkedText], getattr(profile, field_name)))
    for item in linked_items:
        referenced.update(item.evidence_ids)
    for flag in profile.unsafe_or_unverified_claims + profile.claim_flags:
        referenced.update(flag.evidence_ids)
    return referenced


def _usage(response: object) -> ProviderUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return ProviderUsage(
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )
