"""Synthetic ASGI-to-native-HTTP framing persistence discriminator."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from backend.app import main
from lineageweave import observability, post_chat
from tests.test_http_client_native_framing_custody import native_transport, _framing_case
from tests.test_post_chat_live_authorization import _ACCOUNT, _LiveConnection, _Pool, _row


@pytest.mark.parametrize(
    "case,expected_status",
    [("declared_complete", 200), ("declared_short", 503),
     ("missing_terminal", 503), ("missing_terminal_dual", 503)],
)
def test_incomplete_frame_cannot_become_a_persisted_http_answer(
    monkeypatch: pytest.MonkeyPatch, native_transport: object,
    case: str, expected_status: int, tmp_path: Path,
) -> None:
    """An invalid transport must stop before derived-answer writes and activity."""
    class Connection(_LiveConnection):
        """Retain actual persistence command arguments without a database."""
        def __init__(self) -> None:
            super().__init__()
            self.writes: list[tuple[str, tuple[object, ...]]] = []

        async def execute(self, sql: str, *args: object) -> str:
            self.writes.append((sql, args))
            return await super().execute(sql, *args)

    conn = Connection()
    pool = _Pool(conn)
    activities: list[str] = []
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(observability.trace, "get_tracer", provider.get_tracer)

    async def account() -> object:
        return _ACCOUNT

    async def pool_dependency() -> object:
        return pool

    async def valkey_dependency() -> object:
        return object()

    async def visible(*_args: object) -> dict:
        return _row()

    async def gathered(*_args: object, **_kwargs: object) -> list[post_chat.ChatSourceDocument]:
        return [post_chat.ChatSourceDocument(p, "Synthetic title", "Synthetic body")
                for p in ("focal", "linked")]

    async def activity(*args: object) -> None:
        assert conn.depth == 0
        activities.append(str(args[2]))

    real_client = post_chat.ContextualOrchestratorPostChatClient(
        "http://synthetic.invalid", "synthetic-only-token", timeout=1)
    original_answer = real_client.answer

    def answer(question: str, sources: list[post_chat.ChatSourceDocument]) -> post_chat.ChatAnswer:
        assert pool.acquired == 0 and conn.depth == 0
        return original_answer(question, sources)

    monkeypatch.setattr(real_client, "answer", answer)
    monkeypatch.setattr(main, "_post_chat_client", lambda: real_client)
    monkeypatch.setattr(main, "_vision_client", object)
    monkeypatch.setattr(main, "_load_visible_post", visible)
    monkeypatch.setattr(main, "gather_chat_sources", gathered)
    monkeypatch.setattr(main, "build_post_llm_metadata", lambda *_args: {})
    monkeypatch.setattr(main, "publish_activity_event", activity)
    old_overrides = dict(main.app.dependency_overrides)
    main.app.dependency_overrides.update({main.get_current_account: account,
        main.get_pool: pool_dependency, main.get_valkey: valkey_dependency})
    wire, complete = _framing_case(case)
    connection, socket, responses = native_transport(wire)
    try:
        # Not entering the TestClient context deliberately excludes app lifespan.
        # Per-request auth is an explicit synthetic dependency, not JWT acceptance.
        client = TestClient(main.app)
        try:
            response = client.post("/api/posts/focal/chat", json={"question": "Synthetic question"})
        finally:
            client.close()
        body = response.json()
        assert len(responses) == 1 and socket.closed and connection.sock is None
        assert conn.depth == 0 and pool.acquired == 0
        result_writes = [args for sql, args in conn.writes if "insert into post_chat_result " in sql]
        spans = exporter.get_finished_spans()
        transport_spans = [s for s in spans if s.name == "lineageweave.http.post_json"]
        assert len(transport_spans) == 1
        row = {
            "case": case, "native_frame_complete": complete,
            "expected_http_status": expected_status, "actual_http_status": response.status_code,
            "response_answer_present": "answer_text" in body,
            "result_insert_calls": len(result_writes),
            "receipt_insert_calls": sum("insert into post_chat_authorization_receipt " in q for q, _ in conn.writes),
            "source_insert_calls": sum("insert into post_chat_source " in q for q, _ in conn.writes),
            "activity_calls": len(activities),
            "transport_span_status": transport_spans[0].status.status_code.name,
            "response_closed": responses[0].isclosed(),
            "database_and_pool_settled": conn.depth == 0 and pool.acquired == 0,
        }
        destination = Path(os.environ.get("LW_FRAME_RESULT_ROOT", str(tmp_path))) / (case + ".json")
        with destination.open("x") as output:
            json.dump(row, output, indent=2)
        if response.status_code == 200:
            assert body["answer_text"] == "Synthetic answer."
            assert result_writes[0][3] == body["answer_text"]
            assert len(activities) == 1
            assert body["source_post_ids"] == ["focal", "linked"]
            assert transport_spans[0].status.status_code is StatusCode.UNSET
        else:
            assert response.status_code == 503 and not conn.writes and not activities
            assert transport_spans[0].status.status_code is StatusCode.ERROR
        assert response.status_code == expected_status, "incomplete HTTP framing reached answer persistence"
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(old_overrides)
        provider.shutdown()
