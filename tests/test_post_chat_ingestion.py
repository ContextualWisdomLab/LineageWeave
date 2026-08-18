from __future__ import annotations

import asyncio

import pytest

from backend.app.post_chat_ingestion import (
    fetch_persisted_chat,
    fetch_persisted_chats,
    normalize_chat_question,
    persist_post_chat,
)
from lineageweave.post_chat import (
    ChatSourceDocument,
    ContextualOrchestratorPostChatClient,
    parse_chat_response,
)


class _Connection:
    def __init__(self, *, header: dict[str, str] | None, citations: list[dict[str, str]]) -> None:
        self.header = header
        self.citations = citations
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"

    async def fetchrow(self, _query: str, *_args: object):
        return self.header

    async def fetch(self, query: str, *_args: object):
        if "question_norm from post_chat_result" in query:
            return [{"question_norm": "question"}]
        return self.citations


def test_normalize_question_rejects_empty_and_collapses_whitespace() -> None:
    assert normalize_chat_question("  What   happened? ") == "what happened between these events"
    assert normalize_chat_question(" \t ") == ""


def test_persist_chat_deduplicates_citations_and_serializes_result() -> None:
    conn = _Connection(
        header={"question_text": "What happened?", "answer_text": "A synthetic answer."},
        citations=[
            {"cited_post_id": "post-a", "post_title": "Evidence A"},
            {"cited_post_id": "post-b", "post_title": "Evidence B"},
        ],
    )

    payload = asyncio.run(
        persist_post_chat(conn, "post-1", "  What   happened? ", "A synthetic answer.", ["post-a", "post-a", "post-b"])
    )

    assert payload["cited_post_ids"] == ["post-a", "post-b"]
    assert len([query for query, _args in conn.executed if "post_chat_citation" in query]) == 2
    assert any("post_chat_result" in query and "delete" in query.lower() for query, _args in conn.executed)


def test_fetch_chat_handles_empty_and_missing_rows() -> None:
    missing = _Connection(header=None, citations=[])
    assert asyncio.run(fetch_persisted_chat(missing, "post-1", " ")) is None
    assert asyncio.run(fetch_persisted_chat(missing, "post-1", "question")) is None
    assert asyncio.run(fetch_persisted_chats(missing, "post-1")) == []


def test_fetch_chat_list_serializes_existing_exchange() -> None:
    conn = _Connection(
        header={"question_text": "Question", "answer_text": "Answer"},
        citations=[{"cited_post_id": "post-a", "post_title": "Evidence A"}],
    )
    exchanges = asyncio.run(fetch_persisted_chats(conn, "post-1"))
    assert len(exchanges) == 1
    assert exchanges[0]["cited_posts"][0]["post_title"] == "Evidence A"


def test_parse_chat_response_strips_fence_and_drops_invalid_citations() -> None:
    sources = [ChatSourceDocument("post-a", "Evidence A", "body")]
    answer = parse_chat_response(
        '```json\n{"answer_text":" answer ","cited_source_numbers":[1, 0, 2, "bad"]}\n```',
        sources,
    )
    assert answer is not None
    assert answer.answer_text == "answer"
    assert answer.cited_post_ids == ("post-a",)
    assert parse_chat_response("not json", sources) is None
    assert parse_chat_response('{"answer_text":""}', sources) is None


def test_contextual_chat_client_uses_auto_mode_and_evidence_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post_json(url: str, payload: dict, *, headers: dict[str, str], timeout: float) -> dict:
        captured.update({"url": url, "payload": payload, "headers": headers, "timeout": timeout})
        return {
            "choices": [
                {"message": {"content": '{"answer_text":"supported", "cited_source_numbers":[1, 9]}'}},
            ]
        }

    monkeypatch.setattr("lineageweave.post_chat.post_json", fake_post_json)
    client = ContextualOrchestratorPostChatClient("https://orchestrator", "secret", reasoning_effort="low")
    answer = client.answer(
        "What happened?",
        [ChatSourceDocument("post-a", "Evidence A", "body", graph_facts=("fact",))],
    )

    assert answer.answer_text == "supported"
    assert answer.cited_post_ids == ("post-a",)
    assert captured["url"] == "https://orchestrator/v1/chat/completions"
    payload = captured["payload"]
    assert payload["mode"] == "auto"
    assert payload["reasoning_effort"] == "low"
    assert "fact" in payload["messages"][0]["content"]


def test_contextual_chat_client_rejects_malformed_provider_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lineageweave.post_chat.post_json",
        lambda *_args, **_kwargs: {"choices": [{"message": {"content": "{}"}}]},
    )
    client = ContextualOrchestratorPostChatClient("https://orchestrator", "secret")
    with pytest.raises(ValueError, match="required format"):
        client.answer("Question", [ChatSourceDocument("post-a", "Evidence A", "body")])
