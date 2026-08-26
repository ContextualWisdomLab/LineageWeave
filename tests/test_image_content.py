from __future__ import annotations

import base64

import pytest

from lineageweave.image_content import (
    _REGION_RESPONSE_FORMAT,
    _RESPONSE_FORMAT,
    ImageContentClient,
    ImageDescriptionParseError,
    NullImageContentClient,
    OpenAiCompatibleVisionClient,
    _parse_description,
    extract_base64_images,
    orchestrator_vision_client,
)

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

    # position is a character offset (not an image-only ordinal), so the
    # second image's position must fall strictly after the first image's
    # entire <img> tag AND the "Middle text." paragraph between them --
    # exactly what distinguishes "two images with content between them"
    # from "two images back to back," which an ordinal cannot.
    assert images[0].position < images[1].position
    assert images[1].position >= images[0].position + len(f'<img src="data:image/png;base64,{_TINY_PNG_B64}">') + len(
        "<p>Middle text.</p>"
    )
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


def test_parse_description_unexpected_format_raises_instead_of_losing_content() -> None:
    with pytest.raises(ImageDescriptionParseError):
        _parse_description("unexpected format")


def test_parse_description_preserves_multiline_ocr_text() -> None:
    content = "TEXT: Line one\nLine two\nLine three\nCAPTION: A scanned page.\nTAGS: document, scan"
    description = _parse_description(content)
    assert description.extracted_text == "Line one\nLine two\nLine three"
    assert description.caption == "A scanned page."


def test_parse_description_preserves_table_row_structure_in_ocr_text() -> None:
    """Live gap (2026-08-19): an image containing a table used to have its
    text flattened into an unstructured word list on OCR, the same
    row-grouping loss chunk_by_dom had for real HTML tables. The parser
    already preserves multi-line TEXT (see the sibling test above); this
    confirms a table-shaped response -- one row per line, columns
    delimited by " | " per the response-format prompt -- round-trips intact.
    """
    content = "TEXT: No. | Company | Result\n1 | Acme Corp | Declined\n2 | Globex Corp | Interested\nCAPTION: A visit log table.\nTAGS: table, log"
    description = _parse_description(content)
    assert description.extracted_text == (
        "No. | Company | Result\n1 | Acme Corp | Declined\n2 | Globex Corp | Interested"
    )


def test_parse_description_tolerates_markdown_emphasis_on_labels() -> None:
    """Synthetic provider drift may bold labels without changing content."""
    content = "**TEXT:** LT7\n**CAPTION:** A close-up of a component.\n**TAGS:** component, close-up"
    description = _parse_description(content)
    assert description.extracted_text == "LT7"
    assert description.caption == "A close-up of a component."
    assert description.tags == ("component", "close-up")


def test_parse_description_strips_balanced_markdown_emphasis_from_values() -> None:
    content = "TEXT: **LT7**\nCAPTION: _A synthetic component._\nTAGS: `component`, close-up"
    description = _parse_description(content)
    assert description.extracted_text == "LT7"
    assert description.caption == "A synthetic component."
    assert description.tags == ("component", "close-up")


def test_parse_description_tolerates_reordered_labels() -> None:
    content = "CAPTION: A blue sky.\nTEXT: NONE\nTAGS: sky"
    description = _parse_description(content)
    assert description.caption == "A blue sky."
    assert description.extracted_text == ""
    assert description.tags == ("sky",)


def test_parse_description_missing_tags_still_recovers_text_and_caption() -> None:
    """Missing optional tags must not discard provided TEXT/CAPTION fields."""
    content = "TEXT: Quarterly Budget Report\nCAPTION: A printed report cover page."
    description = _parse_description(content)
    assert description.extracted_text == "Quarterly Budget Report"
    assert description.caption == "A printed report cover page."
    assert description.tags == ()


def test_parse_description_leading_commentary_before_labels_is_ignored() -> None:
    content = "Sure, here is the analysis:\n\nTEXT: LT7\nCAPTION: A component.\nTAGS: component"
    description = _parse_description(content)
    assert description.extracted_text == "LT7"


