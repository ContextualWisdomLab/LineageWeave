from __future__ import annotations

import asyncio
from threading import Event, Timer
from types import SimpleNamespace

import pytest

from backend.app.post_chat_ingestion import (
    _POST_CHAT_CANDIDATE_LIMIT,
    LinkedPostIds,
    cited_post_images,
    fetch_persisted_chat,
    fetch_persisted_chats,
    find_linked_post_ids,
    find_project_sibling_post_ids,
    gather_chat_sources,
    normalize_chat_question,
    persist_post_chat,
)
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
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


class _SourceConnection:
    async def fetchrow(self, query: str, *_args: object):
        if "from source_post where post_id" not in query:
            return None
        return {
            "post_id": "post-1",
            "post_title": "Public post",
            "post_body": "<p>Body</p>",
            "source_system_code": None,
            "source_record_key": None,
            "source_author_code": None,
            "source_author_name": None,
            "source_company_code": None,
            "source_company_name": None,
            "source_process_unit_code": None,
            "source_process_unit_name": None,
            "source_sales_pool_code": None,
            "source_sales_pool_name": None,
            "source_customer_code": None,
            "source_customer_name": None,
            "source_project_code": None,
            "source_project_name": None,
        }

    async def fetch(self, _query: str, *_args: object):
        return []


def test_project_siblings_are_separate_from_event_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ProjectConnection:
        project_queries = 0

        async def fetch(self, query: str, *_args: object):
            if "post_lineage_edge" in query or "select distinct person_id" in query:
                return []
            if "select distinct project_key" in query:
                self.project_queries += 1
                return [{"project_key": "project-synthetic"}]
            if "where ppm.project_key = any" in query:
                assert SOURCE_POST_ELIGIBILITY_SQL.format(alias="sp") in query
                assert _args[1] == "post-1"
                return [{"post_id": "post-2"}]
            return []

    async def no_graph(_conn: object, post_ids: list[str]):
        assert post_ids == ["post-1"]
        return []

    monkeypatch.setattr(
        "backend.app.post_chat_ingestion.load_visible_subgraph",
        no_graph,
    )
    connection = ProjectConnection()
    linked = asyncio.run(find_linked_post_ids(connection, "post-1"))
    siblings = asyncio.run(find_project_sibling_post_ids(connection, "post-1"))

    assert linked == LinkedPostIds(direct=frozenset(), indirect=frozenset())
    assert siblings == frozenset({"post-2"})
    assert connection.project_queries == 1


