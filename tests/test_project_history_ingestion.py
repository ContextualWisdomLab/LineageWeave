"""Authorization-bound project-history query tests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.app.project_history import fetch_project_history_projection


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
    assert event_args[1:3] == (["corp-1"], ["pu-1"])
    assert result["events"][0]["event_type_code"] == "source_recorded"
