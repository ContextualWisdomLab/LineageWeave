from __future__ import annotations

import base64

from lineageweave.image_content import _parse_description, extract_base64_images

# A 1x1 transparent PNG, valid base64 -- enough to exercise real decoding
# without needing an image library for pure extraction/parsing tests.
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_extract_base64_images_finds_images_in_document_order() -> None:
    html = (
        f'<p>Intro text.</p><img src="data:image/png;base64,{_TINY_PNG_B64}">'
        f'<p>Middle text.</p><img src="data:image/png;base64,{_TINY_PNG_B64}">'
    )
    images = extract_base64_images(html)

    assert [img.position for img in images] == [0, 1]
    assert all(img.mime_type == "image/png" for img in images)
    assert all(img.data == base64.b64decode(_TINY_PNG_B64) for img in images)


def test_extract_base64_images_skips_malformed_base64() -> None:
    html = '<img src="data:image/png;base64,not-valid-base64!!!">'
    assert extract_base64_images(html) == []


def test_extract_base64_images_ignores_non_data_uri_images() -> None:
    html = '<img src="https://example.com/photo.png">'
    assert extract_base64_images(html) == []


def test_extract_base64_images_empty_document_yields_no_images() -> None:
    assert extract_base64_images("<p>No images here.</p>") == []


def test_parse_description_extracts_all_three_fields() -> None:
    content = "TEXT: Quarterly Budget Report\nCAPTION: A printed report cover page.\nTAGS: document, report, text"
    description = _parse_description(content)

    assert description.extracted_text == "Quarterly Budget Report"
    assert description.caption == "A printed report cover page."
    assert description.tags == ("document", "report", "text")


def test_parse_description_none_text_becomes_empty_string() -> None:
    content = "TEXT: NONE\nCAPTION: A blue sky with clouds.\nTAGS: sky, clouds, nature"
    description = _parse_description(content)
    assert description.extracted_text == ""


def test_parse_description_missing_lines_default_to_empty() -> None:
    description = _parse_description("unexpected format")
    assert description.extracted_text == ""
    assert description.caption == ""
    assert description.tags == ()
