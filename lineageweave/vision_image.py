"""Normalize raster images before sending them to the vision model."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps

_MAX_VISION_IMAGE_EDGE = 4096
_MAX_VISION_IMAGE_BYTES = 8 * 1024 * 1024


def _encode_png(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG", optimize=True, compress_level=9)
    return output.getvalue()


def _encode_bounded_jpeg(image: Image.Image) -> bytes:
    quality = 85
    candidate = b""
    while True:
        output = BytesIO()
        image.save(output, format="JPEG", quality=quality, optimize=True)
        candidate = output.getvalue()
        if len(candidate) <= _MAX_VISION_IMAGE_BYTES:
            return candidate
        if quality > 45:
            quality -= 10
            continue
        width = max(1, round(image.width * 0.8))
        height = max(1, round(image.height * 0.8))
        if (width, height) == image.size:
            return candidate
        image = image.resize((width, height), Image.Resampling.LANCZOS)
        quality = 85


def normalize_vision_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Decode a raster image and return a bounded opaque vision payload."""
    del mime_type
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            source.seek(0)
            rgba = ImageOps.exif_transpose(source).convert("RGBA")
            rgba.load()
    except (OSError, ValueError) as exc:
        raise ValueError("unsupported or invalid raster image") from exc

    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    background.alpha_composite(rgba)
    rgb = background.convert("RGB")
    if max(rgb.size) > _MAX_VISION_IMAGE_EDGE:
        rgb.thumbnail((_MAX_VISION_IMAGE_EDGE, _MAX_VISION_IMAGE_EDGE), Image.Resampling.LANCZOS)
    png = _encode_png(rgb)
    if len(png) <= _MAX_VISION_IMAGE_BYTES:
        return png, "image/png"
    return _encode_bounded_jpeg(rgb), "image/jpeg"
