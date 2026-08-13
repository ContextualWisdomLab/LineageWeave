"""Tests for lineageweave.post_content_normalization.

A fake vision client (no network) proves the wiring end to end without
needing a real provider; the real-provider round trip through
OpenAiCompatibleVisionClient is already covered by
tests/test_image_content.py and does not need re-proving here.
"""

from __future__ import annotations

import base64

from lineageweave.image_content import ImageDescription
from lineageweave.post_content_normalization import normalize_post_body

_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class _FakeVisionClient:
    available = True

    def __init__(self, description: ImageDescription) -> None:
        self._description = description

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription:
        return self._description


class _FailingVisionClient:
    available = True

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription:
        raise RuntimeError("provider is down")


def test_plain_text_passes_through_unchanged() -> None:
    result = normalize_post_body("Just a plain business record, no markup here.")
    assert result.text == "Just a plain business record, no markup here."
    assert result.formatting_hints == ()
    assert result.image_descriptions == ()


def test_html_tags_never_appear_in_the_normalized_text() -> None:
    html = '<div style="color:red"><p>Confirm delivery by Friday.</p></div>'
    result = normalize_post_body(html)
    assert "style" not in result.text
    assert "<p>" not in result.text
    assert "<div" not in result.text
    assert "Confirm delivery by Friday." in result.text


def test_formatting_hints_are_captured_separately_from_text() -> None:
    html = '<h2 style="color:red">Urgent</h2><p>Please review the attached quote.</p>'
    result = normalize_post_body(html)

    assert len(result.formatting_hints) == 1
    assert result.formatting_hints[0].tag == "h2"
    assert result.formatting_hints[0].style == "color:red"
    assert "color:red" not in result.text


def test_image_is_described_and_placed_at_its_document_position_not_dropped() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    html = f'<p>Before the image.</p><img src="data:image/png;base64,{b64}"/><p>After the image.</p>'
    description = ImageDescription(
        extracted_text="Q3 2026", caption="a bar chart of quarterly revenue", tags=("chart", "revenue")
    )
    result = normalize_post_body(html, vision_client=_FakeVisionClient(description))

    assert "Before the image." in result.text
    assert "a bar chart of quarterly revenue" in result.text
    assert "After the image." in result.text
    # Document order is preserved, not just "somewhere in the text."
    before_index = result.text.index("Before the image.")
    image_index = result.text.index("bar chart")
    after_index = result.text.index("After the image.")
    assert before_index < image_index < after_index
    assert result.image_descriptions == (description,)


def test_image_gets_an_explicit_placeholder_when_no_vision_client_is_available() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    html = f'<img src="data:image/png;base64,{b64}"/>'
    result = normalize_post_body(html)  # default: NullImageContentClient
    assert "[image: content unavailable]" in result.text
    assert result.image_descriptions == ()


def test_a_failed_vision_call_does_not_drop_the_rest_of_the_post() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    html = f'<p>Before.</p><img src="data:image/png;base64,{b64}"/><p>After.</p>'
    result = normalize_post_body(html, vision_client=_FailingVisionClient())
    assert "Before." in result.text
    assert "After." in result.text
    assert "[image: content unavailable]" in result.text
