from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.tepp_project_history import (
    _load_project_rows,
    build_project_history_request,
)


def _row(
    post_id: str,
    title: str,
    stage: str | None,
    created_at: str,
    *,
    project_code: str = "project-alpha",
    voc_type_code: str = "neutral",
    actor_ids: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "post_id": post_id,
        "post_title": title,
        "source_stage_code": stage,
        "voc_type_code": voc_type_code,
        "source_project_code": project_code,
        "source_project_name": "Project Alpha" if project_code == "project-alpha" else "Other",
        "created_at": datetime.fromisoformat(created_at.replace("Z", "+00:00")),
        "post_body_excerpt": f"Evidence for {title}",
        "actor_ids": actor_ids,
    }


def test_build_project_history_request_uses_only_exact_project_and_explicit_stage_evidence() -> None:
    request = build_project_history_request(
        rows=[
            _row(
                "post-contract",
                "Contract awarded",
                "contract_awarded",
                "2022-03-01T00:00:00Z",
                actor_ids=("actor-sales",),
            ),
            _row(
                "post-spec",
                "Specification changed",
                "specification_changed",
                "2023-06-01T00:00:00Z",
                actor_ids=("actor-engineering",),
            ),
            _row(
                "post-voc",
                "VOC received",
                None,
                "2026-06-01T00:00:00Z",
                voc_type_code="voc",
                actor_ids=("actor-sales", "actor-operations", "actor-customer"),
            ),
            _row(
                "post-other",
                "Other project event",
                "delivered",
                "2024-01-01T00:00:00Z",
                project_code="project-other",
            ),
        ],
        tenant_workspace_id="tenant-1",
        focus_post_id="post-voc",
        knowledge_cutoff=datetime(2026, 8, 19, tzinfo=timezone.utc),
        idempotency_key="history-idem-1",
    )

    assert request is not None
    assert request.project_key == "project-alpha"
    assert [event.event_type_code for event in request.events] == [
        "contract_awarded",
        "specification_changed",
        "voc_received",
    ]
    assert [event.source_post_id for event in request.events] == [
        "post-contract",
        "post-spec",
        "post-voc",
    ]
    assert request.focus_event_id == "post-voc"
    assert all(event.occurred_at == event.available_at for event in request.events)


def test_build_project_history_request_refuses_missing_project_or_focus() -> None:
    assert (
        build_project_history_request(
            rows=[_row("post-1", "No project", "delivered", "2024-01-01T00:00:00Z", project_code="")],
            tenant_workspace_id="tenant-1",
            focus_post_id="post-1",
            knowledge_cutoff=datetime(2026, 8, 19, tzinfo=timezone.utc),
            idempotency_key="history-idem-1",
        )
        is None
    )
    assert (
        build_project_history_request(
            rows=[_row("post-1", "Delivery", "delivered", "2024-01-01T00:00:00Z")],
            tenant_workspace_id="tenant-1",
            focus_post_id="missing",
            knowledge_cutoff=datetime(2026, 8, 19, tzinfo=timezone.utc),
            idempotency_key="history-idem-1",
        )
        is None
    )


class _RecordingConnection:
    def __init__(self) -> None:
        self.query = ""
        self.arguments: tuple[Any, ...] = ()

    async def fetchrow(self, _query: str, _post_id: str) -> dict[str, str]:
        return {
            "post_id": "post-voc",
            "source_project_code": "project-alpha",
            "source_project_name": "Project Alpha",
        }

    async def fetch(self, query: str, *arguments: Any) -> list[dict[str, Any]]:
        self.query = query
        self.arguments = arguments
        return [
            {
                "post_id": "post-contract",
                "post_title": "Contract awarded",
                "source_stage_code": "contract_awarded",
                "voc_type_code": "neutral",
                "source_project_code": "project-alpha",
                "source_project_name": "Project Alpha",
                "post_body": "Contract evidence",
                "created_at": datetime(2022, 3, 1, tzinfo=timezone.utc),
                "author_actor_id": "actor-sales",
            },
            {
                "post_id": "post-voc",
                "post_title": "VOC received",
                "source_stage_code": None,
                "voc_type_code": "voc",
                "source_project_code": "project-alpha",
                "source_project_name": "Project Alpha",
                "post_body": "VOC evidence",
                "created_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
                "author_actor_id": "actor-customer",
            },
        ]


def test_project_loader_collects_the_authorized_project_history_not_only_citations() -> None:
    connection = _RecordingConnection()
    cutoff = datetime(2026, 8, 19, tzinfo=timezone.utc)
    rows = asyncio.run(
        _load_project_rows(
            connection,  # type: ignore[arg-type]
            focus_post_id="post-voc",
            source_post_ids=["post-voc"],
            corporate_entity_ids=["corporate-1"],
            knowledge_cutoff=cutoff,
        )
    )

    assert [str(row["post_id"]) for row in rows] == ["post-contract", "post-voc"]
    assert "post.post_id = any" not in connection.query
    assert "limit 128" in connection.query.casefold()
    assert connection.arguments == (
        "project-alpha",
        "post-voc",
        ["post-voc"],
        cutoff,
        ["corporate-1"],
    )


def test_api_contract_attaches_tepp_history_to_read_global_and_post_ask() -> None:
    source = Path("backend/app/main.py").read_text(encoding="utf-8")
    assert '@app.get("/api/posts/{post_id}/project-history")' in source
    assert source.count("project_history_for_post_ids(") >= 3
    assert source.count('"tepp_project_history"') >= 3
    project_history_lines = [line for line in source.splitlines() if "project_history" in line]
    assert project_history_lines
    assert all("api_key" not in line for line in project_history_lines)
