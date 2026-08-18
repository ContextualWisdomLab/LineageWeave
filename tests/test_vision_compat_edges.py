from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


_PATH = Path(__file__).parents[1] / "docker" / "contextual-orchestrator" / "vision_compat.py"
_SPEC = importlib.util.spec_from_file_location("lineageweave_vision_compat_extra", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_multimodal_validator_preserves_text_and_safe_image_url_fields() -> None:
    messages = _MODULE.validate_multimodal_messages(
        [
            {"role": "system", "content": "system"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "read this"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,abc", "detail": "high", "extra": "drop"},
                    },
                    {"type": "image_url", "image_url": {"url": "https://example.test/image.png"}},
                ],
            },
        ]
    )

    assert messages[1]["content"] == [
        {"type": "text", "text": "read this"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": "https://example.test/image.png"}},
    ]


@pytest.mark.parametrize(
    "messages",
    [
        [],
        {},
        [{"role": "invalid", "content": "text"}],
        [{"role": "user", "content": []}],
        [{"role": "user", "content": ["not a block"]}],
        [{"role": "user", "content": [{"type": "text", "text": 1}]}],
        [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "http://insecure"}}]}],
        [{"role": "user", "content": [{"type": "file", "file": {}}]}],
    ],
)
def test_multimodal_validator_rejects_unsafe_or_malformed_messages(messages: object) -> None:
    with pytest.raises(ValueError):
        _MODULE.validate_multimodal_messages(messages)


def test_latest_user_text_never_includes_image_payload() -> None:
    messages = [
        {"role": "assistant", "content": "old"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "question"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,secret"}},
            ],
        },
    ]

    assert _MODULE.latest_user_text(messages) == "question\n[image]"
    assert _MODULE.latest_user_text([{"role": "assistant", "content": "only assistant"}]) == ""


def test_install_multimodal_support_wraps_errors_and_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    package = types.ModuleType("contextual_orchestrator")
    server = types.ModuleType("contextual_orchestrator.server")
    orchestrator = types.ModuleType("contextual_orchestrator.orchestrator")

    class RequestError(Exception):
        def __init__(self, status: int, code: str, detail: str) -> None:
            super().__init__(detail)
            self.status = status
            self.code = code

    class TaskOrchestrator:
        def _latest_user_text(self, _messages: list[dict]) -> str:
            return "original"

    server.RequestError = RequestError
    server._validate_messages = lambda messages: messages
    orchestrator.TaskOrchestrator = TaskOrchestrator
    package.server = server
    package.orchestrator = orchestrator
    monkeypatch.setitem(sys.modules, "contextual_orchestrator", package)
    monkeypatch.setitem(sys.modules, "contextual_orchestrator.server", server)
    monkeypatch.setitem(sys.modules, "contextual_orchestrator.orchestrator", orchestrator)

    _MODULE.install_multimodal_chat_support()
    first_validator = server._validate_messages
    assert server._validate_messages([{"role": "user", "content": "ok"}])[0]["role"] == "user"
    with pytest.raises(RequestError) as error:
        server._validate_messages([])
    assert error.value.status == 400
    assert TaskOrchestrator()._latest_user_text(
        [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "https://example.test"}}]}]
    ) == "[image]"

    _MODULE.install_multimodal_chat_support()
    assert server._validate_messages is first_validator
