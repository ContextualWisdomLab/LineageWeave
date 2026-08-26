"""Unit tests for embedding_client.chunked_max_similarity's whole-text
fallback contract, using a fake (non-real-provider) client -- no network,
no credentials needed. The real-provider test in
tests/test_real_provider_integration.py proves the same function works
against a live embedding endpoint; this file proves the fallback logic
itself is correct regardless of provider.
"""

from __future__ import annotations

from lineageweave.chunking import Chunk
from lineageweave.embedding_client import (
    ContextualOrchestratorEmbeddingClient,
    chunked_max_similarity,
)


class _RecordingFakeEmbeddingClient:
    """Deterministic fake: embeds a string as a length-1 vector of its own
    length, so equal-length strings score identically and call counts are
    trivially inspectable.
    """

    available = True

    def __init__(self) -> None:
        self.embed_calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [float(len(text))]


def _chunk_to_two_pieces(text: str) -> list[Chunk]:
    half = len(text) // 2
    return [
        Chunk(text=text[:half], unit_type="paragraph", index=0),
        Chunk(text=text[half:], unit_type="paragraph", index=1),
    ]


def _chunk_to_one_piece(text: str) -> list[Chunk]:
    # Deliberately NOT the identical string -- a real chunker normalizes
    # (e.g. strips/collapses whitespace), which is exactly the case the
    # fallback must override so the original text still gets embedded.
    return [Chunk(text=text.strip(), unit_type="paragraph", index=0)]


def _chunk_to_zero_pieces(text: str) -> list[Chunk]:
    return []


def test_falls_back_to_whole_text_when_chunker_returns_zero_pieces() -> None:
    client = _RecordingFakeEmbeddingClient()
    original = "  padded text with whitespace  "

    _, chunk_a, chunk_b = chunked_max_similarity(client, original, "other", chunker=_chunk_to_zero_pieces)

    assert chunk_a.unit_type == "whole"
    assert chunk_a.text == original  # original whitespace preserved, not stripped
    assert client.embed_calls.count(original) == 1


def test_falls_back_to_whole_text_when_chunker_returns_exactly_one_piece() -> None:
    client = _RecordingFakeEmbeddingClient()
    original = "  padded text with whitespace  "

    _, chunk_a, chunk_b = chunked_max_similarity(client, original, "other", chunker=_chunk_to_one_piece)

    assert chunk_a.unit_type == "whole"
    assert chunk_a.text == original  # the chunker's stripped version must NOT be used
    assert client.embed_calls.count(original) == 1
    # Exactly one embedding call for this document -- the chunker's own
    # (normalized) chunk is never embedded once the fallback applies.
    assert client.embed_calls.count(original.strip()) == 0


def test_uses_chunker_output_directly_when_it_returns_two_or_more_pieces() -> None:
    client = _RecordingFakeEmbeddingClient()

    _, chunk_a, chunk_b = chunked_max_similarity(
        client, "abcdefgh", "ijklmnop", chunker=_chunk_to_two_pieces
    )

    assert chunk_a.unit_type == "paragraph"
    assert chunk_b.unit_type == "paragraph"
    # Both documents chunk into 2 pieces each via _chunk_to_two_pieces --
    # the fallback must NOT engage, so every chunk gets its own embed call.
    assert len(client.embed_calls) == 4


def test_orchestrator_embedding_client_submits_and_polls_batch(monkeypatch) -> None:
    calls = []

    def fake_post_json(url, payload, *, headers, timeout):
        calls.append(("post", url, payload, headers))
        return {
            "batch_id": "synthetic-batch",
            "status": "queued",
            "model": "resolved-embedding",
            "poll_after_ms": 1,
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
