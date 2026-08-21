"""The project-history HTTP contract is authorized, bounded, and non-leaking."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
import pytest

from backend.app.auth import CurrentAccount
from backend.app import project_history_api as api
from backend.app.project_history import ProjectHistoryNotFound
from lineageweave.project_history import build_project_history_projection


class _Acquire:
    """Minimal asynchronous pool acquisition context."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    async def __aenter__(self) -> object:
        return self.connection

    async def __aexit__(self, *args: object) -> None:
        return None


class _Pool:
    """Record whether the endpoint acquired a database connection."""

    def __init__(self) -> None:
        self.connection = object()
        self.acquired = False

    def acquire(self) -> _Acquire:
        """Return one asynchronous acquisition context."""

        self.acquired = True
        return _Acquire(self.connection)


def _account(*permissions: str) -> CurrentAccount:
    """Return one provisioned account with a deterministic ABAC scope."""

    return CurrentAccount(
        user_account_id="account-1",
        external_subject_id="subject-1",
        display_name="Buyer",
        preferred_locale="en",
        corporate_entity_ids=frozenset({"corp-1"}),
        permission_codes=frozenset(permissions),
    )


def test_endpoint_rejects_missing_permission_before_database_access() -> None:
    """A valid token without post_read cannot probe project existence."""

    pool = _Pool()
    with pytest.raises(HTTPException) as captured:
        asyncio.run(
            api.read_project_history(
                project_key="P-100",
                focus_post_id=None,
                knowledge_cutoff=None,
                limit=64,
                account=_account(),
                pool=pool,  # type: ignore[arg-type]
            )
        )
    assert captured.value.status_code == 403
    assert pool.acquired is False


def test_endpoint_rejects_invalid_cutoff_before_database_access() -> None:
    """Malformed cutoff text fails without issuing an evidence query."""

    pool = _Pool()
    with pytest.raises(HTTPException) as captured:
        asyncio.run(
            api.read_project_history(
                project_key="P-100",
                focus_post_id=None,
                knowledge_cutoff="not-a-clock",
                limit=64,
                account=_account("post_read"),
                pool=pool,  # type: ignore[arg-type]
            )
        )
    assert captured.value.status_code == 422
    assert pool.acquired is False


def test_cutoff_defaults_to_utc_when_omitted() -> None:
    """A live project-history request gets an explicit UTC knowledge clock."""

    cutoff = api._parse_knowledge_cutoff(None)
    assert cutoff.tzinfo == timezone.utc


def test_endpoint_maps_invalid_projection_request_to_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository validation failures become a client error, not a 500."""

    async def invalid(*args: object, **kwargs: object) -> dict[str, Any]:
        raise ValueError("invalid project history")

    monkeypatch.setattr(api, "fetch_project_history_projection", invalid)
    with pytest.raises(HTTPException) as captured:
        asyncio.run(
            api.read_project_history(
                project_key="P-100",
                focus_post_id=None,
                knowledge_cutoff="2026-01-31T23:59:59Z",
                limit=64,
                account=_account("post_read"),
                pool=_Pool(),  # type: ignore[arg-type]
            )
        )
    assert captured.value.status_code == 422


def test_endpoint_maps_hidden_and_missing_history_to_the_same_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The response never distinguishes absent project evidence from hidden evidence."""

    async def missing(*args: object, **kwargs: object) -> dict[str, Any]:
        raise ProjectHistoryNotFound("P-100")

    monkeypatch.setattr(api, "fetch_project_history_projection", missing)
    with pytest.raises(HTTPException) as captured:
        asyncio.run(
            api.read_project_history(
                project_key="P-100",
                focus_post_id=UUID("00000000-0000-0000-0000-000000000100"),
                knowledge_cutoff="2026-01-31T23:59:59Z",
                limit=64,
                account=_account("post_read"),
                pool=_Pool(),  # type: ignore[arg-type]
            )
        )
    assert captured.value.status_code == 404
    assert captured.value.detail == "project history not found"


def test_endpoint_passes_exact_scope_cutoff_focus_and_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The repository receives only the authenticated scope and parsed clock."""

    captured: dict[str, object] = {}
    expected = {
        "contract_version": 1,
        "project_key": "P-100",
        "normalized_project_key": "p-100",
        "project_name": "Project 100",
        "focus_event_id": "00000000-0000-0000-0000-000000000100",
        "time_basis_code": "document_time",
        "event_count": 0,
        "distinct_observed_actor_count": 0,
        "truncated": False,
        "events": [],
    }

    async def found(connection: object, **kwargs: object) -> dict[str, Any]:
        captured["connection"] = connection
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(api, "fetch_project_history_projection", found)
    pool = _Pool()
    result = asyncio.run(
        api.read_project_history(
            project_key="P-100",
            focus_post_id=UUID("00000000-0000-0000-0000-000000000100"),
            knowledge_cutoff="2026-01-31T23:59:59Z",
            limit=32,
            account=_account("post_read"),
            pool=pool,  # type: ignore[arg-type]
        )
    )

    assert result == expected
    assert captured["connection"] is pool.connection
    assert captured["project_key"] == "P-100"
    assert captured["focus_post_id"] == "00000000-0000-0000-0000-000000000100"
    assert captured["knowledge_cutoff"] == datetime(
        2026,
        1,
        31,
        23,
        59,
        59,
        tzinfo=timezone.utc,
    )
    assert captured["corporate_entity_ids"] == ["corp-1"]
    assert captured["limit"] == 32


def test_real_projection_builder_matches_the_strict_http_contract() -> None:
    """The repository builder must emit the exact response shape the endpoint validates."""

    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id="post-1",
        event_rows=[
            {
                "post_id": "post-1",
                "post_title": "Contract awarded",
                "created_at": datetime(2026, 1, 1, 9, tzinfo=timezone.utc),
                "voc_type_code": "vom",
                "source_stage_code": "award",
                "source_detail_state_code": None,
            }
        ],
        match_rows=[
            {
                "post_id": "post-1",
                "match_kind_code": "source_project_code",
                "matched_value": "P-100",
                "confidence": None,
                "ontology_iri": None,
                "provenance": "source_post.source_project_code",
            }
        ],
        role_rows=[
            {
                "post_id": "post-1",
                "actor_name": "Demo Analyst",
                "responsibility": "Own the event",
                "actor_type_code": "prov_person",
                "affiliated_organization_name": "Demo Organization",
                "cataloged_person_id": "person-1",
                "cataloged_team_id": None,
                "cataloged_corporate_entity_id": None,
            }
        ],
        edge_rows=[],
    )

    validated = api.ProjectHistoryProjection.model_validate(projection)
    assert validated.normalized_project_key == "p-100"
    assert validated.events[0].source_post_id == "post-1"
