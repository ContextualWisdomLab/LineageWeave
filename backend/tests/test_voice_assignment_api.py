"""API-boundary tests for evidence-backed additional Voice assignments."""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

import pytest
from fastapi import HTTPException

from backend.app import main
from backend.app.auth import CurrentAccount

POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
EVIDENCE_POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"


class _Pool:
    """Provide one connection context for the route contract test."""

    @asynccontextmanager
    async def acquire(self):
        yield object()


def _account(*permissions: str) -> CurrentAccount:
    """Return a synthetic account scoped to the test's permission case."""
    return CurrentAccount(
        user_account_id="synthetic-account",
        external_subject_id="synthetic-subject",
        display_name="Synthetic reviewer",
        preferred_locale=None,
        corporate_entity_ids=frozenset({"synthetic-corporation"}),
        process_unit_ids=frozenset({"synthetic-unit"}),
        permission_codes=frozenset(permissions),
    )


@pytest.mark.anyio
async def test_additional_voice_requires_both_posts_visible_and_returns_persisted_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The route persists only after target and evidence scope checks pass."""
    visible_posts: list[str] = []
    persisted: list[dict[str, str]] = []
    published: list[tuple[object, ...]] = []
    evidence_id = str(UUID(EVIDENCE_POST_ID))
    assignment = {
        "code": "vops",
        "label": "Voice of Process",
        "is_primary": False,
        "truth_status_code": "truth_observed",
    }

    async def load_visible(post_id, _account, _pool):
        visible_posts.append(post_id)
        return {"post_id": post_id}

    async def persist(_conn, **values):
        persisted.append(values)

    async def load_assignments(_conn, post_id):
        assert post_id == POST_ID
        return [assignment]

    async def publish(*values):
        published.append(values)

    monkeypatch.setattr(main, "_load_visible_post", load_visible)
    monkeypatch.setattr(main, "persist_additional_voice_assignment", persist)
    monkeypatch.setattr(main, "_load_post_voice_types", load_assignments)
    monkeypatch.setattr(main, "publish_activity_event", publish)

    result = await main.create_post_voice_assignment(
        POST_ID,
        main.CreatePostVoiceAssignmentRequest(
            voice_type_code="vops",
            truth_status_code="truth_observed",
            evidence_post_id=UUID(EVIDENCE_POST_ID),
        ),
        _account("post_admin", "post_read"),
        _Pool(),
        object(),
    )

    assert visible_posts == [POST_ID, evidence_id]
    assert persisted == [
        {
            "post_id": POST_ID,
            "voice_type_code": "vops",
            "truth_status_code": "truth_observed",
            "evidence_post_id": evidence_id,
        }
    ]
    assert result == assignment
    assert not {"assertion_id", "provenance_assertion_id"}.intersection(result)
    assert len(published) == 1


@pytest.mark.anyio
async def test_hidden_evidence_post_fails_before_voice_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inaccessible evidence Post cannot create a target Voice claim."""
    visible_posts: list[str] = []

    async def load_visible(post_id, _account, _pool):
        visible_posts.append(post_id)
        if post_id == str(UUID(EVIDENCE_POST_ID)):
            raise HTTPException(status_code=404)
        return {"post_id": post_id}

    async def forbidden_persist(*_args, **_kwargs):
        raise AssertionError("hidden evidence must fail before persistence")

    monkeypatch.setattr(main, "_load_visible_post", load_visible)
    monkeypatch.setattr(main, "persist_additional_voice_assignment", forbidden_persist)

    with pytest.raises(HTTPException) as caught:
        await main.create_post_voice_assignment(
            POST_ID,
            main.CreatePostVoiceAssignmentRequest(
                voice_type_code="vops",
                truth_status_code="truth_observed",
                evidence_post_id=UUID(EVIDENCE_POST_ID),
            ),
            _account("post_admin", "post_read"),
            _Pool(),
            object(),
        )

    assert caught.value.status_code == 404
    assert visible_posts == [POST_ID, str(UUID(EVIDENCE_POST_ID))]


@pytest.mark.anyio
async def test_non_admin_cannot_attempt_additional_voice(monkeypatch: pytest.MonkeyPatch) -> None:
    """Accounts without post administration cannot probe post visibility."""

    async def forbidden(*_args, **_kwargs):
        raise AssertionError("permission denial must precede post lookup")

    monkeypatch.setattr(main, "_load_visible_post", forbidden)

    with pytest.raises(HTTPException) as caught:
        await main.create_post_voice_assignment(
            POST_ID,
            main.CreatePostVoiceAssignmentRequest(
                voice_type_code="vops",
                truth_status_code="truth_observed",
                evidence_post_id=UUID(POST_ID),
            ),
            _account("post_read"),
            _Pool(),
            object(),
        )

    assert caught.value.status_code == 403
