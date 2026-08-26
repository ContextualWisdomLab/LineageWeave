"""Bootstrap delegates model and provider protocol behavior to the orchestrator."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest


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


def test_provider_key_is_not_aliased_as_gateway_transport(monkeypatch) -> None:
    module = _load_start_module()
    for name in ("LLM_GATEWAY_API_KEY", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NVIDIA_NIM_API_KEY", "provider-only-key")

    with pytest.raises(SystemExit, match="LLM_GATEWAY_API_KEY or LLM_API_KEY"):
        module.main()


def test_bootstrap_delegates_embedding_discovery_upstream(monkeypatch) -> None:
    module = _load_start_module()
    captured: dict[str, object] = {}

    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def read_text(self, *, encoding: str) -> str:
            assert self.value == "/app/agents.json"
            assert encoding == "utf-8"
            return json.dumps({"agents": [{}]})

        def write_text(self, value: str, *, encoding: str) -> None:
            assert self.value == "/tmp/lineageweave-agents.json"
            assert encoding == "utf-8"
            captured["agents"] = json.loads(value)

    credentials = types.ModuleType("contextual_orchestrator.credentials")

    def register_credential(name: str, value: str) -> None:
        captured.setdefault("credentials", []).append((name, value))

    credentials.register_credential = register_credential
    server = types.ModuleType("contextual_orchestrator.__main__")

    def serve() -> None:
        captured["argv"] = list(sys.argv)

    server.main = serve
    package = types.ModuleType("contextual_orchestrator")
    package.__path__ = []
    monkeypatch.setitem(sys.modules, "contextual_orchestrator", package)
    monkeypatch.setitem(sys.modules, "contextual_orchestrator.credentials", credentials)
    monkeypatch.setitem(sys.modules, "contextual_orchestrator.__main__", server)
    monkeypatch.setattr(module, "Path", FakePath)
    monkeypatch.setattr(sys, "argv", ["start.py"])
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "provider-key")
    monkeypatch.setenv("LLM_API_KEY", "legacy-provider-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("NVIDIA_NIM_API_KEY", "nim-key")
    monkeypatch.setenv("NVIDIA_NIM_API_KEY_SUB", "nim-sub-key")
    monkeypatch.setenv("BYTEZ_API_KEY", "bytez-key")
    monkeypatch.setenv("CONTEXTUAL_ORCHESTRATOR_TOKEN", "orchestrator-token")
    monkeypatch.setenv("LLM_GATEWAY_API_URL", "https://gateway.example")
    monkeypatch.setenv("BATCH_JOB_REGISTRY_VALKEY_URL", "redis://valkey:6379/1")

    module.main()

    argv = captured["argv"]
    assert isinstance(argv, list)
    assert "--embedding-provider-url" not in argv
    assert "--embedding-model" not in argv
    assert captured["credentials"] == [
        ("LLM_GATEWAY_API_KEY", "provider-key"),
        ("batch_job_registry_valkey_url", "redis://valkey:6379/1"),
        ("OPENAI_API_KEY", "openai-key"),
        ("OPENROUTER_API_KEY", "openrouter-key"),
        ("NVIDIA_NIM_API_KEY", "nim-key"),
        ("NVIDIA_NIM_API_KEY_SUB", "nim-sub-key"),
        ("BYTEZ_API_KEY", "bytez-key"),
    ]
    assert not {
        "LLM_GATEWAY_API_KEY",
        "LLM_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "NVIDIA_NIM_API_KEY",
        "NVIDIA_NIM_API_KEY_SUB",
        "BYTEZ_API_KEY",
        "BATCH_JOB_REGISTRY_VALKEY_URL",
    } & os.environ.keys()
    agents = captured["agents"]
    assert isinstance(agents, dict)
    assert not [agent for agent in agents["agents"] if "embedding" in agent.get("tags", [])]
    assert "--auto-discover-model-agents" in argv
