from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from backend.app.tepp_project_history import build_project_history_request


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
    assert all(event.availability_basis == "source_post.created_at" for event in request.events)


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


def test_api_contract_attaches_tepp_history_to_read_global_and_post_ask() -> None:
    source = Path("backend/app/main.py").read_text(encoding="utf-8")
    assert '@app.get("/api/posts/{post_id}/project-history")' in source
    assert source.count("project_history_for_post_ids(") >= 3
    assert source.count('"tepp_project_history"') >= 3
    assert "settings.tepp_api_key" not in source[source.index("project_history_for_post_ids"):]
