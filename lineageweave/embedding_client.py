"""Pluggable embedding channel.

The default :class:`NullEmbeddingClient` makes the channel unavailable
rather than faking a score -- ``reconstruct.active_weights`` drops and
renormalizes around any channel whose client reports ``available = False``.
:class:`ContextualOrchestratorEmbeddingClient` calls the authenticated
contextual-orchestrator ``/v1/batch/embeddings`` boundary once a credential is
set. No client in this repository calls a provider embedding endpoint directly.
"""

from __future__ import annotations

import math
import time
from typing import Protocol

from .chunking import Chunk, chunk_by_paragraph
from .http_client import get_json, post_json


class EmbeddingClient(Protocol):
    """Turns text into a vector, for the cosine-similarity lineage channel."""

    available: bool

    def embed(self, text: str) -> list[float]:
        """Return an embedding for the supplied text."""
        raise NotImplementedError


class NullEmbeddingClient:
    """No embedding provider configured -- the embedding channel is skipped."""

    available = False

    def embed(self, text: str) -> list[float]:  # pragma: no cover
        """Return an embedding for the supplied text."""
        raise RuntimeError("NullEmbeddingClient has no embedding channel; check .available first")


class OpenAiCompatibleEmbeddingClient:
    """Backward-compatible name for the orchestrator-only embedding client."""

    available = True

    def __init__(self, base_url: str, api_key: str, model: str, *, timeout: float = 30.0) -> None:
        self._delegate = ContextualOrchestratorEmbeddingClient(
            base_url, api_key, model, timeout=timeout
        )

    def embed(self, text: str) -> list[float]:
        """Return an embedding for the supplied text."""
        return self._delegate.embed(text)


class ContextualOrchestratorEmbeddingClient:
    """Submit embeddings through contextual-orchestrator's batch boundary."""

    available = True

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout: float = 60.0,
        poll_interval: float = 0.25,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        if not self._base_url.endswith("/v1"):
            self._base_url = f"{self._base_url}/v1"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._poll_interval = poll_interval

    def embed(self, text: str) -> list[float]:
        """Return an embedding for the supplied text."""
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for the supplied texts."""
        if not texts:
            return []
        headers = {"authorization": f"Bearer {self._api_key}"}
        response = post_json(
            f"{self._base_url}/batch/embeddings",
            {
                "model": self._model,
                "inputs": texts,
                "endpoint": "/v1/embeddings",
                "metadata": {"service": "lineageweave", "channel": "post_content_embedding"},
            },
            headers=headers,
            timeout=self._timeout,
        )
        batch_id = response.get("batch_id")
        if isinstance(batch_id, str) and batch_id:
            deadline = time.monotonic() + self._timeout
            while True:
                vectors = self._vectors(response, len(texts))
                if vectors is not None:
                    return vectors
                if response.get("status") in {"failed", "cancelled", "rejected"}:
                    raise RuntimeError("embedding batch did not complete")
                if time.monotonic() >= deadline:
                    raise TimeoutError("embedding batch timed out")
                time.sleep(self._poll_interval)
                response = get_json(
                    f"{self._base_url}/batch/embeddings/{batch_id}",
                    headers=headers,
                    timeout=self._timeout,
                )

        vectors = self._vectors(response, len(texts))
        if vectors is None:
            raise ValueError("embedding response did not contain a complete vector batch")
        return vectors

    @staticmethod
    def _vectors(response: dict, expected: int) -> list[list[float]] | None:
        """Extract and validate one vector per input from provider-neutral payloads."""
        candidate = response.get("vectors")
        if candidate is None:
            data = response.get("data")
            if isinstance(data, list):
                candidate = [item.get("embedding") for item in data if isinstance(item, dict)]
        if not isinstance(candidate, list) or len(candidate) != expected:
            return None
        vectors: list[list[float]] = []
        dimension: int | None = None
        for item in candidate:
            if not isinstance(item, list) or not item:
                return None
            vector = [float(value) for value in item]
            if not all(math.isfinite(value) for value in vector):
                raise ValueError("embedding vector contains a non-finite value")
            if dimension is None:
                dimension = len(vector)
            elif len(vector) != dimension:
                raise ValueError("embedding vectors have inconsistent dimensions")
            vectors.append(vector)
        return vectors


def orchestrator_embedding_client(
    base_url: str,
    api_key: str,
    model: str,
) -> EmbeddingClient:
    """Return the configured orchestrator client or the unavailable sentinel."""
    if not (base_url and api_key and model):
        return NullEmbeddingClient()
    return ContextualOrchestratorEmbeddingClient(base_url, api_key, model)


def embed_chunks(client: EmbeddingClient, chunks: list[Chunk]) -> list[list[float]]:
    """Embed paragraph-level chunks without losing the semantic-unit boundary."""
    if not chunks:
        return []
    embed_many = getattr(client, "embed_many", None)
    if callable(embed_many):
        return embed_many([chunk.text for chunk in chunks])
    return [client.embed(chunk.text) for chunk in chunks]


def embed_text_by_paragraph(client: EmbeddingClient, text: str) -> list[tuple[Chunk, list[float]]]:
    """Chunk text by paragraph and return each chunk with its embedding."""
    chunks = chunk_by_paragraph(text)
    return list(zip(chunks, embed_chunks(client, chunks), strict=True))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity for equal-dimension finite vectors."""
    if len(a) != len(b):
        raise ValueError("vectors must have equal dimensions")
    if not a:
        raise ValueError("vectors must not be empty")
    if not all(math.isfinite(value) for value in (*a, *b)):
        raise ValueError("vectors must contain only finite values")
    norm_a = math.sqrt(sum(value * value for value in a))
    norm_b = math.sqrt(sum(value * value for value in b))
    if norm_a == 0.0 or norm_b == 0.0:
        raise ValueError("vectors must have non-zero magnitude")
    return sum(left * right for left, right in zip(a, b, strict=True)) / (norm_a * norm_b)
