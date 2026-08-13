"""Unit tests for embedding_client.chunked_max_similarity's whole-text
fallback contract, using a fake (non-real-provider) client -- no network,
no credentials needed. The real-provider test in
tests/test_real_provider_integration.py proves the same function works
against a live embedding endpoint; this file proves the fallback logic
itself is correct regardless of provider.
"""

from __future__ import annotations

from lineageweave.chunking import Chunk
from lineageweave.embedding_client import chunked_max_similarity


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
