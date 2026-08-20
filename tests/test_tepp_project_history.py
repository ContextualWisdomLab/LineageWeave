from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lineageweave.tepp_project_history import (
    PROJECT_HISTORY_CONTRACT_VERSION,
    PROJECT_HISTORY_PATH,
    TEMPORAL_ASSOCIATION_ONLY,
    ProjectHistoryEvent,
    ProjectHistoryRequest,
    TeppProjectHistoryClient,
    TeppProjectHistoryUnavailable,
    project_history_endpoint,
)


def _request() -> ProjectHistoryRequest:
    return ProjectHistoryRequest(
        contract_version=PROJECT_HISTORY_CONTRACT_VERSION,
        idempotency_key="history-idem-1",
        tenant_workspace_id="tenant-1",
        project_key="project-alpha",
        project_name="Project Alpha",
        knowledge_cutoff="2026-08-19T00:00:00Z",
        focus_event_id="event-voc",
        events=(
            ProjectHistoryEvent(
                event_id="event-contract",
                event_type_code="contract_awarded",
                event_title="Contract awarded",
                event_time="2022-03-01T00:00:00Z",
                available_at="2022-03-01T00:00:00Z",
                availability_basis="source_post.created_at",
                source_post_id="post-contract",
                evidence_text="The order was awarded.",
                actor_ids=("actor-sales",),
            ),
            ProjectHistoryEvent(
                event_id="event-voc",
                event_type_code="voc_received",
                event_title="VOC received",
                event_time="2026-06-01T00:00:00Z",
                available_at="2026-06-01T00:00:00Z",
                availability_basis="source_post.created_at",
                source_post_id="post-voc",
                evidence_text="A customer VOC was registered.",
                actor_ids=("actor-sales", "actor-operations", "actor-customer"),
            ),
        ),
    )


def _projection_payload() -> dict[str, object]:
    request = _request()
    return {
        "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
        "project_key": request.project_key,
        "project_name": request.project_name,
        "focus_event_id": request.focus_event_id,
        "inference_status": TEMPORAL_ASSOCIATION_ONLY,
        "participant_count": 3,
        "history_span_start": "2022-03-01T00:00:00Z",
        "history_span_end": "2026-06-01T00:00:00Z",
        "events": [event.to_wire() for event in request.events],
        "findings": [
            {
                "finding_code": "contract_award_before_focus",
                "summary": (
                    "An explicit contract-award event precedes the focus event. "
                    "This is a temporal association, not a causal conclusion."
                ),
                "related_event_ids": ["event-contract", "event-voc"],
                "evidence_post_ids": ["post-contract", "post-voc"],
            }
        ],
    }


def test_project_history_client_posts_the_strict_credential_free_contract() -> None:
    calls: list[tuple[str, dict[str, object], dict[str, str], float]] = []

    def transport(
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, object]:
        calls.append((url, payload, headers, timeout))
        return _projection_payload()

    client = TeppProjectHistoryClient(
        "https://tepp.example.test/v1/analysis-runs",
        transport=transport,
        timeout_seconds=30.0,
    )
    projection = client.project(_request())

    assert projection.inference_status == TEMPORAL_ASSOCIATION_ONLY
    assert projection.focus_event_id == "event-voc"
    assert projection.participant_count == 3
    assert [event.event_id for event in projection.events] == [
        "event-contract",
        "event-voc",
    ]
    assert calls == [
        (
            f"https://tepp.example.test{PROJECT_HISTORY_PATH}",
            _request().to_wire(),
            {
                "content-type": "application/json",
                "tepp-consumer": "lineageweave",
                "tepp-contract-version": "1",
                "idempotency-key": "history-idem-1",
            },
            30.0,
        )
    ]
    assert not any("authorization" in name.lower() for name in calls[0][2])


def test_project_history_client_refuses_causal_or_out_of_bundle_results() -> None:
    causal = _projection_payload()
    causal["inference_status"] = "causal"
    client = TeppProjectHistoryClient(
        "https://tepp.example.test",
        transport=lambda *_: causal,
    )
    with pytest.raises(TeppProjectHistoryUnavailable):
        client.project(_request())

    causal_summary = _projection_payload()
    findings = causal_summary["findings"]
    assert isinstance(findings, list)
    finding = findings[0]
    assert isinstance(finding, dict)
    finding["summary"] = (
        "An explicit contract-award event precedes the focus event. "
        "This is a temporal association and a causal conclusion."
    )
    client = TeppProjectHistoryClient(
        "https://tepp.example.test",
        transport=lambda *_: causal_summary,
    )
    with pytest.raises(TeppProjectHistoryUnavailable):
        client.project(_request())

    out_of_bundle = _projection_payload()
    findings = out_of_bundle["findings"]
    assert isinstance(findings, list)
    finding = findings[0]
    assert isinstance(finding, dict)
    finding["evidence_post_ids"] = ["post-not-authorized"]
    client = TeppProjectHistoryClient(
        "https://tepp.example.test",
        transport=lambda *_: out_of_bundle,
    )
    with pytest.raises(TeppProjectHistoryUnavailable):
        client.project(_request())


def test_project_history_endpoint_and_unavailable_boundary_fail_closed() -> None:
    assert (
        project_history_endpoint("https://tepp.example.test/v1/analysis-runs")
        == "https://tepp.example.test/v1/project-histories"
    )
    assert (
        project_history_endpoint("https://tepp.example.test/")
        == "https://tepp.example.test/v1/project-histories"
    )
    assert (
        project_history_endpoint("http://127.0.0.1:45123/v1/analysis-runs")
        == "http://127.0.0.1:45123/v1/project-histories"
    )
    assert (
        project_history_endpoint("http://localhost:45123")
        == "http://localhost:45123/v1/project-histories"
    )
    assert (
        project_history_endpoint("http://[::1]:45123/")
        == "http://[::1]:45123/v1/project-histories"
    )
    for hostile in (
        "",
        "file:///tmp/tepp",
        "http://tepp.example.test",
        "http://0.0.0.0:45123",
        "https://user@host",
        "https://host:bad-port",
        "https://host/path",
        "https://host\n.invalid",
    ):
        with pytest.raises(TeppProjectHistoryUnavailable):
            project_history_endpoint(hostile)

    client = TeppProjectHistoryClient("")
    with pytest.raises(TeppProjectHistoryUnavailable):
        client.project(_request())


def test_project_history_request_rejects_future_or_non_utc_cutoffs() -> None:
    request = _request()
    with pytest.raises(TeppProjectHistoryUnavailable):
        ProjectHistoryRequest(
            **{
                **request.__dict__,
                "knowledge_cutoff": "2099-01-01T00:00:00Z",
            }
        ).to_wire(now=datetime(2026, 8, 20, tzinfo=timezone.utc))

    with pytest.raises(TeppProjectHistoryUnavailable):
        ProjectHistoryRequest(
            **{
                **request.__dict__,
                "knowledge_cutoff": "2026-08-19T09:00:00+09:00",
            }
        ).to_wire(now=datetime(2026, 8, 20, tzinfo=timezone.utc))
