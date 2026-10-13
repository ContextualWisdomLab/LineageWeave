"""Live generation/capture authorization regressions; synthetic fixtures only."""
import asyncio
from contextlib import nullcontext

import pytest
from fastapi import HTTPException

from backend.app import main, post_chat_ingestion as chat
from backend.app.auth import CurrentAccount
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.post_chat import ChatAnswer, ChatSourceDocument

_ACCOUNT = CurrentAccount(user_account_id="synthetic", external_subject_id="synthetic",
                          display_name="Synthetic", preferred_locale="en",
                          corporate_entity_ids=frozenset({"corp-a"}),
                          process_unit_ids=frozenset({"pu-a"}),
                          permission_codes=frozenset({"post_read"}))


def _row(post_id="focal", **changes):
    return dict(post_id=post_id, post_title="Synthetic title", post_body="Synthetic body",
                visibility_code="private", corporate_entity_id="corp-a", process_unit_id="pu-a",
                source_draft_code=None, source_deleted_flag=None, source_customer_code="Synthetic hint",
                **changes)


class _SourceConnection:
    """Expose current source rows while retaining exact capture SQL."""

    def __init__(self, root, neighbors):
        self.root, self.neighbors = root, neighbors
        self.queries = []

    async def fetchrow(self, sql, *_args):
        self.queries.append(sql)
        return self.root

    async def fetch(self, sql, *_args):
        self.queries.append(sql)
        return self.neighbors if "from source_post where post_id = any" in sql else []


@pytest.mark.parametrize("denied", ["focal_abac", "focal_draft", "focal_deleted", "linked_abac", "linked_draft", "linked_deleted", "none"])
def test_capture_rechecks_focal_and_linked_authorization_before_body_use(monkeypatch, denied):
    """Exact focal/linked positives pair with revocation, draft and deletion negatives."""
    root, neighbor = _row(), _row("linked")
    target = root if denied.startswith("focal") else neighbor
    if denied.endswith("abac"):
        target["corporate_entity_id"] = "corp-b"
    if denied.endswith("draft"):
        target["source_draft_code"] = "DRAFT"
    if denied.endswith("deleted"):
        target["source_deleted_flag"] = "DELETED"
    conn = _SourceConnection(root, [neighbor])

    async def linked(*_args):
        return chat.LinkedPostIds(frozenset({"linked"}), frozenset())

    monkeypatch.setattr(chat, "find_linked_post_ids", linked)
    sources = asyncio.run(chat.gather_chat_sources(conn, "focal", lambda row: main._can_see_post(_ACCOUNT, row)))
    expected = [] if denied.startswith("focal") else (["focal", "linked"] if denied == "none" else ["focal"])
    assert [source.post_id for source in sources] == expected
    source_queries = [q for q in conn.queries if "from source_post where post_id" in q]
    for sql in source_queries:
        assert "visibility_code" in sql and "process_unit_id" in sql
        assert SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post") in sql


class _LiveConnection:
    """Query-aware fixture for actual persistence and final authorization."""

    def __init__(self):
        self.revoked = False
        self.queries = []
        self.depth = 0

    def transaction(self):
        conn = self

        class Transaction:
            async def __aenter__(self):
                conn.depth += 1

            async def __aexit__(self, *_exc):
                conn.depth -= 1
        return Transaction()

    async def execute(self, sql, *_args):
        assert self.depth > 0
        self.queries.append(sql)
        return "OK"

    async def fetchrow(self, sql, *_args):
        self.queries.append(sql)
        if "post_chat_authorization_receipt" in sql:
            return None
        assert self.depth > 0
        return {"question_text": "Synthetic question", "answer_text": "Synthetic answer"}

    async def fetch(self, sql, *_args):
        self.queries.append(sql)
        if "for share" in sql.lower():
            assert self.depth > 0
            return [{"post_id": "focal"}] if self.revoked else [{"post_id": p} for p in ("focal", "linked")]
        return [{"cited_post_id": "focal", "post_title": "Synthetic title"}]


class _Pool:
    """Track connection lifecycle for the no-network-under-lock invariant."""

    def __init__(self, conn):
        self.conn = conn
        self.acquired = 0

    def acquire(self):
        pool = self

        class Acquire:
            async def __aenter__(self):
                pool.acquired += 1
                return pool.conn

            async def __aexit__(self, *_exc):
                pool.acquired -= 1
        return Acquire()


@pytest.mark.parametrize("revoke", [True, False])
def test_live_answer_reauthorizes_all_sources_after_generation_before_write_or_response(monkeypatch, revoke):
    """An uncited source revoked during generation denies the entire initial answer."""
    conn = _LiveConnection()
    pool = _Pool(conn)

    async def visible(*_args):
        return _row()

    async def gathered(*_args, **_kwargs):
        return [ChatSourceDocument(
            p, "Synthetic title", "Synthetic body",
            evidence_facts=("Keyman mention: Synthetic Keyman [provenance=post_person_mention]",),
        ) for p in ("focal", "linked")]

    async def activity(*_args):
        assert conn.depth == 0

    class Client:
        available = True

        def answer(self, *_args):
            assert conn.depth == 0 and pool.acquired == 0
            conn.revoked = revoke
            return ChatAnswer("Synthetic answer", ("focal",))

    monkeypatch.setattr(main, "_load_visible_post", visible)
    monkeypatch.setattr(main, "build_post_llm_metadata", lambda *_args: {})
    monkeypatch.setattr(main, "use_llm_metadata", lambda *_args: nullcontext())
    monkeypatch.setattr(main, "traced", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(main, "_post_chat_client", Client)
    monkeypatch.setattr(main, "_vision_client", object)
    monkeypatch.setattr(main, "gather_chat_sources", gathered)
    monkeypatch.setattr(main, "publish_activity_event", activity)
    call = main.chat_about_post("focal", main.ChatRequest(question="Synthetic question"), _ACCOUNT, pool, object())
    if revoke:
        with pytest.raises(HTTPException) as error:
            asyncio.run(call)
        assert error.value.status_code == 409
        assert not any("insert into" in q for q in conn.queries)
    else:
        result = asyncio.run(call)
        assert result["answer_text"] == "Synthetic answer"
        assert result["source_post_ids"] == ["focal", "linked"]
        assert result["cited_post_evidence"] == [{
            "post_id": "focal",
            "facts": [{"kind": "semantic_keyman", "text": "Keyman mention: Synthetic Keyman"}],
        }]
        assert any("insert into post_chat_source" in q for q in conn.queries)
    assert any("for share" in q.lower() for q in conn.queries)
    assert conn.depth == 0 and pool.acquired == 0
