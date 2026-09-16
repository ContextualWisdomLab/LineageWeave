import base64
from io import BytesIO

from PIL import Image

import lineageweave.image_content as image_content


def _transparent_png() -> bytes:
    image = Image.new("RGBA", (1, 1), (12, 34, 56, 0))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_vision_gateway_normalizes_image_and_preserves_structured_response(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def post_json(url, payload, *, headers, timeout):
        captured.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {
            "choices": [
                {
                    "message": {
                        "content": "TEXT: synthetic label\nCAPTION: a synthetic diagram\nTAGS: diagram, test"
                    }
                }
            ]
        }

    monkeypatch.setattr(image_content, "post_json", post_json)
    client = image_content.OpenAiCompatibleVisionClient(
        "http://orchestrator/v1", "gateway-key", "", allow_insecure_http=True
    )

    description = client.describe(_transparent_png(), "image/tiff")

    assert description.extracted_text == "synthetic label"
    assert description.caption == "a synthetic diagram"
    assert description.tags == ("diagram", "test")
    assert captured["url"] == "http://orchestrator/v1/chat/completions"
    assert captured["headers"] == {"authorization": "Bearer gateway-key"}
    payload = captured["payload"]
    assert "model" not in payload
    assert payload["mode"] == "auto"
    assert payload["reasoning_effort"] == "auto"
    assert [message["role"] for message in payload["messages"]] == ["system", "user"]
    user_message = payload["messages"][1]
    image_url = user_message["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/png;base64,")
    normalized = Image.open(BytesIO(base64.b64decode(image_url.split(",", 1)[1])))
    assert normalized.convert("RGB").getpixel((0, 0)) == (255, 255, 255)


def test_vision_factory_forwards_bounded_transport_timeout(monkeypatch) -> None:
    """Carry a caller-selected budget through the factory to synchronous HTTP work."""
    captured: dict[str, object] = {}

    def post_json(url, payload, *, headers, timeout):
        captured["timeout"] = timeout
        return {
            "choices": [
                {
                    "message": {
                        "content": "TEXT: NONE\nCAPTION: synthetic timeout probe\nTAGS: probe"
                    }
                }
            ]
        }

    monkeypatch.setattr(image_content, "post_json", post_json)
    client = image_content.orchestrator_vision_client(
        "http://orchestrator",
        "gateway-key",
        timeout=420.0,
    )

    client.describe(_transparent_png(), "image/png")

    assert captured["timeout"] == 420.0


def test_vision_factory_fails_closed_for_unsupported_url_scheme() -> None:
    client = image_content.orchestrator_vision_client("ftp://orchestrator", "gateway-key", "vision-model")
    assert isinstance(client, image_content.NullImageContentClient)
    assert client.available is False


def test_vision_factory_allows_orchestrator_model_selection() -> None:
    client = image_content.orchestrator_vision_client("http://orchestrator", "gateway-key")

    assert isinstance(client, image_content.OpenAiCompatibleVisionClient)
    assert client.available is True
