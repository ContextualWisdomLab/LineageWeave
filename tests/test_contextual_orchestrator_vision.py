from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_MODULE_PATH = Path(__file__).parents[1] / "docker" / "contextual-orchestrator" / "vision_compat.py"
_SPEC = importlib.util.spec_from_file_location("lineageweave_vision_compat", _MODULE_PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_multimodal_messages_are_validated_without_exposing_image_data_to_routing() -> None:
    messages = _MODULE.validate_multimodal_messages(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Read this"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,SECRET"}},
                ],
            }
        ]
    )

    assert messages[0]["content"][1]["image_url"]["url"].endswith("SECRET")
    assert _MODULE.latest_user_text(messages) == "Read this\n[image]"


@pytest.mark.parametrize(
    "content",
    [
        [],
        [{"type": "audio", "url": "https://example.test/audio"}],
        [{"type": "image_url", "image_url": {"url": "http://example.test/image"}}],
    ],
)
def test_multimodal_message_validation_rejects_unsupported_content(content: object) -> None:
    with pytest.raises(ValueError):
        _MODULE.validate_multimodal_messages([{"role": "user", "content": content}])
