"""The project-history repository applies authorization before composition."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest

from backend.app.project_history import (
    PROJECT_HISTORY_MAXIMUM_LIMIT,
    ProjectHistoryNotFound,
    fetch_project_history_projection,
)


class FakeConnection:
    """Return deterministic rows while recording every SQL invocation."""

    def __init__(self, responses: list[list[dict[str, Any]]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object) -> list[dict[str, Any]]:
        self.calls.append((query, args))
        return self.responses.pop(0)


def source(post_id: str, day: int) -> dict[str, Any]:
    """Return one visible project event row."""

    return {
        "post_id": post_id,
        "post_title": "Contract awarded" if day == 1 else "VOC received",
        "created_at": datetime(2026, 1, day, 9, tzinfo=timezone.utc),
        "voc_type_code": "vom" if day == 1 else "voc",
        "source_stage_code": None,
        "source_detail_state_code": None,
    }


def test_repository_bounds_abac_first_and_constrains_every_child_read() -> None:
    connection = FakeConnection(
        [
            [source("award", 1), source("voc", 2)],
            [
                {
                    "post_id": "award",
                    "match_kind_code": "source_project_code",
                    "matched_value": "P-100",
                    "confidence": None,
                    "ontology_iri": None,
                    "provenance": "source_post.source_project_code",
                },
                {
                    "post_id": "voc",
                    "match_kind_code": "semantic_project_key",
                    "matched_value": "Ｐ－１００",
                    "confidence": 0.9,
                    "ontology_iri": "https://w3id.org/lineageweave#Project",
                    "provenance": "post_project_mention.project_key",
                },
            ],
            [],
            [{"parent_post_id": "award", "child_post_id": "voc", "fused_score": 0.8}],
        ]
    )
    cutoff = datetime(2026, 1, 3, tzinfo=timezone.utc)

    result = asyncio.run(
        fetch_project_history_projection(
            connection,  # type: ignore[arg-type]
            project_key="Ｐ－１００",
            focus_post_id="voc",
            knowledge_cutoff=cutoff,
            corporate_entity_ids=["corp-1"],
            limit=8,
        )
    )

    assert result["event_count"] == 2
    event_query, event_args = connection.calls[0]
    assert "visibility_code = 'public'" in event_query
    assert "corporate_entity_id::text = any($2::text[])" in event_query
    assert "source_draft_code" in event_query
    assert "source_deleted_flag" in event_query
    assert "post.created_at <= $3" in event_query
    assert "post_project_mention" in event_query
    assert event_args == ("p-100", ["corp-1"], cutoff, 9)
    for _query, args in connection.calls[1:]:
        assert args[0] == ["award", "voc"]


def test_repository_reports_truncation_and_rejects_hidden_focus() -> None:
    connection = FakeConnection([[source("award", 1), source("voc", 2)]])
    with pytest.raises(ProjectHistoryNotFound):
        asyncio.run(
            fetch_project_history_projection(
                connection,  # type: ignore[arg-type]
                project_key="P-100",
                focus_post_id="hidden",
                knowledge_cutoff=datetime(2026, 1, 3, tzinfo=timezone.utc),
                corporate_entity_ids=[],
                limit=1,
            )
        )


def test_repository_rejects_unbounded_limits_before_sql() -> None:
    connection = FakeConnection([])
    with pytest.raises(ValueError, match="limit"):
        asyncio.run(
            fetch_project_history_projection(
                connection,  # type: ignore[arg-type]
                project_key="P-100",
                focus_post_id=None,
                knowledge_cutoff=datetime.now(timezone.utc),
                corporate_entity_ids=[],
                limit=PROJECT_HISTORY_MAXIMUM_LIMIT + 1,
            )
        )
    assert connection.calls == []
