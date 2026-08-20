"""Contract tests for the contextual-orchestrator post-chat transport."""

from __future__ import annotations

import pytest

from lineageweave import post_chat
from lineageweave.post_chat import ChatSourceDocument, ContextualOrchestratorPostChatClient


def test_post_chat_uses_auto_orchestration_schema_and_post_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gateway owns model/protocol/reasoning selection and receives post context."""
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
        session_id="lineageweave:post:post-1",
        metadata={"pu_code": "PU-1", "corp_code": "CORP-1"},
    )

    assert answer.cited_post_ids == ("post-1",)
    assert captured["url"] == "https://orchestrator.example/v1/chat/completions"
    assert captured["payload"]["mode"] == "auto"
    assert captured["payload"]["reasoning_effort"] == "auto"
    assert captured["payload"]["max_tokens"] == 2400
    assert captured["payload"]["response_format"] == post_chat.POST_CHAT_RESPONSE_FORMAT
    assert captured["payload"]["metadata"] == {
        "session_id": "lineageweave:post:post-1",
        "pu_code": "PU-1",
        "corp_code": "CORP-1",
    }
    assert captured["payload"]["messages"][0]["role"] == "system"
    assert captured["headers"] == {"authorization": "Bearer service-token"}
    assert captured["timeout"] == post_chat.DEFAULT_CHAT_TIMEOUT_SECONDS == 300.0


def test_post_chat_custom_timeout_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deployments can bound auto calls without changing the wire contract."""
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
