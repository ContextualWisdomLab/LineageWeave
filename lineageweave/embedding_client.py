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
from collections.abc import Mapping
from typing import Protocol

from .chunking import Chunk, chunk_by_paragraph
from .http_client import get_json, json_request_body, post_json


class EmbeddingClient(Protocol):
    """Turns text into a vector, for the cosine-similarity lineage channel."""

    available: bool
    resolved_model: str | None

    def embed(self, text: str) -> list[float]:
        """Return an embedding for the supplied text."""
        raise NotImplementedError


class NullEmbeddingClient:
    """No embedding provider configured -- the embedding channel is skipped."""

    available = False
    resolved_model = None

    def embed(self, text: str) -> list[float]:  # pragma: no cover
        """Return an embedding for the supplied text."""
        raise RuntimeError("NullEmbeddingClient has no embedding channel; check .available first")


class OpenAiCompatibleEmbeddingClient:
    """Backward-compatible name for the orchestrator-only embedding client."""

    available = True

    def __init__(self, base_url: str, api_key: str, model: str | None = None, *, timeout: float = 30.0) -> None:
        self._delegate = ContextualOrchestratorEmbeddingClient(
            base_url, api_key, model, timeout=timeout
        )

    def embed(self, text: str) -> list[float]:
        """Return an embedding for the supplied text."""
        return self._delegate.embed(text)

    @property
    def resolved_model(self) -> str | None:
        """Return the provider-neutral model identity selected upstream."""
        return self._delegate.resolved_model


class ContextualOrchestratorEmbeddingClient:
    """Submit embeddings through contextual-orchestrator's batch boundary."""

    available = True

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str | None = None,
        *,
        timeout: float = 60.0,
        poll_interval: float = 0.25,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        if not self._base_url.endswith("/v1"):
            self._base_url = f"{self._base_url}/v1"
        self._api_key = api_key
        self._model = model or None
        self._timeout = timeout
        self._poll_interval = poll_interval

    def embed(self, text: str) -> list[float]:
        """Return an embedding for the supplied text."""
        return self.embed_many([text])[0]

    def embed_many(
        self,
        texts: list[str],
        *,
        input_attributions: list[Mapping[str, object]] | None = None,
        input_metadata: list[Mapping[str, object]] | None = None,
    ) -> list[list[float]]:
        """Return embeddings while preserving optional per-input provenance."""
        if not texts:
            return []
        if input_attributions is not None and len(input_attributions) != len(texts):
            raise ValueError("input_attributions must align with texts")
        if input_metadata is not None and len(input_metadata) != len(texts):
            raise ValueError("input_metadata must align with texts")
        headers = {"authorization": f"Bearer {self._api_key}"}
        payload = self.batch_payload(
            texts,
            input_attributions=input_attributions,
            input_metadata=input_metadata,
        )
        response = post_json(
            f"{self._base_url}/batch/embeddings",
            payload,
            headers=headers,
            timeout=self._timeout,
        )
        self._bind_model(response)
        batch_id = response.get("batch_id")
        if isinstance(batch_id, str) and batch_id:
            job_retention_ms = response.get("job_retention_ms")
            if type(job_retention_ms) is not int or job_retention_ms < 1:
                raise ValueError("embedding batch did not declare result retention")
            deadline = time.monotonic() + job_retention_ms / 1000
            while True:
                vectors = self._vectors(response, len(texts))
                if vectors is not None:
                    return vectors
                if response.get("status") in {"failed", "cancelled", "rejected"}:
                    failure = response.get("failure")
                    failure_code = (
                        failure.get("provider_code") or failure.get("error_type")
                        if isinstance(failure, dict)
                        else None
                    )
                    suffix = f": {failure_code}" if failure_code else ""
                    raise RuntimeError(f"embedding batch did not complete{suffix}")
                if time.monotonic() >= deadline:
                    raise TimeoutError("embedding batch timed out")
                poll_after_ms = response.get("poll_after_ms")
                if type(poll_after_ms) is not int or poll_after_ms < 1:
                    raise ValueError("embedding batch did not declare a polling cadence")
                time.sleep(poll_after_ms / 1000)
                response = get_json(
                    f"{self._base_url}/batch/embeddings/{batch_id}",
                    headers=headers,
                    timeout=self._timeout,
                    service_peer_name="contextual-orchestrator",
                )
                self._bind_model(response)

        vectors = self._vectors(response, len(texts))
        if vectors is None:
            raise ValueError("embedding response did not contain a complete vector batch")
        return vectors

    def batch_payload(
        self,
        texts: list[str],
        *,
        input_attributions: list[Mapping[str, object]] | None = None,
        input_metadata: list[Mapping[str, object]] | None = None,
    ) -> dict[str, object]:
        """Build the exact provider-neutral bulk request document."""
        payload: dict[str, object] = {
            "inputs": texts,
            "endpoint": "/v1/embeddings",
            "metadata": {"service": "lineageweave", "channel": "post_content_embedding"},
        }
        if input_attributions is not None:
            payload["input_attributions"] = [dict(value) for value in input_attributions]
        if input_metadata is not None:
            payload["input_metadata"] = [dict(value) for value in input_metadata]
        if self._model is not None:
            payload["model"] = self._model
        return payload

    def batch_request_body_size(
        self,
        texts: list[str],
        *,
        input_attributions: list[Mapping[str, object]] | None = None,
        input_metadata: list[Mapping[str, object]] | None = None,
    ) -> int:
        """Return exact UTF-8 bytes sent for one bulk request."""
        return len(
            json_request_body(
                self.batch_payload(
                    texts,
                    input_attributions=input_attributions,
                    input_metadata=input_metadata,
                )
            )
        )

    def batch_capabilities(self) -> dict[str, int]:
        """Read enforced bulk request ceilings from contextual-orchestrator."""
        headers = {"authorization": f"Bearer {self._api_key}"}
        response = get_json(
            f"{self._base_url}/batch/embeddings/capabilities",
            headers=headers,
            timeout=self._timeout,
            service_peer_name="contextual-orchestrator",
        )
        required = (
            "max_request_body_bytes",
            "max_tokens_per_part",
            "max_chars_per_part",
            "poll_after_ms",
            "job_retention_ms",
        )
        if any(type(response.get(key)) is not int or response[key] < 1 for key in required):
            raise ValueError("embedding batch capabilities are incomplete")
        return {key: int(response[key]) for key in required}

    @property
    def resolved_model(self) -> str | None:
        """Return the provider-neutral model identity selected upstream."""
        return self._model

    def _bind_model(self, response: dict) -> None:
        model = response.get("model")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("embedding response did not identify its resolved model")
        model = model.strip()
        if self._model is not None and model != self._model:
            raise ValueError("embedding batch changed its resolved model")
        self._model = model

    @staticmethod
    def _vectors(response: dict, expected_count: int) -> list[list[float]] | None:
        """Implement the _vectors operation for this channel."""
        raw_vectors = response.get("embeddings")
        if not isinstance(raw_vectors, list) or len(raw_vectors) != expected_count:
            return None
        ordered: list[list[float] | None] = [None] * expected_count
        for item in raw_vectors:
            if not isinstance(item, dict) or not isinstance(item.get("index"), int):
                return None
            index = item["index"]
            vector = item.get("embedding")
            if not 0 <= index < expected_count or not isinstance(vector, list) or not vector:
                return None
            if not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in vector):
                return None
            ordered[index] = [float(value) for value in vector]
        if any(vector is None for vector in ordered):
            return None
        return [vector for vector in ordered if vector is not None]


