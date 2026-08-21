from lineageweave.keyman_extraction import ContextualOrchestratorKeymanExtractionClient


def test_keyman_extraction_sends_author_context_hints(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_post_json(url, payload, *, headers, timeout):
        captured["prompt"] = payload["messages"][0]["content"]
        return {"choices": [{"message": {"content": "[]"}}]}

    monkeypatch.setattr("lineageweave.keyman_extraction.post_json", fake_post_json)
    client = ContextualOrchestratorKeymanExtractionClient("http://orchestrator.test", "synthetic")

    assert client.extract_with_hints(
        "Synthetic title",
        "Synthetic body",
        "author=Synthetic Author; author_affiliations=Synthetic Corp; customer_hint_trust=low",
    ) == []
    assert "author=Synthetic Author" in captured["prompt"]
    assert "customer_hint_trust=low" in captured["prompt"]
