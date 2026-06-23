"""Upload validation and metadata stripping for product images."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from marketing_agent.application.commands.analyze_product import RawImageInput
from marketing_agent.domain.models.run import ImageInput
from marketing_agent.domain.ports.perception_provider import ProviderImage

ALLOWED_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}


class ImageValidationError(ValueError):
    def __init__(self, title: str, detail: str, status_code: int = 422) -> None:
        super().__init__(detail)
        self.title = title
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class ValidatedProviderImage:
    provider_image: ProviderImage
    metadata: ImageInput


def _has_supported_signature(data: bytes) -> bool:
    return (
        data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"\x89PNG\r\n\x1a\n")
        or (data.startswith(b"RIFF") and data[8:12] == b"WEBP")
    )


def _safe_filename(index: int, content_hash: str, extension: str) -> str:
    return f"image-{index}-{content_hash[:12]}{extension}"


def validate_images(
    images: list[RawImageInput],
    *,
    max_images: int,
    max_bytes: int,
    max_pixels: int,
) -> list[ValidatedProviderImage]:
    if not images:
        raise ImageValidationError("Invalid image", "At least one product image is required.")
    if len(images) > max_images:
        raise ImageValidationError(
            "Too many images",
            f"Expected at most {max_images} images, received {len(images)}.",
            status_code=422,
        )

    validated: list[ValidatedProviderImage] = []
    for index, raw in enumerate(images, start=1):
        if len(raw.data) > max_bytes:
            raise ImageValidationError(
                "Payload too large",
                f"Image {index} exceeds the configured {max_bytes} byte limit.",
                status_code=413,
            )
        if not _has_supported_signature(raw.data):
            raise ImageValidationError(
                "Unsupported media type",
                f"Image {index} is not a supported JPEG, PNG, or WebP file.",
                status_code=415,
            )
        try:
            with Image.open(BytesIO(raw.data)) as image:
                image.verify()
            with Image.open(BytesIO(raw.data)) as image:
                image.load()
                width, height = image.size
                if width * height > max_pixels:
                    raise ImageValidationError(
                        "Image too large",
                        f"Image {index} exceeds the configured pixel limit.",
                        status_code=422,
                    )
                if image.format not in ALLOWED_FORMATS:
                    raise ImageValidationError(
                        "Unsupported media type",
                        f"Image {index} is not a supported JPEG, PNG, or WebP file.",
                        status_code=415,
                    )
                mime_type, extension = ALLOWED_FORMATS[image.format]
                sanitized = _strip_metadata(image, image.format)
        except ImageValidationError:
            raise
        except (UnidentifiedImageError, OSError) as exc:
            raise ImageValidationError(
                "Invalid image", f"Image {index} could not be decoded."
            ) from exc

        content_hash = sha256(raw.data).hexdigest()
        metadata = ImageInput(
            index=index,
            filename=_safe_filename(index, content_hash, extension),
            mime_type=mime_type,
            content_hash=content_hash,
            byte_size=len(raw.data),
            width=width,
            height=height,
        )
        validated.append(
            ValidatedProviderImage(
                provider_image=ProviderImage(
                    index=index,
                    mime_type=mime_type,
                    data=sanitized,
                    input=metadata,
                ),
                metadata=metadata,
            )
        )
    return validated


def _strip_metadata(image: Image.Image, image_format: str) -> bytes:
    buffer = BytesIO()
    save_format = image_format
    cleaned = image.copy()
    if image_format == "JPEG" and cleaned.mode not in {"RGB", "L"}:
        cleaned = cleaned.convert("RGB")
    cleaned.save(buffer, format=save_format)
    return buffer.getvalue()


def content_type_from_path(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return None
