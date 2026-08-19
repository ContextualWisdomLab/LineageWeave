from __future__ import annotations

import io
import json

from PIL import Image

from lineageweave.image_content import OpenAiCompatibleVisionClient


def test_structured_vision_uses_json_schema_and_returns_regions(monkeypatch) -> None:
    image = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(image, format="PNG")
    seen: dict[str, object] = {}

    def fake_post_json(url, body, *, headers, timeout):
        seen.update(url=url, body=body, headers=headers, timeout=timeout)
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "text": "diagram",
                                "description": "A diagram.",
                                "region": [
                                    {
                                        "x": 0.1,
                                        "y": 0.2,
                                        "width": 0.5,
                                        "height": 0.6,
                                        "text": "panel",
                                        "description": "A panel.",
                                    }
                                ],
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("lineageweave.image_content.post_json", fake_post_json)
    client = OpenAiCompatibleVisionClient(
        "http://orchestrator/v1", "secret", allow_insecure_http=True
    )

    whole, regions = client.describe_regions(image.getvalue(), "image/png")

    assert whole.caption == "A diagram."
    assert regions[0].region.x == 0.1
    assert regions[0].description.extracted_text == "panel"
    body = seen["body"]
    assert body["mode"] == "auto"
    assert body["reasoning_effort"] == "auto"
    assert body["response_format"]["type"] == "json_object"
    assert "temperature" not in body
