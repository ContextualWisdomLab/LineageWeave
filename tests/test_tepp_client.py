from __future__ import annotations

import pytest

from backend.app.analysis_run_start import configured_tepp_client
from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable


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
    with pytest.raises(TeppNotAvailable, match="status transport unavailable"):
        client.get_analysis_run_status("remote-run-1")


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


def test_configured_transport_reads_opaque_remote_run_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received = {}

    def fake_get_json(url: str, **kwargs) -> dict:
        received.update(url=url, **kwargs)
        return {"contract_version": 1, "run_state": "running"}

    monkeypatch.setattr("backend.app.analysis_run_start.get_json", fake_get_json)
    client = configured_tepp_client(
        "https://tepp.example/v1/analysis-runs",
        api_key="runtime-only",
    )

    status = client.get_analysis_run_status("remote/run 1")

    assert status["run_state"] == "running"
    assert received == {
        "url": "https://tepp.example/v1/analysis-runs/remote%2Frun%201",
        "headers": {
            "tepp-consumer": "lineageweave",
            "tepp-contract-version": "1",
            "authorization": "Bearer runtime-only",
        },
        "timeout": 30.0,
        "service_peer_name": "tepp",
    }


@pytest.mark.parametrize("run_id", ["", "   ", None])
def test_status_read_rejects_missing_remote_run_identity(run_id) -> None:
    with pytest.raises(ValueError, match="run_id must be a non-empty string"):
        TeppClient().get_analysis_run_status(run_id)


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
