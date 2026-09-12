from __future__ import annotations

import asyncio
from contextlib import nullcontext
from typing import Any

from backend.app import main
from backend.app.auth import CurrentAccount
from lineageweave.post_chat import ChatAnswer, ChatSourceDocument


class EmptyConnection:
    """Connection sentinel for an endpoint test that must not rely on database behavior."""


class AcquireConnection:
    """Async pool acquisition shim that yields the endpoint-test connection sentinel."""

    async def __aenter__(self) -> EmptyConnection:
        """Yield the test connection without opening a real database transaction."""
        return EmptyConnection()

    async def __aexit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        """Release the test connection without side effects."""
        return None


class EmptyPool:
    """Pool shim used to prove replay authorization at the application boundary."""

    def acquire(self) -> AcquireConnection:
        """Return an async acquisition context for the sentinel connection."""
        return AcquireConnection()


class LiveChatClient:
    """Deterministic live-generation substitute used after cached replay fails closed."""

    available = True

    def answer(self, _question: str, _sources: list[ChatSourceDocument]) -> ChatAnswer:
        """Return a scoped answer so the test can distinguish recomputation from replay."""
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
        """Return the focal post as visible to isolate derived-answer authorization."""
        return {"post_id": "post-1", "post_title": "Visible focal post"}

    async def legacy_chat(*_args: object, **_kwargs: object) -> dict[str, Any]:
        """Represent a historical cached answer that has no generation-scope receipt."""
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
        """Return only evidence visible under the reader's current authorization scope."""
        return [
            ChatSourceDocument(
                post_id="post-1",
                post_title="Visible focal post",
                post_body="Authorized current evidence",
            )
        ]

    async def record_live_answer(*args: object, **_kwargs: object) -> None:
        """Capture replacement persistence after the legacy cache is rejected."""
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
        """Suppress unrelated activity publication in this authorization regression."""
        return None

    monkeypatch.setattr(main, "_load_visible_post", visible_post)
    monkeypatch.setattr(main, "build_post_llm_metadata", lambda *_args: {})
    monkeypatch.setattr(main, "use_llm_metadata", lambda _metadata: nullcontext())
    monkeypatch.setattr(main, "traced", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(main, "fetch_persisted_chat", legacy_chat)
    monkeypatch.setattr(main, "_post_chat_client", LiveChatClient)
    monkeypatch.setattr(main, "_vision_client", object)
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
