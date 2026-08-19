"""Local provider exceptions stay explicit and port-scoped."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_PATH = Path(__file__).parents[1] / "docker" / "contextual-orchestrator" / "provider_policy.py"
_SPEC = importlib.util.spec_from_file_location("lineageweave_provider_policy", _PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_explicit_local_text_and_vision_ports_are_allowed() -> None:
    assert _MODULE.is_local_mlx_provider("http://host.docker.internal:8080/v1")
    assert _MODULE.is_local_mlx_provider("http://host.docker.internal:18082/v1")


def test_other_local_ports_and_remote_http_are_rejected() -> None:
    assert not _MODULE.is_local_mlx_provider("http://host.docker.internal:18083/v1")
    assert not _MODULE.is_local_mlx_provider("http://127.0.0.1:18082/v1")
    assert not _MODULE.is_local_mlx_provider("https://host.docker.internal:18082/v1")
