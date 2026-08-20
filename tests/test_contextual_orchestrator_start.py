"""Bootstrap delegates model and provider protocol behavior to the orchestrator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_start_module():
    stubs = {}
    previous = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        path = Path(__file__).parents[1] / "docker" / "contextual-orchestrator" / "start.py"
        spec = importlib.util.spec_from_file_location("lineageweave_contextual_start", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, previous_module in previous.items():
            if previous_module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous_module


def test_bootstrap_does_not_patch_upstream_model_classes() -> None:
    module = _load_start_module()
    assert "ModelClient" not in module.__dict__
    assert "_apply_provider_models" not in module.__dict__


def test_provider_api_url_is_canonical_over_compatibility_aliases(monkeypatch) -> None:
    module = _load_start_module()
    monkeypatch.setenv("LLM_GATEWAY_API_URL", "https://canonical.example/v1")
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://legacy.example/v1")
    monkeypatch.setenv("LLM_API_GATEWAY", "https://local-alias.example/v1")

    assert module._pop_first_env("LLM_GATEWAY_API_URL", "LLM_GATEWAY_URL", "LLM_API_GATEWAY") == (
        "https://canonical.example/v1"
    )


def test_gateway_api_key_accepts_local_compatibility_alias(monkeypatch) -> None:
    module = _load_start_module()
    monkeypatch.setenv("LLM_API_KEY", "compatibility-key")

    assert module._pop_first_env("LLM_GATEWAY_API_KEY", "LLM_API_KEY") == "compatibility-key"
