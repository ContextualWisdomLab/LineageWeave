from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from lineageweave.image_content import OpenAiCompatibleVisionClient


def test_vision_region_locator_uses_json_object_and_returns_regions(monkeypatch) -> None:
    image = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(image, format="PNG")
    seen: dict[str, object] = {}

    def fake_post_json(url, body, *, headers, timeout):
        seen.update(url=url, body=body, headers=headers, timeout=timeout)
        return {"choices": [{"message": {"content": json.dumps({"regions": [{"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.6}]})}}]}

    monkeypatch.setattr("lineageweave.image_content.post_json", fake_post_json)
    client = OpenAiCompatibleVisionClient(
        "http://orchestrator/v1", "secret", allow_insecure_http=True
    )

    regions = client.locate_regions(image.getvalue(), "image/png")

    assert regions[0].x == 0.1
    assert regions[0].width == 0.5
    body = seen["body"]
    assert body["mode"] == "auto"
    assert body["reasoning_effort"] == "auto"
    assert body["response_format"]["type"] == "json_object"
    assert "temperature" not in body


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "vision region response was not text JSON"),
        ("[]", "vision region response had no regions list"),
    ],
)
def test_vision_region_locator_rejects_wrong_response_types(
    monkeypatch, content: object, message: str
) -> None:
    """Reject provider response types outside the structured region contract."""
    monkeypatch.setattr(
        "lineageweave.vision_image.normalize_vision_image",
        lambda image_bytes, mime_type: (image_bytes, mime_type),
    )
    monkeypatch.setattr(
        "lineageweave.image_content.post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": content}}]},
    )
    client = OpenAiCompatibleVisionClient(
        "http://orchestrator/v1", "secret", allow_insecure_http=True
    )

    with pytest.raises(TypeError, match=message):
        client.locate_regions(b"image-bytes", "image/png")
