from __future__ import annotations

import pytest

from lineageweave import embedding_client
from lineageweave.http_client import json_request_body
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata


def test_missing_embedding_configuration_returns_null_client() -> None:
    client = embedding_client.orchestrator_embedding_client("", "")
    assert isinstance(client, embedding_client.NullEmbeddingClient)
    assert client.available is False
    with pytest.raises(RuntimeError, match="no embedding channel"):
        client.embed("text")


def test_empty_batch_does_not_call_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedding_client, "post_json", lambda *_args, **_kwargs: pytest.fail("unexpected call"))
    client = embedding_client.ContextualOrchestratorEmbeddingClient("http://orchestrator", "key", "model")
    assert client.embed_many([]) == []


@pytest.mark.parametrize("field", ["input_attributions", "input_metadata"])
def test_per_input_context_must_align_with_texts(field: str) -> None:
    client = embedding_client.ContextualOrchestratorEmbeddingClient(
        "http://orchestrator", "key", "model"
    )

    with pytest.raises(ValueError, match=field):
        client.embed_many(["first", "second"], **{field: [{"key": "value"}]})


def test_batch_capabilities_require_positive_integer_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        embedding_client,
        "get_json",
        lambda *_args, **_kwargs: {
            "max_request_body_bytes": 65_536,
            "max_inputs": 2048,
            "max_total_tokens": 300_000,
            "max_tokens_per_part": 280_000,
            "max_chars_per_part": 240_000,
            "poll_after_ms": 1_000,
            "job_retention_ms": 60_000,
        },
    )
    client = embedding_client.ContextualOrchestratorEmbeddingClient(
        "http://orchestrator", "key"
    )
    assert client.batch_capabilities()["max_request_body_bytes"] == 65_536

    monkeypatch.setattr(embedding_client, "get_json", lambda *_args, **_kwargs: {})
    with pytest.raises(ValueError, match="capabilities are incomplete"):
        client.batch_capabilities()


def test_immediate_embedding_response_is_ordered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        embedding_client,
        "post_json",
        lambda *_args, **_kwargs: {
            "model": "model",
            "embeddings": [
                {"index": 1, "embedding": [2]},
                {"index": 0, "embedding": [1]},
            ]
        },
    )
    client = embedding_client.ContextualOrchestratorEmbeddingClient("http://orchestrator/v1", "key", "model")
    assert client.embed_many(["a", "b"]) == [[1.0], [2.0]]


def test_batch_response_polls_until_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter([
        {
            "batch_id": "batch-1",
            "status": "pending",
            "model": "model",
            "poll_after_ms": 1_000,
            "job_retention_ms": 60_000,
        }
    ])
    monkeypatch.setattr(embedding_client, "post_json", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(
        embedding_client,
        "get_json",
        lambda *_args, **_kwargs: {
            "model": "model",
            "embeddings": [{"index": 0, "embedding": [0.5]}],
        },
    )
    monkeypatch.setattr(embedding_client.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(embedding_client.time, "monotonic", lambda: 0.0)
    client = embedding_client.ContextualOrchestratorEmbeddingClient("http://orchestrator", "key", "model", timeout=1)
    assert client.embed_many(["a"]) == [[0.5]]


def test_failed_batch_raises_without_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        embedding_client,
        "post_json",
        lambda *_args, **_kwargs: {
            "batch_id": "batch-1",
            "status": "failed",
            "model": "model",
            "poll_after_ms": 1_000,
            "job_retention_ms": 60_000,
        },
    )
    client = embedding_client.ContextualOrchestratorEmbeddingClient("http://orchestrator", "key", "model")
    with pytest.raises(RuntimeError, match="did not complete"):
        client.embed_many(["a"])


def test_batch_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        embedding_client,
        "post_json",
        lambda *_args, **_kwargs: {
            "batch_id": "batch-1",
            "status": "pending",
            "model": "model",
            "poll_after_ms": 1_000,
            "job_retention_ms": 1_000,
        },
    )
    monkeypatch.setattr(embedding_client.time, "monotonic", iter([0.0, 2.0]).__next__)
    client = embedding_client.ContextualOrchestratorEmbeddingClient("http://orchestrator", "key", "model", timeout=1)
    with pytest.raises(TimeoutError, match="timed out"):
        client.embed_many(["a"])


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"embeddings": []},
        {"embeddings": [{"index": 0, "embedding": []}]},
        {"embeddings": [{"index": 0, "embedding": [float("nan")]}]},
        {"embeddings": [{"index": 2, "embedding": [1]}]},
    ],
)
def test_invalid_embedding_vectors_are_rejected(response: dict) -> None:
    assert embedding_client.ContextualOrchestratorEmbeddingClient._vectors(response, 1) is None


def test_missing_resolved_model_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        embedding_client,
        "post_json",
        lambda *_args, **_kwargs: {"embeddings": [{"index": 0, "embedding": [1.0]}]},
    )
    client = embedding_client.ContextualOrchestratorEmbeddingClient(
        "http://orchestrator", "key"
    )
    with pytest.raises(ValueError, match="resolved model"):
        client.embed_many(["a"])


def test_legacy_client_name_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    class Delegate:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def embed(self, text: str) -> list[float]:
            return [float(len(text))]

    monkeypatch.setattr(embedding_client, "ContextualOrchestratorEmbeddingClient", Delegate)
    client = embedding_client.OpenAiCompatibleEmbeddingClient("http://orchestrator", "key", "model")
    assert client.embed("abc") == [3.0]
def test_batch_body_size_matches_post_scoped_orchestrator_wire_body() -> None:
    """The advertised ceiling includes the injected post session field."""
    client = embedding_client.ContextualOrchestratorEmbeddingClient(
        "http://orchestrator", "synthetic-key"
    )
    payload = client.batch_payload(["synthetic semantic unit"])
    metadata = build_post_llm_metadata("synthetic-post", {})

    with use_llm_metadata(metadata):
        assert client.batch_request_body_size(["synthetic semantic unit"]) == len(
            json_request_body(payload, include_orchestrator_session=True)
        )
