from __future__ import annotations

from dataclasses import replace

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


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("idempotency_key", " "),
        ("tenant_workspace_id", None),
        ("snapshot_id", "\t"),
        ("knowledge_cutoff", ""),
        ("model_contract_version", "\n"),
        ("output_profile", None),
    ],
)
def test_request_rejects_non_blank_schema_fields(field_name: str, value: object) -> None:
    """A v1 request must not send blank or non-text required fields."""
    with pytest.raises(ValueError, match=field_name):
        replace(_sample_request(), **{field_name: value})


def test_request_rejects_unknown_contract_version() -> None:
    """The adapter must not silently emit a request for another contract."""
    with pytest.raises(ValueError, match="contract_version=1"):
        replace(_sample_request(), contract_version=2)


def test_request_rejects_boolean_contract_version() -> None:
    """JSON booleans must not pass Python's integer type relationship."""
    with pytest.raises(ValueError, match="contract_version=1"):
        replace(_sample_request(), contract_version=True)


def test_default_transport_fails_closed_until_tepp_ships_http() -> None:
    client = TeppClient()
    with pytest.raises(TeppNotAvailable):
        client.submit_analysis_run(_sample_request())


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


def test_configured_transport_sends_optional_bearer_key(monkeypatch: pytest.MonkeyPatch) -> None:
    received = {}

    def fake_post_json(url: str, payload: dict, *, headers: dict, timeout: float) -> dict:
        received.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {"status": "accepted"}

    monkeypatch.setattr("backend.app.analysis_run_start.post_json", fake_post_json)
    client = configured_tepp_client("https://tepp.example/v1/analysis-runs", "test-key")

    client.submit_analysis_run(_sample_request())

    assert received["headers"] == {"authorization": "Bearer test-key"}
    assert received["payload"] == _sample_request().to_json()
