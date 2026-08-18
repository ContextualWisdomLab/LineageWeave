from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from lineageweave.vision_image import normalize_vision_image


@pytest.mark.parametrize("image_format", ["BMP", "TIFF"])
def test_decodable_raster_formats_are_emitted_as_png(image_format: str) -> None:
    source = Image.new("RGB", (2, 1), (12, 34, 56))
    encoded = BytesIO()
    source.save(encoded, format=image_format)

    normalized, mime_type = normalize_vision_image(encoded.getvalue(), f"image/{image_format.lower()}")

    assert mime_type == "image/png"
    with Image.open(BytesIO(normalized)) as output:
        assert output.format == "PNG"
        assert output.mode == "RGB"
        assert output.size == (2, 1)
        assert output.getpixel((0, 0)) == (12, 34, 56)


def test_transparent_raster_pixels_are_composited_to_white() -> None:
    source = Image.new("RGBA", (2, 1), (255, 0, 0, 0))
    source.putpixel((1, 0), (0, 0, 255, 255))
    encoded = BytesIO()
    source.save(encoded, format="TIFF")

    normalized, _mime_type = normalize_vision_image(encoded.getvalue(), "image/tiff")

    with Image.open(BytesIO(normalized)) as output:
        assert output.mode == "RGB"
        assert output.getpixel((0, 0)) == (255, 255, 255)
        assert output.getpixel((1, 0)) == (0, 0, 255)
