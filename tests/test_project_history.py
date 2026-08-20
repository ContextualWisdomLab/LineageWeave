"""Contracts for the Buyer project-history timeline."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from backend.app.project_history import (
    ProjectHistoryNotFound,
    fetch_project_history_index,
    fetch_project_history_projection,
)
from lineageweave.project_history import (
    classify_project_event,
    normalize_project_key,
    responsibility_transition_code,
)


class _IndexConnection:
    """Return an aggregate index row without needing a live database."""

    def __init__(self) -> None:
        self.query = ""
        self.args: tuple[object, ...] = ()

    async def fetch(self, query: str, *args: object):
        """Capture the bounded query and return one synthetic index row."""
        self.query = query
        self.args = args
        return [{"project_key": "p-100", "project_name": "Project 100", "event_count": 4}]


class _ProjectionConnection:
    """Return bounded synthetic rows for the projection query sequence."""

    def __init__(self, events, focus=()):
        self.events = list(events)
        self.focus = list(focus)
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        """Serve the event, optional focus, and three child reads in order."""
        self.calls.append((query, args))
        if len(self.calls) == 1:
            return self.events
        if "post_id = $4::uuid" in query:
            return self.focus
        return []


def _event(post_id: str, day: int) -> dict[str, object]:
    """Build one anonymous source event for projection contract tests."""
    return {
        "post_id": post_id,
        "post_title": f"Synthetic event {day}",
        "created_at": datetime(2026, 1, day, tzinfo=timezone.utc),
        "voc_type_code": None,
        "source_stage_code": None,
        "source_detail_state_code": None,
    }


def test_project_identity_is_exact_but_unicode_compatible() -> None:
    """Compatibility forms may normalize; fuzzy project binding may not."""
    assert normalize_project_key("  Ｐ－１００  ") == "p-100"
    assert normalize_project_key("P-100-A") != normalize_project_key("P-100")
    with pytest.raises(ValueError):
        normalize_project_key("   ")


def test_event_display_classification_does_not_create_authority() -> None:
    """The lifecycle label is presentation metadata over an existing post."""
    assert (
        classify_project_event(
            title="Contract awarded",
            source_stage_code=None,
            source_detail_state_code=None,
            voc_type_code=None,
            is_focus=False,
        )
        == "contract_awarded"
    )
    for is_focus in (False, True):
        assert (
            classify_project_event(
                title="Field complaint received",
                source_stage_code=None,
                source_detail_state_code=None,
                voc_type_code="voc",
                is_focus=is_focus,
            )
            == "voc_received"
        )


def test_responsibility_transition_describes_document_evidence_only() -> None:
    """Missing adjacent evidence is a visible evidence gap, not an HR fact."""
    assert responsibility_transition_code(["person:a"], ["person:a"]) == "continuous"
    assert responsibility_transition_code(["person:a"], ["person:b"]) == "handoff"
    assert responsibility_transition_code(["person:a"], []) == "assignment_gap"


def test_project_history_index_is_bounded_and_uses_source_name_priority() -> None:
    connection = _IndexConnection()
    result = asyncio.run(
        fetch_project_history_index(
            connection,
            knowledge_cutoff=datetime(2026, 1, 1, tzinfo=timezone.utc),
            corporate_entity_ids=["corp-1"],
            limit=8,
        )
    )

    assert result == [{"project_key": "p-100", "project_name": "Project 100", "event_count": 4}]
    assert connection.args[-1] == 8
    assert "array_agg(project_name order by display_priority" in connection.query
    assert "nullif(btrim(post.source_project_code), '')" in connection.query
    with pytest.raises(ValueError):
        asyncio.run(
            fetch_project_history_index(
                connection,
                knowledge_cutoff=datetime.now(timezone.utc),
                corporate_entity_ids=[],
                limit=129,
            )
        )


def test_project_history_projection_reads_children_and_keeps_visible_focus() -> None:
    """An in-page focus uses only the already selected visible event IDs."""
    first = _event("00000000-0000-0000-0000-000000000001", 1)
    second = _event("00000000-0000-0000-0000-000000000002", 2)
    connection = _ProjectionConnection([first, second])
    result = asyncio.run(
        fetch_project_history_projection(
            connection,
            project_key="P-100",
            focus_post_id=str(first["post_id"]),
            knowledge_cutoff=datetime.now(timezone.utc),
            corporate_entity_ids=["corp-1"],
            limit=2,
        )
    )

    assert result["focus_event_id"] == str(first["post_id"])
    assert result["event_count"] == 2
    assert len(connection.calls) == 4
    assert connection.calls[0][1][-1] == 3


def test_project_history_projection_appends_authorized_focus_beyond_page() -> None:
    """A focused event beyond a page is fetched and retained deterministically."""
    first = _event("00000000-0000-0000-0000-000000000001", 1)
    second = _event("00000000-0000-0000-0000-000000000002", 2)
    third = _event("00000000-0000-0000-0000-000000000003", 3)
    connection = _ProjectionConnection([first, second, third], [third])
    result = asyncio.run(
        fetch_project_history_projection(
            connection,
            project_key="P-100",
            focus_post_id=str(third["post_id"]),
            knowledge_cutoff=datetime.now(timezone.utc),
            corporate_entity_ids=[],
            limit=2,
        )
    )

    assert result["truncated"] is True
    assert [event["source_post_id"] for event in result["events"]] == [
        str(first["post_id"]),
        str(third["post_id"]),
    ]
    assert len(connection.calls) == 5


def test_project_history_projection_focus_page_one_and_empty_cases_fail_closed() -> None:
    """The one-row page and missing authorized evidence remain bounded and explicit."""
    first = _event("00000000-0000-0000-0000-000000000001", 1)
    focus = _event("00000000-0000-0000-0000-000000000099", 2)
    connection = _ProjectionConnection([first], [focus])
    result = asyncio.run(
        fetch_project_history_projection(
            connection,
            project_key="P-100",
            focus_post_id="00000000-0000-0000-0000-000000000099",
            knowledge_cutoff=datetime.now(timezone.utc),
            corporate_entity_ids=[],
            limit=1,
        )
    )
    assert result["events"][0]["source_post_id"] == str(focus["post_id"])

    with pytest.raises(ProjectHistoryNotFound):
        asyncio.run(
            fetch_project_history_projection(
                _ProjectionConnection([]),
                project_key="P-100",
                focus_post_id=None,
                knowledge_cutoff=datetime.now(timezone.utc),
                corporate_entity_ids=[],
            )
        )
    with pytest.raises(ProjectHistoryNotFound):
        asyncio.run(
            fetch_project_history_projection(
                _ProjectionConnection([first], []),
                project_key="P-100",
                focus_post_id="00000000-0000-0000-0000-000000000099",
                knowledge_cutoff=datetime.now(timezone.utc),
                corporate_entity_ids=[],
                limit=1,
            )
        )
    with pytest.raises(ValueError):
        asyncio.run(
            fetch_project_history_projection(
                connection,
                project_key="P-100",
                focus_post_id=None,
                knowledge_cutoff=datetime.now(timezone.utc),
                corporate_entity_ids=[],
                limit=0,
            )
        )
