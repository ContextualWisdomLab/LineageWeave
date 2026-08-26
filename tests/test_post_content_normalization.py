"""Tests for lineageweave.post_content_normalization.

A fake vision client (no network) proves the wiring end to end without
needing a real provider; the real-provider round trip through
OpenAiCompatibleVisionClient is already covered by
tests/test_image_content.py and does not need re-proving here.
"""

from __future__ import annotations

import base64
from threading import Lock

from lineageweave.chunking import Chunk
from lineageweave.image_content import (
    ImageDescription,
    ImageRegion,
    NullImageContentClient,
)
from lineageweave.llm_context import current_llm_metadata, use_llm_metadata
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


class _MetadataCapturingVisionClient(_FakeVisionClient):
    def __init__(self, description: ImageDescription) -> None:
        super().__init__(description)
        self._lock = Lock()
        self.seen_metadata: list[dict[str, str] | None] = []

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription:
        with self._lock:
            self.seen_metadata.append(current_llm_metadata())
        return super().describe(image_bytes, mime_type)


class _FullImageRegionVisionClient(_FakeVisionClient):
    def locate_regions(self, image_bytes: bytes, mime_type: str) -> tuple[ImageRegion, ...]:
        return (ImageRegion(0.0, 0.0, 1.0, 1.0),)


class _PartialRegionVisionClient(_FakeVisionClient):
    def __init__(self, description: ImageDescription, fail_on_call: int | None = None) -> None:
        super().__init__(description)
        self.describe_calls = 0
        self.fail_on_call = fail_on_call

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription:
        self.describe_calls += 1
        if self.describe_calls == self.fail_on_call:
            raise RuntimeError("synthetic parent-image provider outage")
        return super().describe(image_bytes, mime_type)

    def locate_regions(self, image_bytes: bytes, mime_type: str) -> tuple[ImageRegion, ...]:
        return (ImageRegion(0.25, 0.25, 0.25, 0.25),)


class _MixedValidityRegionVisionClient(_PartialRegionVisionClient):
    def locate_regions(self, image_bytes: bytes, mime_type: str) -> tuple[ImageRegion, ...]:
        return (
            ImageRegion(0.25, 0.25, 0.25, 0.25),
            ImageRegion(-0.1, 0.0, 0.5, 0.5),
            ImageRegion(0.0, 0.0, float("nan"), 0.5),
            ImageRegion(None, 0.0, 0.5, 0.5),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
        )


class _TiledRegionVisionClient(_PartialRegionVisionClient):
    def locate_regions(self, image_bytes: bytes, mime_type: str) -> tuple[ImageRegion, ...]:
        return (
            ImageRegion(0.0, 0.0, 0.5, 1.0),
            ImageRegion(0.5, 0.0, 0.5, 1.0),
        )


class _LocatorFailureVisionClient(_FakeVisionClient):
    def locate_regions(self, image_bytes: bytes, mime_type: str) -> tuple[ImageRegion, ...]:
        raise RuntimeError("synthetic locator outage")


class _EmptyLocatorVisionClient(_FakeVisionClient):
    def locate_regions(self, image_bytes: bytes, mime_type: str) -> tuple[ImageRegion, ...]:
        return None  # type: ignore[return-value]


class _MalformedLocatorVisionClient(_FakeVisionClient):
    def locate_regions(self, image_bytes: bytes, mime_type: str) -> tuple[ImageRegion, ...]:
        return object()  # type: ignore[return-value]


class _PartialRegionFailureVisionClient(_FakeVisionClient):
    def locate_regions(self, image_bytes: bytes, mime_type: str) -> tuple[ImageRegion, ...]:
        return (ImageRegion(0.25, 0.25, 0.25, 0.25),)

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription:
        raise RuntimeError("synthetic region and parent outage")


def test_plain_text_passes_through_unchanged() -> None:
    result = normalize_post_body("Just a plain business record, no markup here.")
    assert result.text == "Just a plain business record, no markup here."
    assert result.formatting_hints == ()
    assert result.image_descriptions == ()


