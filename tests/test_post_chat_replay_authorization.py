from __future__ import annotations

import asyncio
from contextlib import nullcontext
from typing import Any

from backend.app import main
from backend.app.auth import CurrentAccount
from lineageweave.post_chat import ChatAnswer, ChatSourceDocument


class EmptyConnection:
    pass


class AcquireConnection:
    async def __aenter__(self) -> EmptyConnection:
        return EmptyConnection()

    async def __aexit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None


class EmptyPool:
    def acquire(self) -> AcquireConnection:
        return AcquireConnection()


class LiveChatClient:
    available = True

    def answer(self, _question: str, _sources: list[ChatSourceDocument]) -> ChatAnswer:
        return ChatAnswer(answer_text="live scoped answer", cited_post_ids=("post-1",))


def test_legacy_unscoped_chat_row_is_not_replayed(monkeypatch) -> None:
    """A cached answer without generation-scope evidence must fail closed to live generation."""
    account = CurrentAccount(
        user_account_id="00000000-0000-0000-0000-000000000001",
        external_subject_id="replay-scope-test",
        display_name="Replay Scope Test",
        preferred_locale="en",
        corporate_entity_ids=frozenset({"00000000-0000-0000-0000-000000000010"}),
        process_unit_ids=frozenset({"00000000-0000-0000-0000-000000000020"}),
        permission_codes=frozenset({"post_read"}),
    )
    persisted_calls: list[tuple[str, str, str, list[str]]] = []

    async def visible_post(_post_id: str, _account: CurrentAccount, _pool: object) -> dict[str, Any]:
        return {"post_id": "post-1", "post_title": "Visible focal post"}

    async def legacy_chat(*_args: object, **_kwargs: object) -> dict[str, Any]:
        return {
            "answer_text": "legacy answer derived without a generation-scope receipt",
            "cited_post_ids": ["post-1"],
            "cited_posts": [{"post_id": "post-1", "post_title": "Visible focal post"}],
        }

    async def scoped_sources(
        _conn: object,
        _post_id: str,
        _can_see_post: object,
        **_kwargs: object,
    ) -> list[ChatSourceDocument]:
        return [
            ChatSourceDocument(
                post_id="post-1",
                post_title="Visible focal post",
                post_body="Authorized current evidence",
            )
        ]

    async def record_live_answer(*args: object, **_kwargs: object) -> None:
        _conn, post_id, question, answer_text, cited_post_ids, *_rest = args
        persisted_calls.append(
            (
                str(post_id),
                str(question),
                str(answer_text),
                [str(post_id) for post_id in cited_post_ids],
            )
        )

    async def no_activity(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(main, "_load_visible_post", visible_post)
    monkeypatch.setattr(main, "build_post_llm_metadata", lambda *_args: {})
    monkeypatch.setattr(main, "use_llm_metadata", lambda _metadata: nullcontext())
    monkeypatch.setattr(main, "traced", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(main, "fetch_persisted_chat", legacy_chat)
    monkeypatch.setattr(main, "_post_chat_client", LiveChatClient)
    monkeypatch.setattr(main, "_vision_client", lambda: object())
    monkeypatch.setattr(main, "gather_chat_sources", scoped_sources)
    monkeypatch.setattr(main, "persist_post_chat", record_live_answer)
    monkeypatch.setattr(main, "publish_activity_event", no_activity)

    payload = asyncio.run(
        main.chat_about_post(
            post_id="post-1",
            request=main.ChatRequest(question="What happened?"),
            account=account,
            pool=EmptyPool(),
            valkey=object(),
        )
    )

    assert payload["answer_text"] == "live scoped answer"
    assert payload["source_post_ids"] == ["post-1"]
    assert persisted_calls == [
        ("post-1", "What happened?", "live scoped answer", ["post-1"])
    ]