def orchestrator_embedding_client(base_url: str, api_key: str):
    """Build the batch embedding channel, or the unavailable null client."""
    if not (base_url and api_key):
        return NullEmbeddingClient()
    return ContextualOrchestratorEmbeddingClient(base_url, api_key)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity mapped from ``[-1, 1]`` into the ``[0, 1]`` channel range."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    cosine = dot / (norm_a * norm_b)
    return (cosine + 1.0) / 2.0


def chunked_max_similarity(
    client: EmbeddingClient,
    text_a: str,
    text_b: str,
    *,
    chunker=chunk_by_paragraph,
) -> tuple[float, Chunk, Chunk]:
    """Chunk both documents, embed every chunk, and return the single
    highest-scoring chunk pair.

    Embedding a whole document as one vector dilutes a short relevant unit
    with everything else in the same document. Max-pooling over chunk-pair
    similarity instead asks the right question for lineage matching: "is
    there ANY unit in A that plausibly matches ANY unit in B?" -- the
    standard passage-retrieval strategy for exactly this "relevant content
    is buried in a longer document" shape (see module docstring in
    ``chunking.py`` for the per-unit-type grounding).

    Falls back to whole-text embedding (a single implicit chunk) for any
    document that chunks to zero or one pieces, so short records (this
    project's real dataset's ``title_field``, ~28 characters on average)
    behave exactly as they did before chunking existed -- one embedding
    call each, same as :meth:`EmbeddingClient.embed`.
    """
    raw_chunks_a = chunker(text_a)
    raw_chunks_b = chunker(text_b)
    # Fallback applies for zero OR one chunk, not just zero: a single chunk
    # still means "nothing to max-pool over," and the chunker's own single
    # chunk may be normalized (e.g. paragraph-stripped) rather than the
    # original text, which would silently break the documented "behaves
    # exactly as it did before chunking existed" whole-text-embedding contract.
    chunks_a = raw_chunks_a if len(raw_chunks_a) > 1 else [Chunk(text=text_a, unit_type="whole", index=0)]
    chunks_b = raw_chunks_b if len(raw_chunks_b) > 1 else [Chunk(text=text_b, unit_type="whole", index=0)]

    vectors_a = [(chunk, client.embed(chunk.text)) for chunk in chunks_a]
    vectors_b = [(chunk, client.embed(chunk.text)) for chunk in chunks_b]

    best_score = 0.0
    best_pair: tuple[Chunk, Chunk] = (chunks_a[0], chunks_b[0])
    for chunk_a, vector_a in vectors_a:
        for chunk_b, vector_b in vectors_b:
            score = cosine_similarity(vector_a, vector_b)
            if score > best_score:
                best_score = score
                best_pair = (chunk_a, chunk_b)
    return best_score, best_pair[0], best_pair[1]
