import pytest

from marketing_agent.application.commands.analyze_product import RawImageInput
from marketing_agent.infrastructure.media.image_validation import (
    ImageValidationError,
    validate_images,
)
from tests.conftest import make_png_bytes


def test_rejects_wrong_signature() -> None:
    with pytest.raises(ImageValidationError) as exc:
        validate_images(
            [RawImageInput(filename="bad.jpg", content_type="image/jpeg", data=b"not an image")],
            max_images=5,
            max_bytes=1024,
            max_pixels=1000,
        )
    assert exc.value.status_code == 415


def test_rejects_too_many_images() -> None:
    image = RawImageInput(filename="ok.png", content_type="image/png", data=make_png_bytes())
    with pytest.raises(ImageValidationError):
        validate_images([image] * 6, max_images=5, max_bytes=1024, max_pixels=1000)


def test_rejects_too_large_image_bytes() -> None:
    image = RawImageInput(filename="ok.png", content_type="image/png", data=make_png_bytes())
    with pytest.raises(ImageValidationError) as exc:
        validate_images([image], max_images=5, max_bytes=10, max_pixels=1000)
    assert exc.value.status_code == 413
