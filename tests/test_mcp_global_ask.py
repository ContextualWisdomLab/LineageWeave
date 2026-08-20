from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from backend.app import global_ask
from backend.app.auth import CurrentAccount
from lineageweave.http_client import HttpClientError
from lineageweave.post_chat import ChatAnswer, ChatSourceDocument


ACCOUNT = CurrentAccount(
    user_account_id="account-1",
    external_subject_id="subject-1",
    display_name="Analyst",
    corporate_entity_ids=frozenset({"11111111-1111-1111-1111-111111111111"}),
    permission_codes=frozenset({"post_read"}),
)
PUBLIC = {
    "post_id": "public-post",
    "post_title": "Demo Corp public",
    "post_body": "public evidence",
    "visibility_code": "public",
    "corporate_entity_id": "22222222-2222-2222-2222-222222222222",
    "created_at": 1,
    "relevance_score": 3,
}
UNAUTHORIZED = {
    "post_id": "private-other-corp",
    "post_title": "Demo Corp private",
    "post_body": "secret",
    "visibility_code": "private",
    "corporate_entity_id": "22222222-2222-2222-2222-222222222222",
    "created_at": 2,
    "relevance_score": 99,
}


@dataclass
class FakeClient:
    """Synchronous reason-and-cite client used by the application-service tests."""

    available: bool = True
    answer_value: ChatAnswer = field(
        default_factory=lambda: ChatAnswer("grounded answer", ("public-post", "outside-source"))
    )
    error: Exception | None = None
    session_id: str | None = None
    metadata: dict[str, str] | None = None

    def answer(
        self,
        question: str,
        sources: list[ChatSourceDocument],
        *,
        session_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ChatAnswer:
        if self.error is not None:
            raise self.error
        assert question
        assert len(sources) <= global_ask.MAX_GLOBAL_SOURCES
        self.session_id = session_id
        self.metadata = metadata
        return self.answer_value


class FakeConnection:
    """Captures SQL/arguments and returns deterministic search/fallback rows."""

    def __init__(self, *, search_rows=None, fallback_rows=None) -> None:
        self.search_rows = search_rows or {}
        self.fallback_rows = fallback_rows or []
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, sql: str, *args: object):
        self.calls.append((sql, args))
        if len(args) == 3:
            return self.search_rows.get(str(args[1]), [])
        return self.fallback_rows


def test_extract_search_terms_is_unicode_aware_deduplicated_and_bounded() -> None:
    question = (
        "무엇 Demo demo 고객사 Alpha-Beta 프로젝트와 관련 있나요? "
        + " ".join(f"zed{i}" for i in range(20))
    )
    terms = global_ask.extract_search_terms(question)
    assert terms[:4] == ("demo", "고객사", "alpha-beta", "프로젝트와")
    assert len(terms) == global_ask.MAX_SEARCH_TERMS


def test_validate_global_question_rejects_blank_and_oversized() -> None:
    with pytest.raises(ValueError, match="question is required"):
        global_ask.validate_global_question("   ")
    with pytest.raises(ValueError, match="at most 2000"):
        global_ask.validate_global_question("x" * 2001)


@pytest.mark.asyncio
async def test_global_ask_reuses_rbac_abac_bounds_sources_and_filters_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection(search_rows={"demo": [UNAUTHORIZED, PUBLIC]})

    async def gather(conn_, post_id, can_see_post, vision_client=None, **kwargs):
        assert conn_ is conn
        assert post_id == "public-post"
        assert can_see_post(PUBLIC)
        assert not can_see_post(UNAUTHORIZED)
        assert vision_client is None
        assert kwargs["session_id"] == "lineageweave:post:public-post"
        assert kwargs["metadata"]["post_id"] == "public-post"
        return [
            ChatSourceDocument(
                "public-post",
                "Public",
                "A" * 6000,
                occurred_at="2026-03-10T00:00:00+00:00",
                lineage_relation="anchor",
            ),
            ChatSourceDocument(
                "linked-post",
                "Linked",
                "linked evidence",
                occurred_at="2026-03-03T00:00:00+00:00",
                lineage_relation="direct_lineage",
            ),
            *[ChatSourceDocument(f"extra-{i}", "Extra", "extra") for i in range(10)],
        ]

    monkeypatch.setattr(global_ask, "gather_chat_sources", gather)
    client = FakeClient()
    result = await global_ask.answer_global_question(conn, ACCOUNT, client, "What happened at Demo Corp?")
    assert result.answer_text == "grounded answer"
    assert result.anchor_post_id == "public-post"
    assert result.cited_post_ids == ("public-post",)
    assert result.source_post_ids == (
        "public-post",
        "linked-post",
        "extra-0",
        "extra-1",
        "extra-2",
        "extra-3",
    )
    assert result.cited_posts == ({"post_id": "public-post", "post_title": "Public"},)
    assert result.timeline == (
        {
            "post_id": "linked-post",
            "post_title": "Linked",
            "occurred_at": "2026-03-03T00:00:00+00:00",
            "lineage_relation": "direct_lineage",
        },
        {
            "post_id": "public-post",
            "post_title": "Public",
            "occurred_at": "2026-03-10T00:00:00+00:00",
            "lineage_relation": "anchor",
        },
    )
    sql = conn.calls[0][0]
    assert "visibility_code = 'public'" in sql
    assert "p.corporate_entity_id = any($1::uuid[])" in sql
    assert client.session_id == "lineageweave:post:public-post"
    assert client.metadata == {
        "session_id": "lineageweave:post:public-post",
        "post_id": "public-post",
        "requesting_user_account_id": "account-1",
        "corporate_entity_id": "22222222-2222-2222-2222-222222222222",
    }


