from __future__ import annotations

import pytest

from lineageweave.adjudication_client import ContextualOrchestratorAdjudicationClient
from lineageweave.http_client import HttpClientError


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


def test_adjudication_returns_a_genuine_zero_score_unchanged(monkeypatch) -> None:
    """A real "definitely unrelated" verdict of 0.0 must still work exactly
    as before -- only an unparseable reply should now raise.
    """
    monkeypatch.setattr(
        "lineageweave.adjudication_client.post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": "0.0"}}]},
    )

    client = ContextualOrchestratorAdjudicationClient(
        base_url="http://orchestrator:8000", api_key="synthetic-token"
    )

    assert client.judge("workshop", "unrelated topic") == 0.0


def test_adjudication_raises_instead_of_faking_zero_when_reply_has_no_number(
    monkeypatch,
) -> None:
    """A malformed/unscoreable reply is a channel failure, not a real 0.0
    judgment -- it must be distinguishable from the genuine-zero case above.
    """
    monkeypatch.setattr(
        "lineageweave.adjudication_client.post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": "I cannot answer that."}}]},
    )

    client = ContextualOrchestratorAdjudicationClient(
        base_url="http://orchestrator:8000", api_key="synthetic-token"
    )

    with pytest.raises(HttpClientError):
        client.judge("workshop", "follow-up bid")


def test_adjudication_raises_when_content_is_json_null(monkeypatch) -> None:
    """Some gateways emit ``content: null`` for a moderation-blocked or
    tool-call-only completion. That shape passes the existing key/index
    checks, so it must be caught explicitly instead of crashing the regex
    search with an undocumented TypeError.
    """
    monkeypatch.setattr(
        "lineageweave.adjudication_client.post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": None}}]},
    )

    client = ContextualOrchestratorAdjudicationClient(
        base_url="http://orchestrator:8000", api_key="synthetic-token"
    )

    with pytest.raises(HttpClientError):
        client.judge("workshop", "follow-up bid")


def test_adjudication_raises_when_response_shape_is_malformed(monkeypatch) -> None:
    """A gateway response missing the expected message shape must also raise,
    not be silently coerced into a score.
    """
    monkeypatch.setattr(
        "lineageweave.adjudication_client.post_json",
        lambda *args, **kwargs: {"choices": []},
    )

    client = ContextualOrchestratorAdjudicationClient(
        base_url="http://orchestrator:8000", api_key="synthetic-token"
    )

    with pytest.raises(HttpClientError):
        client.judge("workshop", "follow-up bid")
