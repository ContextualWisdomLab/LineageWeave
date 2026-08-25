from __future__ import annotations

import pytest

from backend.app.analysis_run_start import configured_tepp_client
from lineageweave.tepp_client import (
    AnalysisRunRequest,
    TeppClient,
    TeppInvalidResponse,
    TeppNotAvailable,
)


def _sample_request() -> AnalysisRunRequest:
    return AnalysisRunRequest(
        idempotency_key="demo-run-1",
        tenant_workspace_id="demo-workspace",
        snapshot_id="demo-snapshot-1",
        knowledge_cutoff="2026-01-01T00:00:00Z",
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
        "knowledge_cutoff": "2026-01-01T00:00:00Z",
        "model_contract_version": "v1",
        "output_profile": "graphml",
    }


def test_default_transport_fails_closed_until_tepp_ships_http() -> None:
    client = TeppClient()
    with pytest.raises(TeppNotAvailable):
        client.submit_analysis_run(_sample_request())
    with pytest.raises(TeppNotAvailable):
        client.read_analysis_run_status("tepp-run-1", _sample_request())


def _terminal_status() -> dict:
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


def test_status_reader_accepts_only_request_bound_terminal_results() -> None:
    status = _terminal_status()
    client = TeppClient(status_transport=lambda _run_id: status)
    assert client.read_analysis_run_status("tepp-run-1", _sample_request()) == status

    status["terminal_result"]["snapshot_id"] = "other-snapshot"
    with pytest.raises(TeppInvalidResponse):
        client.read_analysis_run_status("tepp-run-1", _sample_request())


def test_status_reader_requires_strict_rfc3339_terminal_time() -> None:
    status = _terminal_status()
    status["terminal_result"]["completed_at"] = "2026-01-02 03:04:05+00:00"
    client = TeppClient(status_transport=lambda _run_id: status)
    with pytest.raises(TeppInvalidResponse):
        client.read_analysis_run_status("tepp-run-1", _sample_request())


@pytest.mark.parametrize(
    "status",
    [None, {}, {"unencodable": {1}}, {"result_artifact_id": "x" * (64 * 1024)}],
)
def test_status_reader_rejects_invalid_or_oversized_payloads(status) -> None:
    client = TeppClient(status_transport=lambda _run_id: status)
    with pytest.raises(TeppInvalidResponse):
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


def test_accepted_response_rejects_oversized_provider_identity() -> None:
    client = TeppClient(
        transport=lambda _payload: {
            "contract_version": 1,
            "run_id": "x" * (64 * 1024),
            "run_state": "accepted",
            "idempotency_key": _sample_request().idempotency_key,
        }
    )

    with pytest.raises(TeppInvalidResponse):
        client.submit_analysis_run(_sample_request())


def test_configured_transport_sends_tepp_consumer_contract_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    received = {}

    def fake_post_json(
        url: str,
        payload: dict,
        *,
        headers: dict,
        timeout: float,
        service_peer_name: str,
    ) -> dict:
        received.update(
            url=url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            service_peer_name=service_peer_name,
        )
        return {"status": "accepted"}

    monkeypatch.setattr("backend.app.analysis_run_start.post_json", fake_post_json)
    client = configured_tepp_client("https://tepp.example/v1/analysis-runs")

    client.submit_analysis_run(_sample_request())

    assert received["headers"] == {
        "idempotency-key": "demo-run-1",
        "tepp-consumer": "lineageweave",
        "tepp-contract-version": "1",
    }
    assert received["payload"] == _sample_request().to_json()
    assert received["service_peer_name"] == "tepp"


def test_configured_transport_hides_raw_provider_exception_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_post_json(*args, **kwargs):
        raise OSError("provider secret must not escape")

    monkeypatch.setattr("backend.app.analysis_run_start.post_json", failing_post_json)
    client = configured_tepp_client("https://tepp.example/v1/analysis-runs")

    with pytest.raises(TeppNotAvailable) as error:
        client.submit_analysis_run(_sample_request())

    assert str(error.value) == "TEPP transport unavailable"
    assert "provider secret" not in str(error.value)
    assert isinstance(error.value.__cause__, OSError)
    assert str(error.value.__cause__) == "provider secret must not escape"
