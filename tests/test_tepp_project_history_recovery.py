"""Regression contracts for the recovered TEPP project-history integration."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from backend.app import main
from backend.app.auth import CurrentAccount
from backend.app.tepp_project_history import (
    build_tepp_project_history_request,
    tenant_workspace_reference,
    validate_project_history_with_tepp,
)
from lineageweave.tepp_project_history import (
    TeppProjectHistoryClient,
    TeppProjectHistoryInvalidResponse,
    TeppProjectHistoryUnavailable,
)


def _canonical_projection() -> dict[str, object]:
    """Return one synthetic authorized LineageWeave project history."""

    return {
        "contract_version": 1,
        "project_key": "P-100",
        "normalized_project_key": "p-100",
        "project_name": "Synthetic transformer renewal",
        "focus_event_id": "00000000-0000-4000-8000-000000000003",
        "time_basis_code": "source_post_created_at_fallback",
        "knowledge_cutoff": "2026-08-20T12:00:00+00:00",
        "evidence_boundary_code": "authorized_visible_source_posts",
        "event_count": 3,
        "distinct_actor_count": 2,
        "distinct_observed_actor_count": 1,
        "truncated": False,
        "events": [
            {
                "event_id": "00000000-0000-4000-8000-000000000001",
                "source_post_id": "00000000-0000-4000-8000-000000000001",
                "event_title": "Synthetic contract awarded",
                "event_type_code": "contract_awarded",
                "event_type_basis_code": "display_classification",
                "occurred_at": "2022-03-11T09:00:00Z",
                "time_basis_code": "source_post_created_at_fallback",
                "voc_type_code": None,
                "source_stage_code": "award",
                "source_detail_state_code": None,
                "project_matches": [],
                "responsibility_evidence": [
                    {
                        "actor_key": "text:prov_person\u001fsynthetic owner\u001fdemo org",
                        "actor_name": "Synthetic Owner",
                        "actor_type_code": "prov_person",
                        "affiliated_organization_name": "Demo Org",
                        "responsibility": "Source author",
                        "truth_status_code": "observed",
                        "provenance": "source_post.source_author",
                    }
                ],
                "observed_responsibilities": [],
                "responsibility_transition_code": None,
                "responsibility_transition_truth_status_code": None,
                "related_prior_paths": [],
            },
            {
                "event_id": "00000000-0000-4000-8000-000000000002",
                "source_post_id": "00000000-0000-4000-8000-000000000002",
                "event_title": "Synthetic specification changed",
                "event_type_code": "specification_changed",
                "event_type_basis_code": "display_classification",
                "occurred_at": "2023-06-15T09:00:00Z",
                "time_basis_code": "source_post_created_at_fallback",
                "voc_type_code": None,
                "source_stage_code": "spec_change",
                "source_detail_state_code": None,
                "project_matches": [],
                "responsibility_evidence": [
                    {
                        "actor_key": "person:synthetic-pm",
                        "actor_name": "Synthetic PM",
                        "actor_type_code": "prov_person",
                        "affiliated_organization_name": "Demo Org",
                        "responsibility": "Coordinate change",
                        "truth_status_code": "inferred",
                        "provenance": "post_summary_role",
                    }
                ],
                "observed_responsibilities": [],
                "responsibility_transition_code": "handoff",
                "responsibility_transition_truth_status_code": "inferred",
                "related_prior_paths": [],
            },
            {
                "event_id": "00000000-0000-4000-8000-000000000003",
                "source_post_id": "00000000-0000-4000-8000-000000000003",
                "event_title": "Synthetic VOC received",
                "event_type_code": "voc_received",
                "event_type_basis_code": "display_classification",
                "occurred_at": "2026-02-02T09:00:00Z",
                "time_basis_code": "source_post_created_at_fallback",
                "voc_type_code": "voc",
                "source_stage_code": None,
                "source_detail_state_code": None,
                "project_matches": [],
                "responsibility_evidence": [],
                "observed_responsibilities": [],
                "responsibility_transition_code": "assignment_gap",
                "responsibility_transition_truth_status_code": "inferred",
                "related_prior_paths": [],
            },
        ],
    }


def _tepp_response(request: dict[str, object]) -> dict[str, object]:
    """Return the exact TEPP #159 response shape for a validated request."""

    events = sorted(
        deepcopy(request["events"]),
        key=lambda event: (event["occurred_at"], event["event_id"]),
    )
    actors = {actor for event in events for actor in event["actor_ids"]}
    return {
        "contract_version": 1,
        "project_key": request["project_key"],
        "project_name": request["project_name"],
        "focus_event_id": request["focus_event_id"],
        "knowledge_cutoff": request["knowledge_cutoff"],
        "history_span_start": events[0]["occurred_at"],
        "history_span_end": events[-1]["occurred_at"],
        "participant_count": len(actors),
        "inference_status": "temporal_association_only",
        "events": events,
        "findings": [
            {
                "finding_code": "specification_change_before_focus",
                "summary": "An explicit specification-change event precedes the focus event.",
                "related_event_ids": [events[1]["event_id"]],
                "evidence_post_ids": [events[1]["source_post_id"]],
            }
        ],
    }


