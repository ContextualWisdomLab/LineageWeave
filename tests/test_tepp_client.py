from __future__ import annotations

import pytest

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
