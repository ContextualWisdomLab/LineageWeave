"""Provider-backed embeddings for the pinned contextual-orchestrator.

The upstream standalone embedding backend is intentionally not used by the
real Compose service: its deterministic eight-dimensional vector is useful for
offline tests but is not a semantic signal. Production requests must cross the
same allowlisted provider boundary as chat and vision.
"""

from __future__ import annotations

import json
import math
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


def _ordered_provider_items(
    payload: dict[str, Any], expected_count: int, model: str
) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != expected_count:
        raise RuntimeError("embedding provider returned an incomplete data array")

    ordered: list[dict[str, Any] | None] = [None] * expected_count
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("index"), int):
            raise RuntimeError("embedding provider returned an invalid index")
        index = item["index"]
        vector = item.get("embedding")
        if not 0 <= index < expected_count or not isinstance(vector, list) or not vector:
            raise RuntimeError("embedding provider returned an invalid vector")
        if not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in vector):
            raise RuntimeError("embedding provider returned a non-finite vector")
        if ordered[index] is not None:
            raise RuntimeError("embedding provider returned a duplicate index")
        ordered[index] = {
            "index": index,
            "embedding": [float(value) for value in vector],
            "prompt_tokens": 0,
            "model": model,
        }
    if any(item is None for item in ordered):
        raise RuntimeError("embedding provider omitted a vector")
    return [item for item in ordered if item is not None]


class ProviderEmbeddingBatchBackend:
    """Submit embedding batches to the configured provider from the orchestrator."""

    name = "provider"

    def __init__(self, base_url: str, allowed_models: set[str], *, timeout: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._allowed_models = frozenset(allowed_models)
        self._timeout = timeout
        self._provider = urlparse(base_url).hostname or "provider"
        self._results: dict[str, list[Any]] = {}

    def submit(self, requests: list[Any], metadata: dict[str, Any] | None = None) -> Any:
        if not requests:
            raise ValueError("embedding batch must not be empty")
        models = {request.model for request in requests}
        if len(models) != 1 or not models.issubset(self._allowed_models):
            raise ValueError("embedding model is not allowlisted")
        model = next(iter(models))
        for request in requests:
            request.attribution.setdefault("provider", self._provider)
        body = self._post(model, [request.input_text for request in requests])
        rows = _ordered_provider_items(body, len(requests), model)
        from contextual_orchestrator.batch_routing import BatchJob, EmbeddingBatchResultItem

        batch_id = f"providerembed_{uuid.uuid4().hex}"
        self._results[batch_id] = [
            EmbeddingBatchResultItem(
                custom_id=request.custom_id,
                index=row["index"],
                embedding=row["embedding"],
                prompt_tokens=row["prompt_tokens"],
                model=row["model"],
            )
            for request, row in zip(requests, rows)
        ]
        return BatchJob(job_id=batch_id, backend=self.name, status="completed", request_count=len(requests))

    def poll(self, job: Any) -> dict[str, Any]:
        return {"job_id": job.job_id, "status": "completed", "is_complete": True}

    def retrieve(self, job: Any) -> list[Any]:
        return self._results.get(job.job_id, [])

    def _post(self, model: str, inputs: list[str]) -> dict[str, Any]:
        from contextual_orchestrator.credentials import get_credential

        request = Request(
            f"{self._base_url}/embeddings",
            data=json.dumps({"model": model, "input": inputs}).encode("utf-8"),
            headers={
                "authorization": f"Bearer {get_credential('LLM_GATEWAY_API_KEY') or ''}",
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:  # nosec B310 - URL is Compose provider configuration.
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("embedding provider request failed") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("embedding provider returned an invalid response")
        return payload


class UnavailableEmbeddingBatchBackend:
    """Fail closed when no semantic embedding provider model is configured."""

    name = "unavailable"

    def submit(self, requests: list[Any], metadata: dict[str, Any] | None = None) -> Any:
        raise RuntimeError("semantic embedding provider is not configured")

    def poll(self, job: Any) -> dict[str, Any]:
        raise RuntimeError("semantic embedding provider is not configured")

    def retrieve(self, job: Any) -> list[Any]:
        raise RuntimeError("semantic embedding provider is not configured")


def install_provider_embedding_support(provider_url: str, embedding_model: str) -> None:
    """Replace the standalone local backend in the running orchestrator service."""
    from contextual_orchestrator import cost_router

    if getattr(cost_router.CostRoutingCoordinator, "_lineageweave_embedding_compat", False):
        return
    backend = (
        ProviderEmbeddingBatchBackend(provider_url, {embedding_model})
        if embedding_model
        else UnavailableEmbeddingBatchBackend()
    )
    original_init = cost_router.CostRoutingCoordinator.__init__

    def init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        self.embedding_batch_backend = backend

    cost_router.CostRoutingCoordinator.__init__ = init
    cost_router.CostRoutingCoordinator._lineageweave_embedding_compat = True