@pytest.mark.asyncio
async def test_global_ask_rejects_missing_permission_and_unrelated_fallback() -> None:
    denied = CurrentAccount(**{**ACCOUNT.__dict__, "permission_codes": frozenset()})
    with pytest.raises(global_ask.GlobalAskForbiddenError, match="post_read"):
        await global_ask.answer_global_question(FakeConnection(), denied, FakeClient(), "question")
    assert (
        await global_ask._select_anchor(
            FakeConnection(fallback_rows=[PUBLIC]), ACCOUNT, "specific missing term"
        )
        is None
    )


@pytest.mark.asyncio
async def test_empty_term_question_uses_authorized_recent_fallback() -> None:
    assert (
        await global_ask._select_anchor(FakeConnection(fallback_rows=[PUBLIC]), ACCOUNT, "what?")
        == PUBLIC
    )


def test_bounded_sources_deduplicates_truncates_and_stops() -> None:
    source = ChatSourceDocument("same", "title", "x" * 5000)
    bounded = global_ask._bounded_sources(
        [source, source] + [ChatSourceDocument(str(i), "t", "b") for i in range(10)]
    )
    assert len(bounded) == global_ask.MAX_GLOBAL_SOURCES
    assert len(bounded[0].post_body) == global_ask.MAX_SOURCE_BODY_CHARS
    assert [item.post_id for item in bounded].count("same") == 1


@pytest.mark.asyncio
async def test_global_ask_fails_closed_without_authorized_evidence() -> None:
    with pytest.raises(global_ask.GlobalAskNoEvidenceError):
        await global_ask.answer_global_question(
            FakeConnection(), ACCOUNT, FakeClient(), "unmatched question"
        )


@pytest.mark.asyncio
async def test_global_ask_fails_closed_without_orchestrator() -> None:
    with pytest.raises(global_ask.GlobalAskUnavailableError, match="orchestrator"):
        await global_ask.answer_global_question(
            FakeConnection(fallback_rows=[PUBLIC]), ACCOUNT, FakeClient(available=False), "what?"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [HttpClientError("http"), KeyError("bad"), OSError("io"), TypeError("type"), ValueError("value")],
)
async def test_evidence_retrieval_errors_fail_closed(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    async def gather(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(global_ask, "gather_chat_sources", gather)
    with pytest.raises(global_ask.GlobalAskUnavailableError, match="evidence retrieval"):
        await global_ask.answer_global_question(
            FakeConnection(search_rows={"public": [PUBLIC]}), ACCOUNT, FakeClient(), "public"
        )


@pytest.mark.asyncio
async def test_empty_gathered_sources_is_no_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    async def gather(*_args, **_kwargs):
        return []

    monkeypatch.setattr(global_ask, "gather_chat_sources", gather)
    with pytest.raises(global_ask.GlobalAskNoEvidenceError):
        await global_ask.answer_global_question(
            FakeConnection(search_rows={"public": [PUBLIC]}), ACCOUNT, FakeClient(), "public"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [HttpClientError("http"), KeyError("bad"), OSError("io"), TypeError("type"), ValueError("value")],
)
async def test_reasoning_errors_fail_closed(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    async def gather(*_args, **_kwargs):
        return [ChatSourceDocument("public-post", "Public", "body")]

    monkeypatch.setattr(global_ask, "gather_chat_sources", gather)
    with pytest.raises(global_ask.GlobalAskUnavailableError, match="orchestrator failed"):
        await global_ask.answer_global_question(
            FakeConnection(search_rows={"public": [PUBLIC]}),
            ACCOUNT,
            FakeClient(error=error),
            "public",
        )


@pytest.mark.asyncio
async def test_duplicate_citations_are_deduplicated(monkeypatch: pytest.MonkeyPatch) -> None:
    async def gather(*_args, **_kwargs):
        return [ChatSourceDocument("public-post", "Public", "body")]

    monkeypatch.setattr(global_ask, "gather_chat_sources", gather)
    result = await global_ask.answer_global_question(
        FakeConnection(search_rows={"public": [PUBLIC]}),
        ACCOUNT,
        FakeClient(answer_value=ChatAnswer("answer", ("public-post", "public-post"))),
        "public",
    )
    assert result.cited_post_ids == ("public-post",)
