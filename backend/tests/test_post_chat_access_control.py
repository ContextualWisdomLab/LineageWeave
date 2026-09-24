"""Service-free access-control regression for the post-chat endpoints.

``backend/tests/test_api.py::test_other_corp_private_post_chat_is_forbidden``
covers the same contract end to end, but that module is skipped unless
PostgreSQL, Keycloak, and Valkey are all reachable, and the Tests workflow
provides only PostgreSQL. This module drives the real FastAPI routes for
``GET``/``POST /api/posts/{post_id}/chat`` through ``TestClient`` with an
in-memory pool and an overridden account dependency, so it runs in CI.

Boundary: the fake pool returns the post row for any query, so this checks
the handler-level ABAC gate (``_load_visible_post`` -> ``_can_see_post``), not
the SQL eligibility fragment or token verification.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.activity_stream import get_valkey
from backend.app.auth import CurrentAccount, get_current_account
from backend.app.db import get_pool

_OWN_ENTITY_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_OTHER_ENTITY_ID = "bbbbbbbb-0000-0000-0000-000000000002"
_POST_ID = "cccccccc-0000-0000-0000-000000000003"
_UNRELATED_POST_ID = "dddddddd-0000-0000-0000-000000000004"


def _private_post_row(corporate_entity_id: str) -> dict[str, object]:
    """One private ``source_post`` row shaped like ``_load_visible_post``'s select."""
    return {
        "post_id": _POST_ID,
        "post_title": "Seal failure",
        "post_body": "The seal failed during the acceptance test.",
        "voc_type_code": "issue",
        "visibility_code": "private",
        "corporate_entity_id": corporate_entity_id,
        "process_unit_id": None,
        "created_at": None,
        "author_account_id": None,
        "source_process_unit_code": None,
        "source_author_code": None,
        "source_company_code": None,
        "source_customer_code": None,
        "source_project_code": None,
        "source_sales_pool_code": None,
        "corporate_entity_code": "CUSTOMER",
    }


class _Connection:
    def __init__(self, row: dict[str, object]) -> None:
        self.row = row
        self.queries: list[str] = []

    async def fetchrow(self, query: str, *_args: object) -> dict[str, object]:
        self.queries.append(query)
        return self.row


class _Pool:
    def __init__(self, row: dict[str, object]) -> None:
        self.connection = _Connection(row)

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


class _ChatStoreSpy:
    """Records every chat-store read the handlers make."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def fetch_persisted_chats(self, _conn, post_id: str) -> list[dict[str, str]]:
        self.calls.append(("fetch_persisted_chats", post_id))
        return [{"question_text": "stored question", "answer_text": "stored answer"}]

    async def fetch_persisted_chat(self, _conn, post_id: str, _question: str) -> dict[str, object]:
        self.calls.append(("fetch_persisted_chat", post_id))
        return {"answer_text": "stored answer", "cited_post_ids": [post_id], "cited_posts": []}


@pytest.fixture
def chat_store(monkeypatch) -> _ChatStoreSpy:
    spy = _ChatStoreSpy()
    monkeypatch.setattr(main, "fetch_persisted_chats", spy.fetch_persisted_chats)
    monkeypatch.setattr(main, "fetch_persisted_chat", spy.fetch_persisted_chat)
    return spy


@pytest.fixture
def analyst_client():
    """TestClient whose caller is an analyst bound only to ``_OWN_ENTITY_ID``.

    No ``with`` block: the lifespan (database pool, OIDC discovery) is not
    started; the route dependencies are overridden instead.
    """
    account = CurrentAccount(
        user_account_id="analyst-account",
        external_subject_id="analyst-subject",
        display_name="Analyst",
        preferred_locale=None,
        corporate_entity_ids=frozenset({_OWN_ENTITY_ID}),
        process_unit_ids=frozenset(),
        permission_codes=frozenset({"post_read"}),
    )
    main.app.dependency_overrides[get_current_account] = lambda: account
    main.app.dependency_overrides[get_valkey] = lambda: None
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.pop(get_current_account, None)
        main.app.dependency_overrides.pop(get_valkey, None)
        main.app.dependency_overrides.pop(get_pool, None)


def _use_pool(row: dict[str, object]) -> _Pool:
    pool = _Pool(row)
    main.app.dependency_overrides[get_pool] = lambda: pool
    return pool


def test_own_corp_private_post_chat_is_readable(analyst_client, chat_store) -> None:
    """An analyst bound to the post's owning entity reads and asks its chat."""
    _use_pool(_private_post_row(_OWN_ENTITY_ID))

    listed = analyst_client.get(f"/api/posts/{_POST_ID}/chat")
    assert listed.status_code == 200
    assert listed.json()["exchanges"] == [
        {"question_text": "stored question", "answer_text": "stored answer"}
    ]

    posted = analyst_client.post(f"/api/posts/{_POST_ID}/chat", json={"question": "what happened"})
    assert posted.status_code == 200
    assert posted.json()["answer_text"] == "stored answer"

    assert chat_store.calls == [
        ("fetch_persisted_chats", _POST_ID),
        ("fetch_persisted_chat", _POST_ID),
    ]


def test_post_chat_lookup_does_not_authorize_a_different_post(analyst_client, chat_store) -> None:
    """The pool double must preserve ``WHERE post_id = $1`` identity semantics."""
    row = _private_post_row(_OWN_ENTITY_ID)
    row["post_id"] = _UNRELATED_POST_ID
    pool = _use_pool(row)

    listed = analyst_client.get(f"/api/posts/{_POST_ID}/chat")

    assert listed.status_code == 404
    assert chat_store.calls == []
    assert len(pool.connection.queries) == 1
    assert "from source_post" in pool.connection.queries[0]


def test_other_corp_private_post_chat_get_is_forbidden(analyst_client, chat_store) -> None:
    """GET chat on another company's private post is 403 and never reads the store."""
    pool = _use_pool(_private_post_row(_OTHER_ENTITY_ID))

    listed = analyst_client.get(f"/api/posts/{_POST_ID}/chat")

    assert listed.status_code == 403
    assert "stored answer" not in listed.text
    assert chat_store.calls == []
    assert len(pool.connection.queries) == 1
    assert "from source_post" in pool.connection.queries[0]


def test_other_corp_private_post_chat_post_is_forbidden(analyst_client, chat_store) -> None:
    """POST chat on another company's private post is 403 and never reads the store."""
    pool = _use_pool(_private_post_row(_OTHER_ENTITY_ID))

    posted = analyst_client.post(f"/api/posts/{_POST_ID}/chat", json={"question": "what happened"})

    assert posted.status_code == 403
    assert "stored answer" not in posted.text
    assert chat_store.calls == []
    assert len(pool.connection.queries) == 1
    assert "from source_post" in pool.connection.queries[0]
