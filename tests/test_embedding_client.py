"""Unit tests for the contextual-orchestrator embedding transport."""

from __future__ import annotations

from lineageweave.embedding_client import ContextualOrchestratorEmbeddingClient


def test_orchestrator_embedding_client_submits_and_polls_batch(monkeypatch) -> None:
    calls = []

    def fake_post_json(url, payload, *, headers, timeout):
        calls.append(("post", url, payload, headers))
        return {
            "batch_id": "synthetic-batch",
            "status": "queued",
            "model": "resolved-embedding",
            "poll_after_ms": 1,
            "job_retention_ms": 60_000,
        }

    def fake_get_json(url, *, headers, timeout, service_peer_name):
        assert service_peer_name == "contextual-orchestrator"
        calls.append(("get", url, headers))
        return {
            "batch_id": "synthetic-batch",
            "status": "completed",
            "model": "resolved-embedding",
            "embeddings": [
                {"index": 1, "embedding": [2.0, 3.0]},
                {"index": 0, "embedding": [0.0, 1.0]},
            ],
        }

    monkeypatch.setattr("lineageweave.embedding_client.post_json", fake_post_json)
    monkeypatch.setattr("lineageweave.embedding_client.get_json", fake_get_json)
    client = ContextualOrchestratorEmbeddingClient(
        "http://orchestrator:8000", "synthetic-token", poll_interval=0
    )

    assert client.embed_many(["first", "second"]) == [[0.0, 1.0], [2.0, 3.0]]
    assert calls[0][1] == "http://orchestrator:8000/v1/batch/embeddings"
    assert calls[0][3] == {"authorization": "Bearer synthetic-token"}
    assert "model" not in calls[0][2]
    assert client.resolved_model == "resolved-embedding"

    assert client.embed_many(["third", "fourth"]) == [[0.0, 1.0], [2.0, 3.0]]
    assert calls[2][2]["model"] == "resolved-embedding"


def test_orchestrator_embedding_client_submits_index_aligned_provenance(monkeypatch) -> None:
    """Each bulk input carries its own source metadata and cost attribution."""
    captured = {}

    def fake_post_json(url, payload, *, headers, timeout):
        captured.update(payload)
        return {
            "status": "completed",
            "model": "resolved-embedding",
            "embeddings": [
                {"index": 0, "embedding": [1.0]},
                {"index": 1, "embedding": [2.0]},
            ],
        }

    monkeypatch.setattr("lineageweave.embedding_client.post_json", fake_post_json)
    client = ContextualOrchestratorEmbeddingClient(
        "http://orchestrator:8000", "synthetic-token"
    )

    assert client.embed_many(
        ["first", "second"],
        input_attributions=[{"team": "alpha"}, {"team": "beta"}],
        input_metadata=[{"session_id": "one"}, {"session_id": "two"}],
    ) == [[1.0], [2.0]]
    assert captured["input_attributions"] == [
        {"team": "alpha"},
        {"team": "beta"},
    ]
    assert captured["input_metadata"] == [
        {"session_id": "one"},
        {"session_id": "two"},
    ]
