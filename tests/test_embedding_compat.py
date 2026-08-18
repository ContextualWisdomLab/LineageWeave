from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_MODULE_PATH = Path(__file__).parents[1] / "docker" / "contextual-orchestrator" / "embedding_compat.py"
_SPEC = importlib.util.spec_from_file_location("lineageweave_embedding_compat", _MODULE_PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_provider_vectors_are_ordered_and_converted_to_floats() -> None:
    rows = _MODULE._ordered_provider_items(
        {
            "data": [
                {"index": 1, "embedding": [2, 3]},
                {"index": 0, "embedding": [1, 4]},
            ]
        },
        2,
        "text-embedding-3-large",
    )

    assert rows[0]["index"] == 0
    assert rows[0]["embedding"] == [1.0, 4.0]
    assert rows[1]["model"] == "text-embedding-3-large"


@pytest.mark.parametrize(
    "payload",
    [
        {"data": [{"index": 0, "embedding": []}]},
        {"data": [{"index": 0, "embedding": [float("nan")]}]},
        {"data": [{"index": 0, "embedding": [1]}, {"index": 0, "embedding": [2]}]},
    ],
)
def test_provider_vectors_reject_invalid_payloads(payload: dict) -> None:
    with pytest.raises(RuntimeError):
        _MODULE._ordered_provider_items(payload, 1, "text-embedding-3-large")


def test_unavailable_backend_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="not configured"):
        _MODULE.UnavailableEmbeddingBatchBackend().submit([object()])
