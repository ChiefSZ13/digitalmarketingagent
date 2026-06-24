"""Evidence models shared by perception and keyword intelligence."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceSource(StrEnum):
    USER_DESCRIPTION = "user_description"
    USER_METADATA = "user_metadata"
    IMAGE_OBSERVATION = "image_observation"
    MODEL_INFERENCE = "model_inference"
    KEYWORD_PROVIDER = "keyword_provider"
    MARKETPLACE_PROVIDER = "marketplace_provider"


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=3)
    source: EvidenceSource
    source_reference: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    quote: str | None = Field(default=None, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceLinkedText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class ClaimFlag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    severity: str = Field(default="warning", pattern="^(info|warning|blocker)$")
    evidence_ids: list[str] = Field(default_factory=list)
