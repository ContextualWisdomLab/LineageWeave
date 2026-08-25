from __future__ import annotations

import pytest

from backend.app.analysis_run_start import configured_tepp_client
from lineageweave.tepp_client import (
    AnalysisRunRequest,
    TemporalContextEvent,
    TemporalContextRequest,
    TeppClient,
    TeppInvalidResponse,
    TeppNotAvailable,
)


def _sample_request() -> AnalysisRunRequest:
    return AnalysisRunRequest(
        idempotency_key="demo-run-1",
        tenant_workspace_id="demo-workspace",
        snapshot_id="demo-snapshot-1",
        knowledge_cutoff="2026-01-01",
        model_contract_version="v1",
        output_profile="graphml",
    )


def test_to_json_matches_tepp_published_schema_shape() -> None:
    payload = _sample_request().to_json()

    assert payload == {
        "contract_version": 1,
        "idempotency_key": "demo-run-1",
        "tenant_workspace_id": "demo-workspace",
        "snapshot_id": "demo-snapshot-1",
        "knowledge_cutoff": "2026-01-01",
        "model_contract_version": "v1",
        "output_profile": "graphml",
    }


def test_default_transport_fails_closed_until_tepp_ships_http() -> None:
    client = TeppClient()
    with pytest.raises(TeppNotAvailable):
        client.submit_analysis_run(_sample_request())
    with pytest.raises(TeppNotAvailable):
        client.read_analysis_run_status("tepp-run-1", _sample_request())


def test_custom_transport_receives_the_exact_wire_payload() -> None:
    received = {}

    def fake_transport(payload: dict) -> dict:
        received.update(payload)
        return {"status": "accepted"}

    client = TeppClient(transport=fake_transport)
    result = client.submit_analysis_run(_sample_request())

    assert result == {"status": "accepted"}
    assert received["contract_version"] == 1
    assert received["snapshot_id"] == "demo-snapshot-1"


def _succeeded_status() -> dict:
    """Return TEPP's identity-free terminal status v1 fixture."""
    request = _sample_request()
    return {
        "contract_version": 1,
        "run_id": "tepp-run-1",
        "run_state": "succeeded",
        "idempotency_key": request.idempotency_key,
        "terminal_result": {
            "contract_version": 1,
            "run_id": "tepp-run-1",
            "run_state": "succeeded",
            "idempotency_key": request.idempotency_key,
            "tenant_workspace_id": request.tenant_workspace_id,
            "snapshot_id": request.snapshot_id,
            "knowledge_cutoff": request.knowledge_cutoff,
            "model_contract_version": request.model_contract_version,
            "output_profile": request.output_profile,
            "result_artifact_id": "artifact-1",
            "result_sha256": "ab" * 32,
            "result_schema_version": "tepp-result-v1",
            "completed_at": "2026-01-02T03:04:05Z",
            "summary": {
                "analysis_family": "temporal_topic_measurement",
                "evidence_count": 12,
                "statistic_count": 4,
                "validation_status": "validated",
            },
            "failure_code": None,
        },
    }


def test_status_reader_accepts_only_the_request_bound_terminal_contract() -> None:
    status = _succeeded_status()
    client = TeppClient(status_transport=lambda _run_id: status)

    assert client.read_analysis_run_status("tepp-run-1", _sample_request()) == status


@pytest.mark.parametrize(
    "mutate",
    [
        lambda status: status.clear(),
        lambda status: status.update(run_id="other-run"),
        lambda status: status["terminal_result"].update(snapshot_id="other-snapshot"),
        lambda status: status["terminal_result"].update(result_sha256="not-a-digest"),
        lambda status: status["terminal_result"].update(completed_at="2026-01-02"),
        lambda status: status["terminal_result"].update(completed_at=None),
        lambda status: status["terminal_result"].update(completed_at="not-a-time"),
        lambda status: status["terminal_result"].update(summary={}),
        lambda status: status["terminal_result"]["summary"].update(
            analysis_family="family\u001fhidden"
        ),
        lambda status: status["terminal_result"].update(
            result_artifact_id="x" * (64 * 1024)
        ),
        lambda status: status.update(extra=True),
        lambda status: status.update(run_state="unknown", terminal_result=None),
        lambda status: status.update(run_state="succeeded", terminal_result=[]),
    ],
)
def test_status_reader_fails_closed_on_identity_shape_and_digest_mismatch(mutate) -> None:
    status = _succeeded_status()
    mutate(status)
    client = TeppClient(status_transport=lambda _run_id: status)

    with pytest.raises(TeppInvalidResponse):
        client.read_analysis_run_status("tepp-run-1", _sample_request())