def test_parse_description_does_not_absorb_trailing_commentary() -> None:
    content = (
        "TEXT: NONE\nCAPTION: A turbine diagram.\nTAGS: turbine, diagram\n"
        "Let me know if you need more detail."
    )
    description = _parse_description(content)
    assert description.caption == "A turbine diagram."
    assert description.tags == ("turbine", "diagram")


def test_vision_client_rejects_non_http_url_schemes() -> None:
    with pytest.raises(ValueError, match="unsupported vision client URL scheme: file"):
        OpenAiCompatibleVisionClient(
            base_url="file:///etc/passwd",
            api_key="unused",
            model="unused",
        )


def test_vision_client_accepts_https_urls_by_default() -> None:
    https_client = OpenAiCompatibleVisionClient(
        base_url="https://gateway.example/v1",
        api_key="unused",
        model="unused",
    )
    assert https_client._base_url == "https://gateway.example/v1"


def test_vision_client_rejects_plain_http_by_default() -> None:
    """A plain-HTTP endpoint sends the Bearer API key and raw images
    unencrypted -- secure by default, explicit opt-in only.
    """
    with pytest.raises(ValueError, match="requires https://"):
        OpenAiCompatibleVisionClient(
            base_url="http://127.0.0.1:8000/v1",
            api_key="unused",
            model="unused",
        )


def test_vision_client_allows_http_with_explicit_insecure_opt_in() -> None:
    http_client = OpenAiCompatibleVisionClient(
        base_url="http://127.0.0.1:8000/v1",
        api_key="unused",
        model="unused",
        allow_insecure_http=True,
    )
    assert http_client._base_url == "http://127.0.0.1:8000/v1"


def test_orchestrator_vision_client_appends_v1_and_allows_local_http() -> None:
    client = orchestrator_vision_client("http://127.0.0.1:8000", "key", "vision-model")
    assert isinstance(client, OpenAiCompatibleVisionClient)
    assert client._base_url == "http://127.0.0.1:8000/v1"


def test_orchestrator_vision_client_does_not_double_v1() -> None:
    client = orchestrator_vision_client("https://gateway.example/v1", "key", "vision-model")
    assert isinstance(client, OpenAiCompatibleVisionClient)
    assert client._base_url == "https://gateway.example/v1"


def test_orchestrator_vision_client_is_null_when_unconfigured() -> None:
    client = orchestrator_vision_client("", "")
    assert isinstance(client, NullImageContentClient)
    assert client.available is False


def test_image_content_client_protocol_stub_raises() -> None:
    """The Protocol method is a real stub, not a no-op ellipsis, so a
    mistaken call cannot be mistaken for a successful empty description.
    """
    with pytest.raises(NotImplementedError):
        ImageContentClient.describe(None, b"", "image/png")  # type: ignore[arg-type]


def test_ocr_prompt_asks_for_table_row_structure() -> None:
    """Live gap (2026-08-19): the OCR prompt had no guidance for a
    table-shaped image, so a real table image had its text flattened into
    an unstructured list -- the same class of bug chunk_by_dom had for
    real HTML tables. The prompt must tell the model to preserve rows.
    """
    assert "row" in _RESPONSE_FORMAT.lower()
    assert "table" in _RESPONSE_FORMAT.lower()


def test_region_prompt_requires_full_image_coverage() -> None:
    """Live gap (2026-08-19): "distinct meaningful visual regions" alone
    let the model describe only the most visually striking part of an
    image and skip the rest, instead of covering the whole DOM/image area.
    """
    assert "entire image" in _REGION_RESPONSE_FORMAT.lower()


def test_parse_description_does_not_absorb_unknown_labels_into_tags() -> None:
    parsed = _parse_description(
        "TEXT: NONE\nCAPTION: A turbine diagram\n"
        "TAGS: turbine, diagram\nNOTE: synthetic"
    )
    assert parsed.tags == ("turbine", "diagram")
