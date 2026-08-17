"""Fail-closed contextual-orchestrator task envelope (ADR 0025).

The portable envelope is a versioned REST adapter. A missing host, a
missing key, or an upstream ``invalid_mode`` must not become an invented
completion, a confidence of 0.0, or a theta.
"""

from __future__ import annotations

import hashlib

import pytest

from lineageweave.orchestrator_client import (
    ACCEPTED_MODES,
    OrchestratorClient,
    OrchestratorNotAvailable,
    SYNTHETIC_PROBE_PROMPT,
    TaskEnvelope,
    build_orchestrator_client,
    classify_orchestrator_error,
    published_task_envelopes,
)


def test_default_transport_fails_closed() -> None:
    client = OrchestratorClient()
    with pytest.raises(OrchestratorNotAvailable, match="orchestrator_not_available"):
        client.submit_task_envelope(published_task_envelopes()[0])


def test_default_payload_never_invents_a_completion() -> None:
    payload = OrchestratorClient().as_api_payload()

    assert payload == {
        "port": "contextual_orchestrator",
        "status": "unavailable",
        "status_reason": OrchestratorNotAvailable.reason,
        "envelopes": [],
    }
    assert "theta" not in payload
    assert "completion" not in payload
    assert "choices" not in payload


def test_empty_credentials_factory_fails_closed() -> None:
    client = build_orchestrator_client(base_url="", api_key="")
    payload = client.as_api_payload()
    assert payload["status"] == "unavailable"
    assert payload["envelopes"] == []


def test_whitespace_credentials_factory_fails_closed() -> None:
    client = build_orchestrator_client(base_url="  ", api_key="  ")
    assert client.as_api_payload()["status"] == "unavailable"


def test_configured_factory_publishes_auto_and_verify_without_calling_http() -> None:
    calls: list[object] = []

    def boom(envelope: TaskEnvelope) -> dict[str, object]:
        calls.append(envelope)
        raise AssertionError("home status must not POST a completion")

    client = build_orchestrator_client(
        base_url="https://orchestrator.test",
        api_key="token",
        submit=boom,
    )
    payload = client.as_api_payload()

    assert calls == []
    assert payload["status"] == "accepted"
    assert payload["status_reason"] is None
    kinds = {item["task_kind"]: item for item in payload["envelopes"]}
    assert kinds["structured"]["mode"] == "auto"
    assert kinds["structured"]["next_action"] == "Structured work uses auto"
    assert kinds["checked_judgment"]["mode"] == "verify"
    assert kinds["checked_judgment"]["next_action"] == "Checked judgment uses verify"
    assert "theta" not in payload
    for item in payload["envelopes"]:
        assert "completion" not in item
        assert item["mode"] in ACCEPTED_MODES


def test_published_envelopes_are_the_portable_contract() -> None:
    structured, checked = published_task_envelopes()
    assert structured.mode == "auto"
    assert structured.task_kind == "structured"
    assert structured.reasoning_effort == "medium"
    assert checked.mode == "verify"
    assert checked.task_kind == "checked_judgment"
    assert checked.reasoning_effort == "high"
    probe_hash = hashlib.sha256(SYNTHETIC_PROBE_PROMPT.encode("utf-8")).hexdigest()
    for envelope in (structured, checked):
        body = envelope.to_json()
        assert body["contract_version"] == 1
        assert body["prompt_hash"] == probe_hash
        assert body["access_list"] == ["user_message"]
        assert set(body) == {
            "contract_version",
            "task_kind",
            "mode",
            "reasoning_effort",
            "prompt_hash",
            "access_list",
        }


def test_submit_rejects_an_unknown_mode() -> None:
    client = build_orchestrator_client(
        base_url="https://orchestrator.test",
        api_key="token",
        submit=lambda envelope: {"mode": envelope.mode},
    )
    with pytest.raises(OrchestratorNotAvailable, match="orchestrator_invalid_mode"):
        client.submit_task_envelope(
            TaskEnvelope(
                task_kind="structured",
                mode="conduct",
                reasoning_effort="medium",
            )
        )


def test_http_invalid_mode_fails_closed_instead_of_inventing_zero() -> None:
    def invalid_mode(_envelope: TaskEnvelope) -> dict[str, object]:
        raise classify_orchestrator_error("HTTP 400 invalid_mode")

    client = OrchestratorClient(transport=invalid_mode)
    with pytest.raises(OrchestratorNotAvailable, match="orchestrator_invalid_mode"):
        client.submit_task_envelope(published_task_envelopes()[1])

    payload = client.as_api_payload()
    assert payload["status"] == "unavailable"
    assert payload["status_reason"] == "orchestrator_invalid_mode"
    assert payload["envelopes"] == []


def test_classify_maps_invalid_mode_and_leaves_other_errors_generic() -> None:
    invalid = classify_orchestrator_error("HTTP 400 from orchestrator.test: invalid_mode")
    assert invalid.reason == "orchestrator_invalid_mode"
    generic = classify_orchestrator_error("connection refused")
    assert generic.reason == "orchestrator_not_available"