def test_plain_text_visual_continuation_breaks_are_normalized_for_embeddings() -> None:
    result = normalize_post_body("- 요청 사항\n    후속 설명은 같은 항목에 속한다.\n· 다음 항목")

    assert result.text == "- 요청 사항 후속 설명은 같은 항목에 속한다.\n· 다음 항목"


def test_html_tags_never_appear_in_the_normalized_text() -> None:
    html = '<div style="color:red"><p>Confirm delivery by Friday.</p></div>'
    result = normalize_post_body(html)
    assert "style" not in result.text
    assert "<p>" not in result.text
    assert "<div" not in result.text
    assert "Confirm delivery by Friday." in result.text


def test_nested_html_character_references_are_decoded() -> None:
    result = normalize_post_body("<p>Company&amp;nbsp;&amp;amp;&amp;nbsp;Product &#39;s note</p>")
    assert result.text == "Company & Product 's note"


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
    assert "Q3 2026" in result.text
    assert "After the image." in result.text
    # Document order is preserved, not just "somewhere in the text."
    before_index = result.text.index("Before the image.")
    image_index = result.text.index("bar chart")
    after_index = result.text.index("After the image.")
    assert before_index < image_index < after_index
    assert result.image_descriptions == (description,)


def test_single_full_image_locator_response_keeps_parent_evidence_without_region() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    html = f'<p>Before.</p><img src="data:image/png;base64,{b64}"/><p>After.</p>'
    description = ImageDescription(
        extracted_text="panel text", caption="one visual panel", tags=("panel",)
    )

    result = normalize_post_body(html, vision_client=_FullImageRegionVisionClient(description))

    assert result.image_results[0].status_code == "described"
    assert result.image_results[0].regions == ()
    assert result.image_results[0].description == description
    assert "panel text" in result.text


def test_image_without_ocr_uses_caption_only_and_preserves_image_result() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    description = ImageDescription(extracted_text="", caption="a blank chart", tags=())

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>',
        vision_client=_FakeVisionClient(description),
    )

    assert result.text == "[image: a blank chart]"
    assert result.image_results[0].status_code == "described"


def test_unavailable_vision_channel_keeps_an_explicit_image_outcome() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>',
        vision_client=NullImageContentClient(),
    )

    assert result.text == "[image: content unavailable]"
    assert result.image_results[0].status_code == "unavailable"


def test_available_client_with_missing_image_bytes_keeps_unavailable_outcome() -> None:
    from lineageweave.post_content_normalization import _describe_image_chunk

    result, description, placeholder = _describe_image_chunk(
        Chunk(text="", unit_type="image", index=0, label="image/png", image_data=None),
        _FakeVisionClient(ImageDescription(extracted_text="", caption="unused", tags=())),
    )

    assert result.status_code == "unavailable"
    assert description is None
    assert placeholder == "[image: content unavailable]"


def test_locator_failure_falls_back_to_parent_image_evidence() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    description = ImageDescription(extracted_text="parent", caption="whole image", tags=())

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>',
        vision_client=_LocatorFailureVisionClient(description),
    )

    assert result.image_results[0].status_code == "described"
    assert result.image_results[0].regions == ()
    assert result.image_results[0].description == description


def test_empty_locator_result_falls_back_to_parent_image_evidence() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    description = ImageDescription(extracted_text="parent", caption="whole image", tags=())

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>',
        vision_client=_EmptyLocatorVisionClient(description),
    )

    assert result.image_results[0].status_code == "described"
    assert result.image_results[0].regions == ()
    assert result.image_results[0].description == description


def test_non_iterable_locator_result_falls_back_to_parent_image_evidence() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    description = ImageDescription(extracted_text="parent", caption="whole image", tags=())

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>',
        vision_client=_MalformedLocatorVisionClient(description),
    )

    assert result.image_results[0].status_code == "described"
    assert result.image_results[0].regions == ()
    assert result.image_results[0].description == description


