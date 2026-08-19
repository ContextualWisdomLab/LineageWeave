"""Contract tests for the contextual-orchestrator post-chat transport."""

from __future__ import annotations

import pytest

from lineageweave import post_chat
from lineageweave.post_chat import ChatSourceDocument, ContextualOrchestratorPostChatClient


def test_post_chat_uses_supported_conduct_mode_and_accuracy_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LineageWeave must not send the orchestrator's rejected legacy verify mode."""
    captured: dict[str, object] = {}

    def fake_post_json(url, payload, *, headers, timeout):
        captured.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"answer_text":"Grounded","cited_source_numbers":[1]}'
                    }
                }
            ]
        }

    monkeypatch.setattr(post_chat, "post_json", fake_post_json)
    client = ContextualOrchestratorPostChatClient(
        "https://orchestrator.example/",
        "service-token",
    )
    answer = client.answer(
        "What happened?",
        [ChatSourceDocument("post-1", "Evidence", "Grounded source")],
    )

    assert answer.cited_post_ids == ("post-1",)
    assert captured["url"] == "https://orchestrator.example/v1/chat/completions"
    assert captured["payload"]["mode"] == "conduct"
    assert captured["payload"]["reasoning_effort"] == "high"
    assert captured["headers"] == {"authorization": "Bearer service-token"}
    assert captured["timeout"] == post_chat.DEFAULT_CHAT_TIMEOUT_SECONDS == 300.0


def test_post_chat_custom_timeout_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deployments can bound conduct calls without changing the wire contract."""
    captured: dict[str, object] = {}

    def fake_post_json(_url, _payload, *, headers, timeout):
        captured.update(headers=headers, timeout=timeout)
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"answer_text":"Grounded","cited_source_numbers":[1]}'
                    }
                }
            ]
        }

    monkeypatch.setattr(post_chat, "post_json", fake_post_json)
    ContextualOrchestratorPostChatClient(
        "https://orchestrator.example",
        "service-token",
        timeout=45.0,
    ).answer("Question", [ChatSourceDocument("post-1", "Evidence", "Source")])
    assert captured["timeout"] == 45.0