def test_project_sibling_precedes_a_dense_graph_candidate_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact project evidence is not crowded out by a dense graph window."""

    root_id = "00000000-0000-0000-0000-000000000001"
    project_id = "00000000-0000-0000-0000-000000000002"
    direct_ids = {
        f"00000000-0000-0000-0001-{index:012d}" for index in range(40)
    }

    class DenseConnection(_SourceConnection):
        candidate_ids: list[str] = []

        async def fetch(self, query: str, *args: object):
            if "select post_id, post_title, post_body, visibility_code" in query:
                self.candidate_ids = list(args[0])
                return []
            return []

    async def dense_links(_conn: object, _post_id: str) -> LinkedPostIds:
        return LinkedPostIds(frozenset(direct_ids), frozenset())

    async def project_link(_conn: object, _post_id: str) -> frozenset[str]:
        return frozenset({project_id})

    monkeypatch.setattr(
        "backend.app.post_chat_ingestion.find_linked_post_ids", dense_links
    )
    monkeypatch.setattr(
        "backend.app.post_chat_ingestion.find_project_sibling_post_ids",
        project_link,
    )
    connection = DenseConnection()

    asyncio.run(gather_chat_sources(connection, root_id, lambda _row: True))

    assert connection.candidate_ids[0] == project_id
    assert len(connection.candidate_ids) == _POST_CHAT_CANDIDATE_LIMIT


def test_gather_chat_sources_keeps_the_event_loop_responsive_during_body_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    release = Event()

    def blocking_normalize(_body: str, *, vision_client: object) -> SimpleNamespace:
        del vision_client
        order.append("normalization_started")
        assert release.wait(timeout=1.0)
        order.append("normalization_finished")
        return SimpleNamespace(text="normalized body")

    monkeypatch.setattr(
        "backend.app.post_chat_ingestion.normalize_post_body",
        blocking_normalize,
    )

    async def exercise() -> None:
        loop = asyncio.get_running_loop()
        timer = Timer(0.2, release.set)
        timer.start()
        loop.call_later(0.01, order.append, "event_loop_progress")
        try:
            sources = await gather_chat_sources(
                _SourceConnection(),
                "post-1",
                lambda _row: True,
            )
            await asyncio.sleep(0)
        finally:
            release.set()
            timer.cancel()
        assert sources[0].post_body == "normalized body"

    asyncio.run(exercise())

    assert order.index("event_loop_progress") < order.index("normalization_finished")


def test_gather_chat_sources_bounds_and_orders_linked_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_id = "00000000-0000-0000-0000-000000000000"
    direct_ids = frozenset(
        f"00000000-0000-0000-0000-{index:012d}" for index in range(1, 21)
    )
    indirect_ids = frozenset(
        f"00000000-0000-0000-0001-{index:012d}" for index in range(1, 21)
    )

    async def fake_find_linked_post_ids(_conn: object, _post_id: str) -> LinkedPostIds:
        return LinkedPostIds(direct=direct_ids, indirect=indirect_ids)

    monkeypatch.setattr(
        "backend.app.post_chat_ingestion.find_linked_post_ids",
        fake_find_linked_post_ids,
    )

    class SourceBudgetConnection:
        def __init__(self) -> None:
            self.candidate_ids: list[str] = []
            self.candidate_query = ""

        async def fetchrow(self, query: str, *_args: object):
            if "from source_post where post_id" not in query:
                return None
            return {
                "post_id": root_id,
                "post_title": "Root post",
                "post_body": "Root body",
                **{
                    field_name: None
                    for field_name in (
                        "source_system_code",
                        "source_record_key",
                        "source_author_code",
                        "source_author_name",
                        "source_company_code",
                        "source_company_name",
                        "source_process_unit_code",
                        "source_process_unit_name",
                        "source_sales_pool_code",
                        "source_sales_pool_name",
                        "source_customer_code",
                        "source_customer_name",
                        "source_project_code",
                        "source_project_name",
                    )
                },
            }

        async def fetch(self, query: str, *args: object):
            if "from source_post where post_id = any" not in query:
                return []
            self.candidate_query = query
            self.candidate_ids = list(args[0])
            return [
                {
                    "post_id": post_id,
                    "post_title": f"Post {post_id}",
                    "post_body": "Body",
                    "visibility_code": "public",
                    "corporate_entity_id": None,
                    **{
                        field_name: None
                        for field_name in (
                            "source_system_code",
                            "source_record_key",
                            "source_author_code",
                            "source_author_name",
                            "source_company_code",
                            "source_company_name",
                            "source_process_unit_code",
                            "source_process_unit_name",
                            "source_sales_pool_code",
                            "source_sales_pool_name",
                            "source_customer_code",
                            "source_customer_name",
                            "source_project_code",
                            "source_project_name",
                        )
                    },
                }
                for post_id in self.candidate_ids
            ]

    conn = SourceBudgetConnection()
    sources = asyncio.run(gather_chat_sources(conn, root_id, lambda _row: True))

    expected_candidates = [*sorted(direct_ids), *sorted(indirect_ids)][:32]
    assert conn.candidate_ids == expected_candidates
    assert "array_position" in conn.candidate_query
    assert [source.post_id for source in sources] == [root_id, *expected_candidates[:7]]
    assert len(sources) == 8


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
                {"message": {"content": "supported\nCITED SOURCES: 1, 9"}},
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


class _ImageFakeConnection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.queries: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
        self.queries.append((query, args))
        cited_ids = set(args[0]) if args else set()
        return [row for row in self.rows if row["post_id"] in cited_ids]


def test_cited_post_images_returns_persisted_captions_for_cited_posts_only() -> None:
    connection = _ImageFakeConnection(
        [
            {
                "post_id": "post-a",
                "unit_index": 2,
                "mime_type": "image/png",
                "description_status_code": "described",
                "extracted_text": "Error code 500 on checkout",
                "caption": "Screenshot of the checkout error",
                "tags": ["screenshot", "error"],
            },
            {
                "post_id": "post-not-cited",
                "unit_index": 0,
                "mime_type": "image/png",
                "description_status_code": "described",
                "extracted_text": "irrelevant",
                "caption": "irrelevant",
                "tags": [],
            },
            {
                "post_id": "post-a",
                "unit_index": 3,
                "mime_type": "image/png",
                "description_status_code": "unavailable",
                "extracted_text": None,
                "caption": None,
                "tags": [],
            },
        ]
    )
    images = asyncio.run(cited_post_images(connection, ["post-a"]))
    assert images == [
        {
            "post_id": "post-a",
            "unit_index": 2,
            "mime_type": "image/png",
            "status_code": "described",
            "extracted_text": "Error code 500 on checkout",
            "caption": "Screenshot of the checkout error",
            "tags": ["screenshot", "error"],
        }
    ]


def test_cited_post_images_with_no_citations_skips_the_query() -> None:
    connection = _ImageFakeConnection([])
    images = asyncio.run(cited_post_images(connection, []))
    assert images == []
    assert connection.queries == []