def test_mapper_uses_opaque_actor_references_and_bounded_source_evidence() -> None:
    projection = _canonical_projection()
    workspace = tenant_workspace_reference(["tenant-b", "tenant-a"])

    request = build_tepp_project_history_request(
        projection=projection,
        tenant_workspace_id=workspace,
    )
    encoded = json.dumps(request, ensure_ascii=False)

    assert workspace == tenant_workspace_reference(["tenant-a", "tenant-b"])
    assert "Synthetic Owner" not in encoded
    assert "Synthetic PM" not in encoded
    assert "Demo Org" not in encoded
    assert all(
        actor.startswith("lw-actor-")
        for event in request["events"]
        for actor in event["actor_ids"]
    )
    assert request["events"][0]["available_at"] == request["events"][0]["occurred_at"]
    assert request["events"][0]["evidence_text"].startswith("Synthetic contract awarded")


@pytest.mark.parametrize("timestamp", ["2026-08-20 12:00:00Z", "2026-08-20T12:00:00+0900"])
def test_mapper_rejects_non_rfc3339_timestamp_shapes(timestamp: str) -> None:
    projection = _canonical_projection()
    projection["knowledge_cutoff"] = timestamp

    with pytest.raises(TeppProjectHistoryUnavailable, match="RFC 3339"):
        build_tepp_project_history_request(
            projection=projection,
            tenant_workspace_id=tenant_workspace_reference(["tenant-a"]),
        )


def test_strict_client_accepts_tepp_159_and_rejects_authority_or_evidence_drift() -> None:
    request = build_tepp_project_history_request(
        projection=_canonical_projection(),
        tenant_workspace_id=tenant_workspace_reference(["tenant-a"]),
    )
    captured: dict[str, object] = {}

    def transport(url, payload, headers, timeout):
        captured.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return _tepp_response(payload)

    client = TeppProjectHistoryClient("https://tepp.example", transport=transport)
    result = client.project(request)

    assert result["inference_status"] == "temporal_association_only"
    assert captured["url"] == "https://tepp.example/v1/project-histories"
    assert "authorization" not in {key.lower() for key in captured["headers"]}
    assert captured["headers"]["tepp-consumer"] == "lineageweave"

    def causal_transport(url, payload, headers, timeout):
        del url, headers, timeout
        response = _tepp_response(payload)
        response["inference_status"] = "causal"
        return response

    with pytest.raises(TeppProjectHistoryInvalidResponse):
        TeppProjectHistoryClient(
            "https://tepp.example", transport=causal_transport
        ).project(request)

    def changed_evidence_transport(url, payload, headers, timeout):
        del url, headers, timeout
        response = _tepp_response(payload)
        response["events"][0]["evidence_text"] = "changed"
        return response

    with pytest.raises(TeppProjectHistoryInvalidResponse):
        TeppProjectHistoryClient(
            "https://tepp.example", transport=changed_evidence_transport
        ).project(request)


