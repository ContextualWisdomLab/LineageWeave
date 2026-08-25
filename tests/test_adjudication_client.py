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
