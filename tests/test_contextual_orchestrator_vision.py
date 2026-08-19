from __future__ import annotations

import json

import lineageweave.image_content as image_content
import lineageweave.http_client as http_client
from lineageweave.llm_context import use_llm_metadata


def test_native_vision_client_sends_multimodal_payload_through_orchestrator(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(
        "lineageweave.vision_image.normalize_vision_image",
        lambda image_bytes, mime_type: (image_bytes, mime_type),
    )

    def fake_request(method, url, *, body, headers, timeout):
        captured["url"] = url
        captured["payload"] = json.loads(body)
        response = {
            "choices": [{
                "message": {
                    "content": "TEXT: visible text\nCAPTION: a diagram\nTAGS: diagram",
                }
            }]
        }
        return 200, json.dumps(response).encode("utf-8")

    monkeypatch.setattr(http_client, "_request", fake_request)
    client = image_content.OpenAiCompatibleVisionClient(
        "http://orchestrator/v1", "test-key", allow_insecure_http=True
    )

    with use_llm_metadata({"lineageweave_post_session_id": "session-1"}):
        result = client.describe(b"image-bytes", "image/png")

    assert result.extracted_text == "visible text"
    assert captured["url"] == "http://orchestrator/v1/chat/completions"
    assert captured["payload"]["metadata"]["lineageweave_post_session_id"] == "session-1"
    assert captured["payload"]["messages"][1]["content"][1]["type"] == "image_url"
