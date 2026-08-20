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
    client = NullCustomerHintResolutionClient()
    assert client.available is False


def test_live_client_uses_adaptive_orchestrator_mode(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_post_json(url, body, *, headers, timeout):
        seen.update(url=url, body=body, headers=headers, timeout=timeout)
        return {"choices": [{"message": {"content": "Northridge Grid"}}]}

    monkeypatch.setattr("lineageweave.customer_hint_resolution.post_json", fake_post_json)
    client = ContextualOrchestratorCustomerHintResolutionClient(
        "http://orchestrator", "secret", reasoning_effort="high", timeout=11.0
    )

    assert client.resolve("0019999999", "Northridge Grid visited our booth") == "Northridge Grid"
    assert seen["url"] == "http://orchestrator/v1/chat/completions"
    assert seen["body"]["mode"] == "auto"
    assert seen["body"]["reasoning_effort"] == "high"
    assert seen["timeout"] == 11.0
    # The opaque hint code is threaded into the prompt so the model knows
    # which records it is naming, even though the code itself never
    # appears in their text.
    assert "0019999999" in seen["body"]["messages"][0]["content"]


def test_live_client_returns_none_when_model_declines(monkeypatch) -> None:
    monkeypatch.setattr(
        "lineageweave.customer_hint_resolution.post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": "UNKNOWN"}}]},
    )
    client = ContextualOrchestratorCustomerHintResolutionClient("http://orchestrator", "secret")
    assert client.resolve("0019999999", "ambiguous context") is None
