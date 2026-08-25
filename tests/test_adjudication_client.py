from __future__ import annotations

import pytest

from lineageweave.adjudication_client import (
    AdjudicationClientError,
    ContextualOrchestratorAdjudicationClient,
    parse_confidence_response,
)
from lineageweave.http_client import HttpClientError


@pytest.mark.parametrize("content", ["0", "0.75", "1", "1.000"])
def test_parse_confidence_response_accepts_only_bounded_numbers(content: str) -> None:
    """A compliant number-only response becomes its exact unit score."""
    assert parse_confidence_response(content) == float(content)


@pytest.mark.parametrize("content", ["", "maybe 0.75", "2.0", "0.75 extra", ".5"])
def test_parse_confidence_response_rejects_malformed_or_out_of_range_text(content: str) -> None:
    """Malformed provider output is not silently converted to confidence zero."""
    with pytest.raises(AdjudicationClientError):
        parse_confidence_response(content)


def test_parse_confidence_response_rejects_non_text_payload() -> None:
    """A structured provider payload cannot masquerade as a score."""
    with pytest.raises(AdjudicationClientError, match="not text"):
        parse_confidence_response({"score": 0.5})


def test_adjudication_client_rejects_provider_score_outside_unit_interval(monkeypatch) -> None:
    """An out-of-range score is rejected instead of being clamped."""
    monkeypatch.setattr(
        "lineageweave.adjudication_client.post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": "1.2"}}]},
    )
    client = ContextualOrchestratorAdjudicationClient(
        "https://orchestrator.invalid", "synthetic-key"
    )
    with pytest.raises(AdjudicationClientError, match="0..1"):
        client.judge("Parent", "Child")


def test_adjudication_uses_supported_auto_mode_and_long_local_timeout(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post_json(url, payload, *, headers, timeout):
        captured.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {"choices": [{"message": {"content": "0.75"}}]}

    monkeypatch.setattr("lineageweave.adjudication_client.post_json", fake_post_json)

    client = ContextualOrchestratorAdjudicationClient(
        base_url="http://orchestrator:8000", api_key="synthetic-token"
    )

    assert client.judge("workshop", "follow-up bid") == 0.75
    assert captured["url"] == "http://orchestrator:8000/v1/chat/completions"
    assert captured["payload"]["mode"] == "auto"
    assert captured["payload"]["reasoning_effort"] == "auto"
    assert captured["timeout"] == 180.0


@pytest.mark.parametrize(
    "body",
    [
        {"choices": [{"message": {"content": "not a score"}}]},
        {"choices": []},
        {"choices": [{"message": {"content": None}}]},
    ],
)
def test_adjudication_fails_closed_for_unscoreable_responses(monkeypatch, body) -> None:
    """A provider failure must not become a genuine unrelated score of zero."""
    monkeypatch.setattr(
        "lineageweave.adjudication_client.post_json", lambda *args, **kwargs: body
    )
    client = ContextualOrchestratorAdjudicationClient(
        base_url="http://orchestrator:8000", api_key="synthetic-token"
    )

    with pytest.raises(HttpClientError):
        client.judge("workshop", "follow-up bid")
