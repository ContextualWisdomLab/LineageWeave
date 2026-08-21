"""TEPP project histories are typed, cutoff-safe, and source-grounded."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.tepp_project_history import build_project_history_request, classify_event_type
from lineageweave.tepp_project_history import (
    PROJECT_HISTORY_CONTRACT_VERSION,
    ProjectHistoryProjection,
    TeppProjectHistoryClient,
    TeppProjectHistoryNotAvailable,
)


def source_row(
    post_id: str,
    title: str,
    created_at: str,
    *,
    focus: bool = False,
    voc_type_code: str = "vom",
    actors: tuple[str, ...] = (),
) -> dict:
    """Return one authorized row shape consumed by the request builder."""
    return {
        "post_id": post_id,
        "post_title": title,
        "created_at": datetime.fromisoformat(created_at.replace("Z", "+00:00")),
        "source_stage_code": None,
        "source_detail_state_code": None,
        "voc_type_code": voc_type_code,
        "source_project_code": "P-100",
        "source_project_name": "Northridge renewal",
        "secondary_grouping_key": "proj-alpha",
        "evidence_text": f"Evidence: {title}",
        "actor_ids": list(actors),
        "is_focus": focus,
    }


def test_request_builder_emits_the_minimum_buyer_cycle_without_raw_body() -> None:
    rows = [
        source_row("award", "Contract awarded", "2022-03-11T09:00:00Z", actors=("a",)),
        source_row(
            "spec",
            "Specification revision requested",
            "2023-06-15T09:00:00Z",
            actors=("a", "b"),
        ),
        source_row("delivery", "Delivery confirmed", "2024-02-20T09:00:00Z", actors=("b",)),
        source_row("handoff", "Operational handoff recorded", "2024-03-01T09:00:00Z", actors=("b", "c")),
        source_row(
            "voc",
            "Transformer VOC received",
            "2026-07-30T09:00:00Z",
            focus=True,
            voc_type_code="voc",
            actors=("c",),
        ),
        source_row("rebid", "Rebid started", "2026-08-10T09:00:00Z", actors=("c",)),
    ]

    request = build_project_history_request(
        rows,
        focus_post_id="voc",
        tenant_workspace_id="tenant-demo",
        knowledge_cutoff=datetime(2026, 8, 19, 23, 59, 59, tzinfo=timezone.utc),
    )

    assert request.contract_version == PROJECT_HISTORY_CONTRACT_VERSION
    assert request.project_key == "P-100"
    assert request.focus_event_id == "voc"
    assert [event.event_type_code for event in request.events] == [
        "contract_awarded",
        "specification_changed",
        "delivered",
        "handoff_recorded",
        "voc_received",
        "rebid_started",
    ]
    assert all(event.availability_basis_code == "source_created_at_proxy" for event in request.events)
    assert all("post_body" not in event.to_json() for event in request.events)


def test_classifier_requires_explicit_event_language_and_focus_for_generic_voc() -> None:
    assert classify_event_type("Specification revision requested", None, None, "vom", False) == "specification_changed"
    assert classify_event_type("Operational handoff recorded", None, None, "vom", False) == "handoff_recorded"
    assert classify_event_type("General account note", None, None, "voc", False) == "source_recorded"
    assert classify_event_type("General account note", None, None, "voc", True) == "voc_received"


def test_client_validates_the_tepp_projection_and_publishes_no_credentials() -> None:
    captured: dict = {}

    def transport(payload: dict, headers: dict[str, str]) -> dict:
        captured["payload"] = payload
        captured["headers"] = headers
        return {
            "contract_version": 1,
            "project_key": "P-100",
            "project_name": "Northridge renewal",
            "focus_event_id": "voc",
            "history_span_start": "2022-03-11T09:00:00Z",
            "history_span_end": "2026-08-10T09:00:00Z",
            "participant_count": 3,
            "inference_status": "temporal_association_only",
            "events": [
                {
                    "event_id": "voc",
                    "event_type_code": "voc_received",
                    "event_title": "Transformer VOC received",
                    "occurred_at": "2026-07-30T09:00:00Z",
                    "available_at": "2026-07-30T09:00:00Z",
                    "availability_basis_code": "source_created_at_proxy",
                    "source_post_id": "voc",
                    "evidence_text": "Evidence: Transformer VOC received",
                    "actor_ids": ["c"],
                }
            ],
            "findings": [],
        }

    request = build_project_history_request(
        [source_row("voc", "Transformer VOC received", "2026-07-30T09:00:00Z", focus=True, voc_type_code="voc")],
        focus_post_id="voc",
        tenant_workspace_id="tenant-demo",
        knowledge_cutoff=datetime(2026, 8, 19, 23, 59, 59, tzinfo=timezone.utc),
    )
    projection = TeppProjectHistoryClient(transport=transport).project(request)

    assert isinstance(projection, ProjectHistoryProjection)
    assert projection.participant_count == 3
    assert captured["headers"]["tepp-consumer"] == "lineageweave"
    assert captured["headers"]["tepp-contract-version"] == "1"
    assert "authorization" not in {key.lower() for key in captured["headers"]}


def test_default_client_and_unpublished_response_fail_closed() -> None:
    request = build_project_history_request(
        [source_row("voc", "Transformer VOC received", "2026-07-30T09:00:00Z", focus=True, voc_type_code="voc")],
        focus_post_id="voc",
        tenant_workspace_id="tenant-demo",
        knowledge_cutoff=datetime(2026, 8, 19, 23, 59, 59, tzinfo=timezone.utc),
    )
    with pytest.raises(TeppProjectHistoryNotAvailable):
        TeppProjectHistoryClient().project(request)

    client = TeppProjectHistoryClient(transport=lambda _payload, _headers: {"causal_score": 0.99})
    with pytest.raises(ValueError, match="project-history projection"):
        client.project(request)
