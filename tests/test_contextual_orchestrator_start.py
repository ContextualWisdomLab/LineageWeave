"""Bootstrap keeps explicit Vision model selection inside the orchestrator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_start_module():
    stubs = {
        "embedding_compat": ModuleType("embedding_compat"),
        "provider_policy": ModuleType("provider_policy"),
        "vision_compat": ModuleType("vision_compat"),
    }
    stubs["embedding_compat"].install_provider_embedding_support = lambda *args: None
    stubs["provider_policy"].is_local_mlx_provider = lambda value: False
    stubs["vision_compat"].install_multimodal_chat_support = lambda: None
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


def test_explicit_vision_model_does_not_get_replaced_by_text_model() -> None:
    module = _load_start_module()
    agents = [
        {"id": "vision", "model": "default-vision", "tags": ["vision"]},
        {"id": "text", "model": "default-text", "tags": ["writing"]},
    ]

    module._apply_provider_models(agents, "text-model", "vision-model")

    assert agents[0]["model"] == "vision-model"
    assert agents[1]["model"] == "text-model"


def test_text_model_is_used_when_no_vision_override_exists() -> None:
    module = _load_start_module()
    agents = [{"id": "vision", "model": "default-vision", "tags": ["vision"]}]

    module._apply_provider_models(agents, "text-model", "")

    assert agents[0]["model"] == "text-model"


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
