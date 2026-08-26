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
                ),
                include_orchestrator_session=True,
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
            "max_inputs",
            "max_total_tokens",
            "max_tokens_per_part",
            "max_chars_per_part",
            "poll_after_ms",
            "job_retention_ms",
        )
        if any(type(response.get(key)) is not int or response[key] < 1 for key in required):
            raise ValueError("embedding batch capabilities are incomplete")
        model = response.get("model")
        if isinstance(model, str) and model.strip():
            self._bind_model(response)
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
