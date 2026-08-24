from __future__ import annotations

import pytest

from backend.app.analysis_run_start import configured_tepp_client
from lineageweave.tepp_client import (
    AnalysisRunRequest,
    TemporalContextEvent,
    TemporalContextRequest,
    TeppClient,
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
