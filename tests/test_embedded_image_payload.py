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
_JPEG_BYTES = b"\xff\xd8\xff\x00"
_GIF87_BYTES = b"GIF87a" + b"\x00" * 2
_GIF89_BYTES = b"GIF89a" + b"\x00" * 2
_WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP"
_AVIF_BYTES = b"\x00\x00\x00\x00ftypavif\x00\x00\x00\x00"
_AVIS_BYTES = b"\x00\x00\x00\x00ftypavis\x00\x00\x00\x00"
_MIF1_BYTES = b"\x00\x00\x00\x00ftypmif1\x00\x00\x00\x00"


def test_looks_like_raster_image_accepts_png_signature() -> None:
    assert looks_like_raster_image("image/png", _TINY_PNG) is True


def test_looks_like_raster_image_rejects_ascii_labeled_as_png() -> None:
    assert looks_like_raster_image("image/png", b"Hello") is False


def test_looks_like_raster_image_rejects_empty_payload() -> None:
    assert looks_like_raster_image("image/png", b"") is False


def test_looks_like_raster_image_accepts_jpeg_gif_webp_avif_signatures() -> None:
    assert looks_like_raster_image("image/jpeg", _JPEG_BYTES) is True
    assert looks_like_raster_image("image/jpg", _JPEG_BYTES) is True
    assert looks_like_raster_image("image/gif", _GIF87_BYTES) is True
    assert looks_like_raster_image("image/gif", _GIF89_BYTES) is True
    assert looks_like_raster_image("image/webp", _WEBP_BYTES) is True
    assert looks_like_raster_image("image/avif", _AVIF_BYTES) is True
    assert looks_like_raster_image("image/avif", _AVIS_BYTES) is True
    assert looks_like_raster_image("image/avif", _MIF1_BYTES) is True


def test_looks_like_raster_image_rejects_wrong_magic_and_unknown_type() -> None:
    assert looks_like_raster_image("image/jpeg", b"not-a-jpeg") is False
    assert looks_like_raster_image("image/gif", b"GIF8xa") is False
    assert looks_like_raster_image("image/webp", b"RIFF....NOTW") is False
    assert looks_like_raster_image("image/webp", b"RIFF") is False
    assert looks_like_raster_image("image/avif", b"xxxxftypxxxx") is False
    assert looks_like_raster_image("image/avif", b"short") is False
    assert looks_like_raster_image("image/svg+xml", _TINY_PNG) is False


def test_decode_data_uri_image_rejects_svg_and_remote_src() -> None:
    assert decode_data_uri_image("https://example.test/invoice.png") is None
    assert (
        decode_data_uri_image(
            "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjwvc3ZnPg=="
        )
        is None
    )


def test_decode_data_uri_image_rejects_missing_comma_or_base64_marker() -> None:
    assert decode_data_uri_image("data:image/png;base64") is None
    assert decode_data_uri_image(f"data:image/png,{_TINY_PNG_B64}") is None


def test_decode_data_uri_image_rejects_unpadded_and_wrong_magic() -> None:
    assert decode_data_uri_image("data:image/png;base64,YQ") is None
    assert decode_data_uri_image("data:image/png;base64,AAAA") is None


def test_decode_data_uri_image_accepts_newlines_inside_png_payload() -> None:
    wrapped = f"data:image/png;base64,{_TINY_PNG_B64[:24]}\n{_TINY_PNG_B64[24:]}"
    decoded = decode_data_uri_image(wrapped)
    assert decoded == ("image/png", _TINY_PNG)


def test_decode_data_uri_image_accepts_jpeg_alias() -> None:
    encoded = base64.b64encode(_JPEG_BYTES).decode("ascii")
    assert decode_data_uri_image(f"data:image/jpg;base64,{encoded}") == (
        "image/jpg",
        _JPEG_BYTES,
    )


def test_decode_data_uri_image_accepts_gif_webp_and_avif() -> None:
    for mime_type, payload in (
        ("image/gif", _GIF89_BYTES),
        ("image/webp", _WEBP_BYTES),
        ("image/avif", _AVIF_BYTES),
    ):
        encoded = base64.b64encode(payload).decode("ascii")
        assert decode_data_uri_image(f"data:{mime_type};base64,{encoded}") == (
            mime_type,
            payload,
        )


def test_source_offset_maps_htmlparser_getpos() -> None:
    source = "ab\ncd"
    assert source_offset(source, 1, 0) == 0
    assert source_offset(source, 2, 1) == 4
    assert source_offset(source, 0, 0) == 0
    assert source_offset(source, 9, 0) == len(source)
