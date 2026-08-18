from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from urllib.error import HTTPError

import pytest


_PATH = Path(__file__).parents[1] / "docker" / "contextual-orchestrator" / "embedding_compat.py"
_SPEC = importlib.util.spec_from_file_location("lineageweave_embedding_compat_extra", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_provider_payload_is_ordered_and_normalized() -> None:
    rows = _MODULE._ordered_provider_items(
        {
            "data": [
                {"index": 1, "embedding": [2, 3]},
                {"index": 0, "embedding": [1, 2]},
            ]
        },
        2,
        "embed-model",
    )

    assert rows == [
        {"index": 0, "embedding": [1.0, 2.0], "prompt_tokens": 0, "model": "embed-model"},
        {"index": 1, "embedding": [2.0, 3.0], "prompt_tokens": 0, "model": "embed-model"},
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": [{"embedding": [1]}]},
        {"data": [{"index": 0, "embedding": []}]},
        {"data": [{"index": 0, "embedding": [float("nan")]}]},
        {"data": [{"index": 0, "embedding": [1]}, {"index": 0, "embedding": [2]}]},
        {"data": [{"index": 1, "embedding": [1]}]},
    ],
)
def test_provider_payload_errors_fail_closed(payload: dict) -> None:
    with pytest.raises(RuntimeError):
        _MODULE._ordered_provider_items(payload, 2, "embed-model")


class _Request:
    def __init__(self, custom_id: str, text: str, model: str = "embed-model") -> None:
        self.custom_id = custom_id
        self.input_text = text
        self.model = model
        self.attribution: dict[str, str] = {}


def _install_batch_types(monkeypatch: pytest.MonkeyPatch) -> None:
    package = types.ModuleType("contextual_orchestrator")
    batch = types.ModuleType("contextual_orchestrator.batch_routing")

    class BatchJob:
        def __init__(self, job_id: str, backend: str, status: str, request_count: int) -> None:
            self.job_id = job_id
            self.backend = backend
            self.status = status
            self.request_count = request_count

    class EmbeddingBatchResultItem:
        def __init__(self, **kwargs: object) -> None:
            self.__dict__.update(kwargs)

    batch.BatchJob = BatchJob
    batch.EmbeddingBatchResultItem = EmbeddingBatchResultItem
    package.batch_routing = batch
    monkeypatch.setitem(sys.modules, "contextual_orchestrator", package)
    monkeypatch.setitem(sys.modules, "contextual_orchestrator.batch_routing", batch)


def test_provider_backend_submit_poll_retrieve_and_attribution(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_batch_types(monkeypatch)
    backend = _MODULE.ProviderEmbeddingBatchBackend("https://gateway.example/v1", {"embed-model"})
    monkeypatch.setattr(
        backend,
        "_post",
        lambda model, inputs: {
            "data": [
                {"index": 1, "embedding": [0.2]},
                {"index": 0, "embedding": [0.1]},
            ]
        },
    )
    requests = [_Request("a", "first"), _Request("b", "second")]

    job = backend.submit(requests)
    assert job.backend == "provider"
    assert job.status == "completed"
    assert backend.poll(job)["is_complete"] is True
    results = backend.retrieve(job)
    assert [result.custom_id for result in results] == ["a", "b"]
    assert all(request.attribution["provider"] == "gateway.example" for request in requests)


def test_provider_backend_rejects_empty_or_unallowlisted_batches() -> None:
    backend = _MODULE.ProviderEmbeddingBatchBackend("https://gateway.example/v1", {"embed-model"})
    with pytest.raises(ValueError):
        backend.submit([])
    with pytest.raises(ValueError):
        backend.submit([_Request("a", "first", model="other-model")])
    with pytest.raises(ValueError):
        backend.submit([_Request("a", "first"), _Request("b", "second", model="other-model")])


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = json.dumps(payload).encode()

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_provider_http_post_uses_gateway_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    credentials = types.ModuleType("contextual_orchestrator.credentials")
    credentials.get_credential = lambda name: "gateway-secret" if name == "LLM_GATEWAY_API_KEY" else None
    monkeypatch.setitem(sys.modules, "contextual_orchestrator.credentials", credentials)
    captured: dict[str, object] = {}

    def urlopen(request: object, timeout: float) -> _Response:
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response({"data": []})

    monkeypatch.setattr(_MODULE, "urlopen", urlopen)
    backend = _MODULE.ProviderEmbeddingBatchBackend("https://gateway.example/v1", {"embed-model"}, timeout=7)

    assert backend._post("embed-model", ["a"]) == {"data": []}
    assert captured["timeout"] == 7
    request = captured["request"]
    assert request.full_url.endswith("/embeddings")
    assert request.get_header("Authorization") == "Bearer gateway-secret"


def test_provider_http_errors_are_not_exposed(monkeypatch: pytest.MonkeyPatch) -> None:
    credentials = types.ModuleType("contextual_orchestrator.credentials")
    credentials.get_credential = lambda _name: "gateway-secret"
    monkeypatch.setitem(sys.modules, "contextual_orchestrator.credentials", credentials)

    def urlopen(*_args: object, **_kwargs: object) -> None:
        raise HTTPError("https://gateway.example/v1/embeddings", 502, "bad gateway", {}, None)

    monkeypatch.setattr(_MODULE, "urlopen", urlopen)
    backend = _MODULE.ProviderEmbeddingBatchBackend("https://gateway.example/v1", {"embed-model"})
    with pytest.raises(RuntimeError, match="embedding provider request failed"):
        backend._post("embed-model", ["a"])


def test_unavailable_backend_fails_closed() -> None:
    backend = _MODULE.UnavailableEmbeddingBatchBackend()
    for method, args in ((backend.submit, ([],)), (backend.poll, (object(),)), (backend.retrieve, (object(),))):
        with pytest.raises(RuntimeError, match="not configured"):
            method(*args)


def test_install_provider_embedding_support_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    package = types.ModuleType("contextual_orchestrator")
    cost_router = types.ModuleType("contextual_orchestrator.cost_router")

    class CostRoutingCoordinator:
        def __init__(self) -> None:
            self.embedding_batch_backend = "local"

    cost_router.CostRoutingCoordinator = CostRoutingCoordinator
    package.cost_router = cost_router
    monkeypatch.setitem(sys.modules, "contextual_orchestrator", package)
    monkeypatch.setitem(sys.modules, "contextual_orchestrator.cost_router", cost_router)

    _MODULE.install_provider_embedding_support("https://gateway.example/v1", "embed-model")
    first = CostRoutingCoordinator().embedding_batch_backend
    _MODULE.install_provider_embedding_support("https://other.example/v1", "other-model")
    second = CostRoutingCoordinator().embedding_batch_backend

    assert first.name == "provider"
    assert second is first
