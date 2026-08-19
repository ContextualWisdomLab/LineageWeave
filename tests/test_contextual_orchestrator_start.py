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
