from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from lineageweave.vision_image import normalize_vision_image


def _encoded_image(image: Image.Image, image_format: str) -> bytes:
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def test_normalize_vision_image_flattens_transparent_png_to_white() -> None:
    image = Image.new("RGBA", (2, 1), (255, 0, 0, 0))
    image.putpixel((1, 0), (255, 0, 0, 255))

    normalized, mime_type = normalize_vision_image(_encoded_image(image, "PNG"), "image/png")

    with Image.open(BytesIO(normalized)) as result:
        assert mime_type == "image/png"
        assert result.mode == "RGB"
        assert result.getpixel((0, 0)) == (255, 255, 255)
        assert result.getpixel((1, 0)) == (255, 0, 0)


def test_normalize_vision_image_converts_jpeg_to_png() -> None:
    normalized, mime_type = normalize_vision_image(
        _encoded_image(Image.new("RGB", (1, 1), "blue"), "JPEG"), "image/jpeg"
    )

    with Image.open(BytesIO(normalized)) as result:
        assert mime_type == "image/png"
        assert result.format == "PNG"


def test_normalize_vision_image_rejects_invalid_bytes() -> None:
    with pytest.raises(ValueError, match="unsupported or invalid"):
        normalize_vision_image(b"not-an-image", "image/png")
