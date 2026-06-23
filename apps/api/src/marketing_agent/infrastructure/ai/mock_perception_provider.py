"""Deterministic perception provider for offline development and tests."""

import re
from datetime import UTC, datetime

from marketing_agent.domain.models.evidence import (
    ClaimFlag,
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.models.run import ProviderMetadata
from marketing_agent.domain.ports.perception_provider import (
    PerceptionProviderRequest,
    ProviderPerceptionResult,
)

PROMPT_VERSION = "perception_v1"


class MockPerceptionProvider:
    async def analyze(self, request: PerceptionProviderRequest) -> ProviderPerceptionResult:
        now = datetime.now(UTC)
        analysis = request.request
        evidence = [
            EvidenceRecord(
                id="ev-description-1",
                source=EvidenceSource.USER_DESCRIPTION,
                source_reference="description",
                observation="User supplied the product description.",
                quote=analysis.description[:500],
                confidence=0.95,
                created_at=now,
            )
        ]
        if analysis.brand:
            evidence.append(
                EvidenceRecord(
                    id="ev-metadata-brand",
                    source=EvidenceSource.USER_METADATA,
                    source_reference="brand",
                    observation="User supplied a brand name.",
                    quote=analysis.brand,
                    confidence=0.95,
                    created_at=now,
                )
            )
        if analysis.category_hint:
            evidence.append(
                EvidenceRecord(
                    id="ev-metadata-category",
                    source=EvidenceSource.USER_METADATA,
                    source_reference="category_hint",
                    observation="User supplied a category hint.",
                    quote=analysis.category_hint,
                    confidence=0.9,
                    created_at=now,
                )
            )
        if analysis.target_audience_hint:
            evidence.append(
                EvidenceRecord(
                    id="ev-metadata-audience",
                    source=EvidenceSource.USER_METADATA,
                    source_reference="target_audience_hint",
                    observation="User supplied a target audience hint.",
                    quote=analysis.target_audience_hint,
                    confidence=0.9,
                    created_at=now,
                )
            )
        for image in request.images:
            evidence.append(
                EvidenceRecord(
                    id=f"ev-image-{image.index}",
                    source=EvidenceSource.IMAGE_OBSERVATION,
                    source_reference=f"image:{image.index}",
                    observation=(
                        f"Image {image.index} is a decodable {image.mime_type} file with "
                        f"{image.input.width}x{image.input.height} pixels."
                    ),
                    confidence=0.88,
                    created_at=now,
                )
            )
        evidence.append(
            EvidenceRecord(
                id="ev-inference-1",
                source=EvidenceSource.MODEL_INFERENCE,
                source_reference="mock_provider",
                observation=(
                    "Mock provider derived safe product attributes from supplied text only."
                ),
                confidence=0.72,
                created_at=now,
            )
        )

        product_name = _derive_product_name(analysis.description, analysis.category_hint)
        category = analysis.category_hint or _derive_category(analysis.description)
        feature_text = _derive_feature(analysis.description)
        benefit_text = _derive_benefit(analysis.description)
        use_case = _derive_use_case(analysis.description)
        audience = analysis.target_audience_hint or "buyers researching the product category"
        image_evidence_ids = [f"ev-image-{image.index}" for image in request.images]

        brand = (
            EvidenceLinkedText(
                value=analysis.brand, evidence_ids=["ev-metadata-brand"], confidence=0.95
            )
            if analysis.brand
            else None
        )
        category_evidence = (
            ["ev-metadata-category"] if analysis.category_hint else ["ev-inference-1"]
        )
        flags = _claim_flags(analysis.description)
        profile = ProductProfile(
            product_name=EvidenceLinkedText(
                value=product_name,
                evidence_ids=["ev-description-1", "ev-inference-1"],
                confidence=0.74,
            ),
            brand=brand,
            category=EvidenceLinkedText(
                value=category, evidence_ids=category_evidence, confidence=0.78
            ),
            subcategory=None,
            summary=EvidenceLinkedText(
                value=f"{product_name} positioned for {use_case}.",
                evidence_ids=["ev-description-1", "ev-inference-1"],
                confidence=0.72,
            ),
            visual_attributes=[
                EvidenceLinkedText(
                    value=f"{len(request.images)} validated product image(s) supplied",
                    evidence_ids=image_evidence_ids,
                    confidence=0.88,
                )
            ],
            observed_facts=[
                EvidenceLinkedText(
                    value=f"Image set contains {len(request.images)} supported upload(s)",
                    evidence_ids=image_evidence_ids,
                    confidence=0.88,
                )
            ],
            user_provided_facts=[
                EvidenceLinkedText(
                    value=analysis.description.strip(),
                    evidence_ids=["ev-description-1"],
                    confidence=0.95,
                )
            ],
            inferred_attributes=[
                EvidenceLinkedText(
                    value=f"Likely belongs in {category}",
                    evidence_ids=category_evidence,
                    confidence=0.68,
                )
            ],
            features=[
                EvidenceLinkedText(
                    value=feature_text,
                    evidence_ids=["ev-description-1"],
                    confidence=0.76,
                )
            ],
            benefits=[
                EvidenceLinkedText(
                    value=benefit_text,
                    evidence_ids=["ev-description-1", "ev-inference-1"],
                    confidence=0.7,
                )
            ],
            materials=[],
            colors=[],
            use_cases=[
                EvidenceLinkedText(
                    value=use_case,
                    evidence_ids=["ev-description-1", "ev-inference-1"],
                    confidence=0.72,
                )
            ],
            target_audiences=[
                EvidenceLinkedText(
                    value=audience,
                    evidence_ids=["ev-metadata-audience"]
                    if analysis.target_audience_hint
                    else ["ev-inference-1"],
                    confidence=0.72 if not analysis.target_audience_hint else 0.9,
                )
            ],
            differentiators=[
                EvidenceLinkedText(
                    value=feature_text,
                    evidence_ids=["ev-description-1"],
                    confidence=0.68,
                )
            ],
            limitations=[
                EvidenceLinkedText(
                    value="No live market metrics or third-party keyword data were used.",
                    evidence_ids=["ev-inference-1"],
                    confidence=1.0,
                )
            ],
            ambiguities=[
                EvidenceLinkedText(
                    value=(
                        "Mock analysis does not make factual visual claims beyond "
                        "upload properties."
                    ),
                    evidence_ids=image_evidence_ids,
                    confidence=0.86,
                )
            ],
            unknowns=[
                EvidenceLinkedText(
                    value=(
                        "Exact dimensions, certifications, warranty, and performance are unknown "
                        "unless supplied."
                    ),
                    evidence_ids=["ev-inference-1"],
                    confidence=1.0,
                )
            ],
            unsafe_or_unverified_claims=flags,
            claim_flags=flags,
            evidence=evidence,
            overall_confidence=0.76,
        )
        return ProviderPerceptionResult(
            product_profile=profile,
            metadata=ProviderMetadata(
                provider="mock",
                model="deterministic-fixture",
                request_id=None,
                latency_ms=0,
                prompt_version=PROMPT_VERSION,
                usage=None,
            ),
            warnings=[
                "Mock provider used; visual product attributes are intentionally conservative."
            ],
        )


def _derive_product_name(description: str, category_hint: str | None) -> str:
    text = re.sub(r"[^A-Za-z0-9\s-]", " ", description).strip()
    words = [word for word in text.split() if len(word) > 2][:5]
    if words:
        return " ".join(words).title()
    return (category_hint or "Product").title()


def _derive_category(description: str) -> str:
    lowered = description.lower()
    if "lamp" in lowered or "light" in lowered:
        return "Lighting"
    if "bag" in lowered or "backpack" in lowered:
        return "Bags"
    if "bottle" in lowered or "cup" in lowered:
        return "Drinkware"
    if "skin" in lowered or "serum" in lowered:
        return "Personal care"
    return "Consumer product"


def _derive_feature(description: str) -> str:
    lowered = description.lower()
    for term in ("rechargeable", "portable", "foldable", "wireless", "water-resistant"):
        if term in lowered:
            return term
    words = [word for word in re.sub(r"[^A-Za-z0-9\s-]", " ", description).split() if len(word) > 4]
    return words[0].lower() if words else "general-purpose"


def _derive_benefit(description: str) -> str:
    lowered = description.lower()
    if "portable" in lowered:
        return "easy to move and position"
    if "rechargeable" in lowered:
        return "supports cordless use when charged"
    return "helps shoppers evaluate fit for their needs"


def _derive_use_case(description: str) -> str:
    lowered = description.lower()
    if "desk" in lowered:
        return "desk setup"
    if "travel" in lowered:
        return "travel"
    if "office" in lowered:
        return "office work"
    return "everyday use"


def _claim_flags(description: str) -> list[ClaimFlag]:
    risky_tokens = (
        "certified",
        "cures",
        "medical",
        "guaranteed",
        "waterproof",
        "clinically proven",
    )
    flags: list[ClaimFlag] = []
    lowered = description.lower()
    for token in risky_tokens:
        if token in lowered:
            flags.append(
                ClaimFlag(
                    claim=token,
                    reason="The description contains a claim that requires external verification.",
                    severity="warning",
                    evidence_ids=["ev-description-1"],
                )
            )
    return flags