def test_strict_client_rejects_unknown_or_duplicate_finding_references() -> None:
    request = build_tepp_project_history_request(
        projection=_canonical_projection(),
        tenant_workspace_id=tenant_workspace_reference(["tenant-a"]),
    )

    def unknown_finding_transport(url, payload, headers, timeout):
        del url, headers, timeout
        response = _tepp_response(payload)
        response["findings"][0]["finding_code"] = "provider_authored_conclusion"
        return response

    with pytest.raises(TeppProjectHistoryInvalidResponse):
        TeppProjectHistoryClient(
            "https://tepp.example", transport=unknown_finding_transport
        ).project(request)

    def duplicate_reference_transport(url, payload, headers, timeout):
        del url, headers, timeout
        response = _tepp_response(payload)
        event_id = response["findings"][0]["related_event_ids"][0]
        response["findings"][0]["related_event_ids"] = [event_id, event_id]
        return response

    with pytest.raises(TeppProjectHistoryInvalidResponse):
        TeppProjectHistoryClient(
            "https://tepp.example", transport=duplicate_reference_transport
        ).project(request)


def test_validation_fails_closed_without_hiding_canonical_history(monkeypatch) -> None:
    projection = _canonical_projection()
    unconfigured = validate_project_history_with_tepp(
        projection=projection,
        tenant_workspace_id=tenant_workspace_reference([]),
        transport_url="",
    )
    assert unconfigured == {
        "status": "not_configured",
        "project_history": None,
        "next_action_code": "configure_tepp_project_history",
    }

    def broken_project(self, request):
        del self, request
        raise TeppProjectHistoryUnavailable("synthetic outage")

    monkeypatch.setattr(TeppProjectHistoryClient, "project", broken_project)
    unavailable = validate_project_history_with_tepp(
        projection=projection,
        tenant_workspace_id=tenant_workspace_reference([]),
        transport_url="https://tepp.example",
    )
    assert unavailable["status"] == "unavailable"
    assert projection["event_count"] == 3

    def invalid_project(self, request):
        del self, request
        raise TeppProjectHistoryInvalidResponse("synthetic invalid response")

    monkeypatch.setattr(TeppProjectHistoryClient, "project", invalid_project)
    invalid = validate_project_history_with_tepp(
        projection=projection,
        tenant_workspace_id=tenant_workspace_reference([]),
        transport_url="https://tepp.example",
    )
    assert invalid["status"] == "invalid_evidence"
    assert projection["event_count"] == 3


class _Acquire:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class _Pool:
    def acquire(self) -> _Acquire:
        return _Acquire()


def test_project_history_route_attaches_validation_to_the_canonical_projection(monkeypatch) -> None:
    projection = _canonical_projection()
    captured: dict[str, object] = {}

    async def fake_projection(connection, **kwargs):
        del connection, kwargs
        return deepcopy(projection)

    def fake_validate(**kwargs):
        captured.update(kwargs)
        return {
            "status": "validated",
            "project_history": {"inference_status": "temporal_association_only"},
            "next_action_code": "open_source_evidence",
        }

    monkeypatch.setattr(main, "fetch_project_history_projection", fake_projection)
    monkeypatch.setattr(main, "validate_project_history_with_tepp", fake_validate)
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: SimpleNamespace(tepp_transport_url="https://tepp.example"),
    )
    account = CurrentAccount(
        user_account_id="account-1",
        external_subject_id="subject-1",
        display_name="Synthetic analyst",
        preferred_locale="en",
        corporate_entity_ids=frozenset({"tenant-a"}),
        permission_codes=frozenset({"post_read"}),
    )

    result = asyncio.run(
        main.read_project_history(
            project_key="P-100",
            focus_post_id=None,
            knowledge_cutoff="2026-08-20T12:00:00+00:00",
            limit=64,
            account=account,
            pool=_Pool(),
        )
    )

    assert result["events"] == projection["events"]
    assert result["tepp_validation"]["status"] == "validated"
    assert captured["projection"]["project_key"] == "P-100"
    assert captured["transport_url"] == "https://tepp.example"
