"""Authorization-bound project-history query tests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.app.project_history import (
    ProjectHistoryRequestError,
    fetch_project_history_projection,
)


class _Connection:
    """Record projection queries and return one synthetic visible event."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        """Return the minimum rows required by each bounded query."""

        self.calls.append((" ".join(query.split()), args))
        if "select post.post_id, post.post_title" in " ".join(query.split()):
            return [
                {
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "post_title": "Synthetic project record",
                    "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "event_occurred_at": datetime(2025, 12, 20, tzinfo=timezone.utc),
                    "voc_type_code": None,
                    "source_stage_code": "observed-stage",
                    "source_detail_state_code": None,
                }
            ]
        return []


def test_project_history_query_binds_corporate_and_process_scopes() -> None:
    """Private project evidence must bind both dimensions before child reads."""

    connection = _Connection()
    result = asyncio.run(
        fetch_project_history_projection(
            connection,
            project_key="P-100",
            focus_post_id=None,
            knowledge_cutoff=datetime(2026, 2, 1, tzinfo=timezone.utc),
            corporate_entity_ids=["corp-1"],
            process_unit_ids=["pu-1"],
        )
    )
    event_query, event_args = connection.calls[0]
    assert "post.process_unit_id::text = any($3::text[])" in event_query
    assert "coalesce(post.event_occurred_at, post.created_at)" in event_query
    assert event_args[1:3] == (["corp-1"], ["pu-1"])
    assert result["events"][0]["event_type_code"] == "source_recorded"
    assert result["events"][0]["occurred_at"] == "2025-12-20T00:00:00Z"
    assert result["events"][0]["time_basis_code"] == "document_time"


def test_project_history_query_uses_the_same_ascii_edge_whitespace_as_python() -> None:
    """SQL and Python must normalize tab-delimited source keys identically."""

    connection = _Connection()
    asyncio.run(
        fetch_project_history_projection(
            connection,
            project_key="\tP-100\n",
            focus_post_id=None,
            knowledge_cutoff=datetime(2026, 2, 1, tzinfo=timezone.utc),
            corporate_entity_ids=[],
            process_unit_ids=[],
        )
    )
    event_query, event_args = connection.calls[0]
    assert "btrim(normalize(coalesce(post.source_project_code, ''), NFKC), E'" in event_query
    assert event_args[0] == "p-100"


def test_project_history_rejects_invalid_request_parameters_explicitly() -> None:
    """Caller input errors use the request-error type, not internal ValueError."""

    connection = _Connection()
    try:
        asyncio.run(
            fetch_project_history_projection(
                connection,
                project_key=" ",
                focus_post_id=None,
                knowledge_cutoff=datetime(2026, 2, 1, tzinfo=timezone.utc),
                corporate_entity_ids=[],
                process_unit_ids=[],
            )
        )
    except ProjectHistoryRequestError:
        pass
    else:
        raise AssertionError("blank project key was accepted")


def test_truncated_focus_does_not_claim_a_responsibility_transition_across_omitted_events() -> None:
    """A retained focus event loses its transition when hidden events break adjacency."""

    class _TruncatedConnection:
        async def fetch(self, query: str, *args: object):
            compact_query = " ".join(query.split())
            early = {
                "post_id": "00000000-0000-0000-0000-000000000001",
                "post_title": "Early record",
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "event_occurred_at": None,
                "voc_type_code": None,
                "source_stage_code": None,
                "source_detail_state_code": None,
            }
            omitted = {
                "post_id": "00000000-0000-0000-0000-000000000002",
                "post_title": "Omitted record",
                "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
                "event_occurred_at": None,
                "voc_type_code": None,
                "source_stage_code": None,
                "source_detail_state_code": None,
            }
            focus = {
                "post_id": "00000000-0000-0000-0000-000000000003",
                "post_title": "Focus record",
                "created_at": datetime(2026, 1, 3, tzinfo=timezone.utc),
                "event_occurred_at": None,
                "voc_type_code": None,
                "source_stage_code": None,
                "source_detail_state_code": None,
            }
            if "post.post_id = $5::uuid" in compact_query:
                return [focus]
            if "limit $5" in compact_query:
                return [early, omitted, focus]
            if "from post_summary_role" in compact_query:
                return [
                    {
                        "post_id": early["post_id"],
                        "actor_name": "Early owner",
                        "responsibility": "Own early work",
                        "actor_type_code": "prov_person",
                        "affiliated_organization_name": None,
                        "cataloged_person_id": None,
                        "cataloged_team_id": None,
                        "cataloged_corporate_entity_id": None,
                    },
                    {
                        "post_id": focus["post_id"],
                        "actor_name": "Focus owner",
                        "responsibility": "Own focus work",
                        "actor_type_code": "prov_person",
                        "affiliated_organization_name": None,
                        "cataloged_person_id": None,
                        "cataloged_team_id": None,
                        "cataloged_corporate_entity_id": None,
                    },
                ]
            return []

    result = asyncio.run(
        fetch_project_history_projection(
            _TruncatedConnection(),
            project_key="P-100",
            focus_post_id="00000000-0000-0000-0000-000000000003",
            knowledge_cutoff=datetime(2026, 2, 1, tzinfo=timezone.utc),
            corporate_entity_ids=["corp-1"],
            process_unit_ids=["pu-1"],
            limit=2,
        )
    )

    assert [event["event_id"] for event in result["events"]] == [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000003",
    ]
    assert result["events"][-1]["responsibility_transition_code"] is None