def test_partial_locator_with_no_successful_description_fails_closed() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>',
        vision_client=_PartialRegionFailureVisionClient(
            ImageDescription(extracted_text="unused", caption="unused", tags=())
        ),
    )

    assert result.image_results[0].status_code == "failed"
    assert result.text == "[image: content unavailable]"


def test_unknown_chunk_kinds_are_not_leaked_into_buyer_text(monkeypatch) -> None:
    from lineageweave import post_content_normalization

    monkeypatch.setattr(
        post_content_normalization,
        "chunk_by_dom",
        lambda _body: [Chunk(text="hidden", unit_type="unknown", index=0)],
    )

    result = normalize_post_body("<div>ignored by the synthetic chunker</div>")

    assert result.text == ""


def test_image_analysis_preserves_post_scoped_llm_metadata() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    html = (
        f'<img src="data:image/png;base64,{b64}"/>'
        f'<img src="data:image/png;base64,{b64}"/>'
    )
    description = ImageDescription(extracted_text="Q3 2026", caption="a chart", tags=("chart",))
    client = _MetadataCapturingVisionClient(description)
    metadata = {
        "lineageweave_post_id": "post-1",
        "lineageweave_pu": "PU-01",
    }

    with use_llm_metadata(metadata):
        result = normalize_post_body(html, vision_client=client)

    assert len(result.image_descriptions) == 2
    assert len(client.seen_metadata) == 2
    assert all(seen == metadata for seen in client.seen_metadata)


def test_partial_region_response_retains_panel_and_parent_evidence() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    html = f'<img src="data:image/png;base64,{b64}"/>'
    client = _PartialRegionVisionClient(
        ImageDescription(extracted_text="whole image", caption="whole", tags=())
    )
    result = normalize_post_body(html, vision_client=client)

    assert result.image_results[0].regions[0].region == ImageRegion(0.25, 0.25, 0.25, 0.25)
    assert client.describe_calls == 2


def test_tiled_regions_still_retain_parent_image_evidence() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    client = _TiledRegionVisionClient(
        ImageDescription(extracted_text="source", caption="source", tags=())
    )

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>', vision_client=client
    )

    assert len(result.image_results[0].regions) == 2
    assert client.describe_calls == 3


def test_partial_region_parent_failure_keeps_successful_panel_evidence() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    client = _PartialRegionVisionClient(
        ImageDescription(extracted_text="panel", caption="panel", tags=()),
        fail_on_call=2,
    )

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>',
        vision_client=client,
    )

    assert result.image_results[0].status_code == "described"
    assert result.image_results[0].regions[0].description is not None
    assert result.image_results[0].description is not None


def test_partial_region_analysis_discards_unbounded_locator_regions() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    client = _MixedValidityRegionVisionClient(
        ImageDescription(extracted_text="whole", caption="whole", tags=())
    )

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>',
        vision_client=client,
    )

    assert len(result.image_results[0].regions) == 1
    assert result.image_results[0].regions[0].region == ImageRegion(0.25, 0.25, 0.25, 0.25)


def test_non_iterable_locator_result_falls_back_to_parent_evidence() -> None:
    b64 = base64.b64encode(_PNG_1X1).decode("ascii")
    description = ImageDescription(extracted_text="parent", caption="whole", tags=())

    result = normalize_post_body(
        f'<img src="data:image/png;base64,{b64}"/>',
        vision_client=_MalformedLocatorVisionClient(description),
    )

    assert result.image_results[0].status_code == "described"
    assert result.image_results[0].regions == ()
    assert result.image_results[0].description == description


def test_comparison_operators_in_plain_text_are_not_treated_as_html() -> None:
    body = "Need delivery if qty < 50 and price > 10."
    result = normalize_post_body(body)
    assert result.text == body
    assert result.formatting_hints == ()


def test_quantity_superscripts_normalize_to_unicode_for_embeddings() -> None:
    html = normalize_post_body("<p>Tank volume is 12 m<sup>3</sup>.</p>")
    assert html.text == "Tank volume is 12 m³."
    caret = normalize_post_body("Tank volume is 12 m^3.")
    assert caret.text == "Tank volume is 12 m³."


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
