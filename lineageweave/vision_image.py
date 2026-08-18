"""Normalize raster images before sending them to the vision model."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps


def normalize_vision_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Decode a raster image, flatten transparency to white, and emit PNG."""
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
    output = BytesIO()
    background.convert("RGB").save(output, format="PNG")
    return output.getvalue(), "image/png"
