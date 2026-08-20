"""Unit-level branch coverage for the bounded project-history projection."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest

from backend.app.project_history import _bounded_limit, fetch_project_history

UTC = timezone.utc


class FakeConnection:
    """Return deterministic row batches for consecutive ``fetch`` calls."""

    def __init__(self, *responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.queries: list[str] = []

    async def fetch(self, query: str, *_args: object) -> list[dict[str, Any]]:
        self.queries.append(query)
        return self.responses.pop(0)


def test_bounded_limit_and_empty_project_key_fail_closed() -> None:
    assert _bounded_limit(0) == 1
    assert _bounded_limit(999) == 500
    with pytest.raises(ValueError, match="must not be empty"):
        asyncio.run(fetch_project_history(FakeConnection(), "  ", []))


def test_empty_visible_history_does_not_disclose_project_name() -> None:
    payload = asyncio.run(
        fetch_project_history(FakeConnection([], []), "SECRET-PROJECT", [])
    )
    assert payload == {
        "project_key": "SECRET-PROJECT",
        "project_name": "SECRET-PROJECT",
        "events": [],
        "relations": [],
        "responsibility_assignments": [],
        "handover_gaps": [],
        "truncated": False,
        "evidence_boundary": "authorized_source_posts_only",
    }


def test_projection_marks_every_bounded_channel_and_serializes_confidence() -> None:
    event_rows = [
        {
            "project_history_event_id": "event-visible",
            "project_key": "P-1",
            "project_name": "Project One",
            "event_type_code": "project_event_voc",
            "event_type_label": "VOC received",
            "event_title": "Visible VOC",
            "event_start_at": datetime(2026, 2, 1, tzinfo=UTC),
            "event_end_at": None,
            "evidence_post_id": "post-voc",
            "evidence_post_title": "VOC source",
        },
        {
            "project_history_event_id": "event-over-limit",
            "project_key": "P-1",
            "project_name": "Project One",
            "event_type_code": "project_event_rebid",
            "event_type_label": "Rebid",
            "event_title": "Over limit",
            "event_start_at": datetime(2026, 3, 1, tzinfo=UTC),
            "event_end_at": None,
            "evidence_post_id": "post-rebid",
            "evidence_post_title": "Rebid source",
        },
    ]
    relation_rows = [
        {
            "source_project_history_event_id": "event-visible",
            "target_project_history_event_id": "event-visible",
            "relation_type_code": "project_relation_related_to",
            "relation_type_label": "Related to",
            "evidence_post_id": f"relation-post-{index}",
            "evidence_post_title": f"Relation source {index}",
            "relation_confidence": 0.5 if index == 0 else None,
        }
        for index in range(9)
    ]
    assignment_rows = [
        {
            "project_responsibility_assignment_id": "assignment-visible",
            "project_key": "P-1",
            "project_name": "Project One",
            "cataloged_person_id": "person-visible",
            "person_name": "Visible Owner",
            "responsibility_role_code": "project_role_service",
            "responsibility_role_label": "Service",
            "valid_from": datetime(2026, 1, 1, tzinfo=UTC),
            "valid_to": None,
            "evidence_post_id": "post-voc",
            "evidence_post_title": "VOC source",
        },
        {
            "project_responsibility_assignment_id": "assignment-over-limit",
            "project_key": "P-1",
            "project_name": "Project One",
            "cataloged_person_id": "person-hidden",
            "person_name": "Over Limit",
            "responsibility_role_code": "project_role_sales",
            "responsibility_role_label": "Sales",
            "valid_from": datetime(2026, 2, 1, tzinfo=UTC),
            "valid_to": None,
            "evidence_post_id": "post-over-limit",
            "evidence_post_title": "Over limit source",
        },
    ]
    payload = asyncio.run(
        fetch_project_history(
            FakeConnection(event_rows, relation_rows, assignment_rows),
            "P-1",
            ["corp-1"],
            limit=1,
        )
    )

    assert payload["truncated"] is True
    assert len(payload["events"]) == 1
    assert len(payload["relations"]) == 8
    assert payload["relations"][0]["relation_confidence"] == 0.5
    assert payload["relations"][1]["relation_confidence"] is None
    assert payload["relations"][0]["causal"] is False
    assert len(payload["responsibility_assignments"]) == 1
    assert payload["responsibility_assignments"][0]["valid_to"] is None
