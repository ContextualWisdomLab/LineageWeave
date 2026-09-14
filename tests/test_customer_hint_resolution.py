"""Tests for lineageweave.customer_hint_resolution.

Deterministic fake HTTP transport, same style as
tests/test_organization_name_resolution.py -- post_json's own HTTP
mechanics are already covered in test_http_client.py; these tests are
for this module's own prompt/response contract.
"""

from __future__ import annotations

from lineageweave.customer_hint_resolution import (
    ContextualOrchestratorCustomerHintResolutionClient,
    NullCustomerHintResolutionClient,
)


def test_null_client_is_unavailable() -> None:
    resolution_client = NullCustomerHintResolutionClient()
    assert resolution_client.available is False


def test_live_client_uses_adaptive_orchestrator_mode(monkeypatch) -> None:
    transport_observations: dict[str, object] = {}

    def fake_post_json(request_url, request_body, *, headers, timeout):
        transport_observations.update(
            url=request_url, body=request_body, headers=headers, timeout=timeout
        )
        return {"choices": [{"message": {"content": "Northridge Grid"}}]}

    monkeypatch.setattr(
        "lineageweave.customer_hint_resolution.post_json", fake_post_json
    )
    resolution_client = ContextualOrchestratorCustomerHintResolutionClient(
        "http://orchestrator", "secret", reasoning_effort="high", timeout=11.0
    )

    assert (
        resolution_client.resolve("0019999999", "Northridge Grid visited our booth")
        == "Northridge Grid"
    )
    assert transport_observations["url"] == "http://orchestrator/v1/chat/completions"
    assert transport_observations["body"]["mode"] == "auto"
    assert transport_observations["body"]["reasoning_effort"] == "high"
    assert transport_observations["timeout"] == 11.0
    # The opaque hint code is threaded into the prompt so the model knows
    # which records it is naming, even though the code itself never
    # appears in their text.
    assert "0019999999" in transport_observations["body"]["messages"][0]["content"]


def test_live_client_returns_none_when_model_declines(monkeypatch) -> None:
    monkeypatch.setattr(
        "lineageweave.customer_hint_resolution.post_json",
        lambda *call_arguments, **call_keyword_arguments: {
            "choices": [{"message": {"content": "UNKNOWN"}}]
        },
    )
    resolution_client = ContextualOrchestratorCustomerHintResolutionClient(
        "http://orchestrator", "secret"
    )
    assert resolution_client.resolve("0019999999", "ambiguous context") is None
