from __future__ import annotations

import pytest

from lineageweave.http_client import HttpClientError
from lineageweave.tepp_client import (
    AnalysisRunRequest,
    TeppClient,
    TeppNotAvailable,
    analysis_run_request_from_registry,
    create_https_analysis_run_transport,
    create_in_process_tepp_transport,
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


def test_analysis_run_request_from_registry_requires_snapshot_and_cutoff() -> None:
    request = analysis_run_request_from_registry(
        snapshot_id="  snap-1  ",
        knowledge_cutoff="2026-08-15T00:30:00Z",
        idempotency_key="demo-run-1",
        tenant_workspace_id="demo-workspace",
        model_contract_version="v1",
        output_profile="graphml",
    )
    assert request.snapshot_id == "snap-1"
    assert request.knowledge_cutoff == "2026-08-15T00:30:00Z"
    with pytest.raises(ValueError, match="snapshot_id"):
        analysis_run_request_from_registry(
            snapshot_id="   ",
            knowledge_cutoff="2026-08-15T00:30:00Z",
            idempotency_key="demo-run-1",
            tenant_workspace_id="demo-workspace",
            model_contract_version="v1",
            output_profile="graphml",
        )
    with pytest.raises(ValueError, match="knowledge_cutoff"):
        analysis_run_request_from_registry(
            snapshot_id="snap-1",
            knowledge_cutoff="",
            idempotency_key="demo-run-1",
            tenant_workspace_id="demo-workspace",
            model_contract_version="v1",
            output_profile="graphml",
        )


def test_https_transport_fails_closed_unless_https_post_is_injected() -> None:
    with pytest.raises(TeppNotAvailable, match="HTTPS"):
        create_https_analysis_run_transport("http://tepp.example.test")
    with pytest.raises(TeppNotAvailable, match="HTTPS"):
        create_https_analysis_run_transport("")
    with pytest.raises(TeppNotAvailable, match="HTTPS"):
        create_https_analysis_run_transport("file:///tmp/tepp")
    with pytest.raises(TeppNotAvailable, match="HTTPS"):
        create_https_analysis_run_transport("https://")

    recorded: dict[str, object] = {}

    def fake_poster(url: str, payload: dict, *, headers: dict, timeout: float) -> dict:
        recorded["url"] = url
        recorded["payload"] = payload
        recorded["headers"] = headers
        recorded["timeout"] = timeout
        return {"status": "accepted"}

    transport = create_https_analysis_run_transport(
        "https://tepp.example.test/base/",
        api_key="demo-key",
        poster=fake_poster,
        timeout=7.5,
    )
    result = TeppClient(transport=transport).submit_analysis_run(_sample_request())
    assert result == {"status": "accepted"}
    assert recorded["url"] == "https://tepp.example.test/base/v1/analysis-runs"
    assert recorded["payload"]["snapshot_id"] == "demo-snapshot-1"
    assert recorded["payload"]["knowledge_cutoff"] == "2026-01-01"
    assert recorded["headers"]["authorization"] == "Bearer demo-key"
    assert recorded["timeout"] == 7.5

    def failing_poster(*_args, **_kwargs) -> dict:
        raise HttpClientError("HTTP 503 from tepp.example.test")

    closed = create_https_analysis_run_transport(
        "https://tepp.example.test",
        poster=failing_poster,
    )
    with pytest.raises(TeppNotAvailable, match="503"):
        closed(_sample_request().to_json())

    anonymous = create_https_analysis_run_transport(
        "https://tepp.example.test",
        poster=fake_poster,
    )
    anonymous(_sample_request().to_json())
    assert "authorization" not in recorded["headers"]


def test_in_process_tepp_api_transport_is_injected_explicitly() -> None:
    def tepp_api(payload: dict) -> dict:
        return {"status": "accepted", "snapshot_id": payload["snapshot_id"]}

    transport = create_in_process_tepp_transport(tepp_api)
    result = TeppClient(transport=transport).submit_analysis_run(_sample_request())
    assert result == {"status": "accepted", "snapshot_id": "demo-snapshot-1"}