@pytest.mark.parametrize("invalid", [None, {"unencodable": {1, 2}}])
def test_status_reader_rejects_non_object_and_non_json_payloads(invalid) -> None:
    client = TeppClient(status_transport=lambda _run_id: invalid)

    with pytest.raises(TeppInvalidResponse):
        client.read_analysis_run_status("tepp-run-1", _sample_request())


def test_status_reader_keeps_nonterminal_receipts_measurement_free() -> None:
    status = {
        "contract_version": 1,
        "run_id": "tepp-run-1",
        "run_state": "running",
        "idempotency_key": _sample_request().idempotency_key,
        "terminal_result": None,
    }
    client = TeppClient(status_transport=lambda _run_id: status)

    assert client.read_analysis_run_status("tepp-run-1", _sample_request()) == status


def test_configured_transport_sends_optional_bearer_key(monkeypatch: pytest.MonkeyPatch) -> None:
    received = {}

    def fake_post_json(
        url: str, payload: dict, *, headers: dict, timeout: float, include_context_metadata: bool
    ) -> dict:
        received.update(
            url=url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            include_context_metadata=include_context_metadata,
        )
        return {"status": "accepted"}

    monkeypatch.setattr("backend.app.analysis_run_start.post_json", fake_post_json)
    client = configured_tepp_client("https://tepp.example/v1/analysis-runs", "test-key")

    client.submit_analysis_run(_sample_request())

    assert received["headers"] == {
        "tepp-consumer": "lineageweave",
        "tepp-contract-version": "1",
        "idempotency-key": "demo-run-1",
    }
    assert received["payload"] == _sample_request().to_json()
    assert received["include_context_metadata"] is False


def test_configured_temporal_context_uses_published_lineageweave_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received = {}

    def fake_post_json(
        url: str, payload: dict, *, headers: dict, timeout: float, include_context_metadata: bool
    ) -> dict:
        received.update(
            url=url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            include_context_metadata=include_context_metadata,
        )
        event = payload["events"][0]
        return {
            "contract_version": 1,
            "claim_boundary": "association_not_causal",
            "timeline_events": [
                {
                    **{key: value for key, value in event.items() if key != "available_time"},
                    "sequence_ordinal": 0,
                    "is_subject": True,
                }
            ],
            "temporal_relations": [],
            "transition_gap_candidates": [],
            "source_post_ids": ["post-1"],
        }

    monkeypatch.setattr("backend.app.analysis_run_start.post_json", fake_post_json)
    client = configured_tepp_client(
        temporal_context_url="https://tepp.example/v1/temporal-context"
    )
    request = TemporalContextRequest(
        knowledge_cutoff="2026-08-23T00:00:00Z",
        subject_post_id="post-1",
        events=(
            TemporalContextEvent(
                event_id="event-1",
                source_post_id="post-1",
                event_type_code="post_recorded",
                event_label="Source post recorded",
                event_time="2026-08-21T00:00:00Z",
                available_time="2026-08-21T00:00:00Z",
                project_reference=None,
                actor_references=("actor-1",),
            ),
        ),
    )

    assert client.temporal_context(request)["claim_boundary"] == "association_not_causal"
    assert received == {
        "url": "https://tepp.example/v1/temporal-context",
        "payload": request.to_json(),
        "headers": {"tepp-consumer": "lineageweave", "tepp-contract-version": "1"},
        "timeout": 10.0,
        "include_context_metadata": False,
    }


def test_temporal_context_host_gateway_preserves_tepp_loopback_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received = {}

    def fake_post_json(_url: str, _payload: dict, **kwargs) -> dict:
        received.update(kwargs)
        raise OSError("stop after observing headers")

    monkeypatch.setattr("backend.app.analysis_run_start.post_json", fake_post_json)
    client = configured_tepp_client(
        temporal_context_url="http://host.docker.internal:15174/v1/temporal-context"
    )
    with pytest.raises(TeppNotAvailable):
        client.temporal_context(
            TemporalContextRequest(
                knowledge_cutoff="2026-08-23T00:00:00Z",
                subject_post_id="post-1",
                events=(),
            )
        )

    assert received["headers"]["host"] == "127.0.0.1"
