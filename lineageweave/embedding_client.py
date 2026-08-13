"""Pluggable embedding channel.

The default :class:`NullEmbeddingClient` makes the channel unavailable
rather than faking a score -- ``reconstruct.active_weights`` drops and
renormalizes around any channel whose client reports ``available = False``.
:class:`OpenAiCompatibleEmbeddingClient` calls any OpenAI-compatible
``/v1/embeddings`` endpoint (contextual-orchestrator's ``/v1/batch/embeddings``,
a company LLM gateway, or a hosted provider) once a credential is set.
"""

from __future__ import annotations

import json
import math
import ssl
import urllib.request
from typing import Protocol

import certifi

# Some interpreter distributions (notably standalone uv/pyenv-managed
# builds on macOS) don't reliably inherit the OS trust store the way a
# browser or curl does, so the stdlib ssl module's default context can
# reject a perfectly valid, publicly-trusted certificate. Pointing
# explicitly at certifi's maintained bundle keeps full chain validation
# (nothing is weakened) while working the same way on every platform.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class EmbeddingClient(Protocol):
    """Turns text into a vector, for the cosine-similarity lineage channel."""

    available: bool

    def embed(self, text: str) -> list[float]: ...


class NullEmbeddingClient:
    """No embedding provider configured -- the embedding channel is skipped."""

    available = False

    def embed(self, text: str) -> list[float]:  # pragma: no cover
        raise RuntimeError("NullEmbeddingClient has no embedding channel; check .available first")


class OpenAiCompatibleEmbeddingClient:
    """Calls an OpenAI-compatible ``POST {base_url}/embeddings`` endpoint."""

    available = True

    def __init__(self, base_url: str, api_key: str, model: str, *, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def embed(self, text: str) -> list[float]:
        payload = json.dumps({"model": self._model, "input": text}).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/embeddings",
            data=payload,
            headers={"authorization": f"Bearer {self._api_key}", "content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout, context=_SSL_CONTEXT) as response:  # nosec B310 -- base_url is operator-configured, not request-controlled.
            body = json.loads(response.read().decode("utf-8"))
        return body["data"][0]["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity mapped from ``[-1, 1]`` into the ``[0, 1]`` channel range."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    cosine = dot / (norm_a * norm_b)
    return (cosine + 1.0) / 2.0
