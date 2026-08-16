from __future__ import annotations

import base64

from lineageweave.embedded_image_payload import (
    decode_data_uri_image,
    looks_like_raster_image,
    source_offset,
)

_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_TINY_PNG = base64.b64decode(_TINY_PNG_B64)


def test_looks_like_raster_image_accepts_png_signature() -> None:
    assert looks_like_raster_image("image/png", _TINY_PNG) is True


def test_looks_like_raster_image_rejects_ascii_labeled_as_png() -> None:
    assert looks_like_raster_image("image/png", b"Hello") is False


def test_decode_data_uri_image_rejects_svg_and_remote_src() -> None:
    assert decode_data_uri_image("https://example.test/invoice.png") is None
    assert (
        decode_data_uri_image(
            "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjwvc3ZnPg=="
        )
        is None
    )


def test_decode_data_uri_image_accepts_newlines_inside_png_payload() -> None:
    wrapped = f"data:image/png;base64,{_TINY_PNG_B64[:24]}\n{_TINY_PNG_B64[24:]}"
    decoded = decode_data_uri_image(wrapped)
    assert decoded == ("image/png", _TINY_PNG)


def test_source_offset_maps_htmlparser_getpos() -> None:
    source = "ab\ncd"
    assert source_offset(source, 1, 0) == 0
    assert source_offset(source, 2, 1) == 4
