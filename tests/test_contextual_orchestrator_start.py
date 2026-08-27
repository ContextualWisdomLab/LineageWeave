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


def test_container_pin_verifies_provider_host_cli_contract() -> None:
    """The image build fails if its immutable upstream drops the forwarded flag."""
    dockerfile = (
        Path(__file__).parents[1]
        / "docker"
        / "contextual-orchestrator"
        / "Dockerfile"
    ).read_text(encoding="utf-8")

    assert "python -m contextual_orchestrator --help" in dockerfile
    assert "grep -q -- '--allowed-provider-host'" in dockerfile


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


def test_gateway_host_requires_an_explicit_matching_allowlist(monkeypatch) -> None:
    """The bootstrap cannot inherit upstream's open public-host default."""
    module = _load_start_module()
    monkeypatch.delenv("CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS", raising=False)
    with pytest.raises(SystemExit, match="ALLOWED_PROVIDER_HOSTS is required"):
        module._allowed_provider_hosts("https://gateway.example/v1")

    monkeypatch.setenv(
        "CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS", "other.example"
    )
    with pytest.raises(SystemExit, match="not in the provider allowlist"):
        module._allowed_provider_hosts("https://gateway.example/v1")

    monkeypatch.setenv(
        "CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS",
        " gateway.example., OTHER.EXAMPLE ",
    )
    assert module._allowed_provider_hosts("https://GATEWAY.EXAMPLE/v1") == (
        "gateway.example",
        "other.example",
    )


def test_provider_key_is_not_aliased_as_gateway_transport(monkeypatch) -> None:
    module = _load_start_module()
    for name in ("LLM_GATEWAY_API_KEY", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NVIDIA_NIM_API_KEY", "provider-only-key")

    with pytest.raises(SystemExit, match="LLM_GATEWAY_API_KEY or LLM_API_KEY"):
        module.main()


def test_bootstrap_leaves_embedding_selection_to_the_orchestrator(monkeypatch) -> None:
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
    monkeypatch.setenv("LLM_GATEWAY_EMBEDDING_MODEL", "embedding-model")
    monkeypatch.setenv(
        "CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS",
        " secondary.example, gateway.example,secondary.example ",
    )

    module.main()

    argv = captured["argv"]
    assert isinstance(argv, list)
    assert "--embedding-provider-url" not in argv
    assert "--embedding-model" not in argv
    assert argv.count("--allowed-provider-host") == 2
    assert argv[argv.index("--allowed-provider-host") + 1] == "gateway.example"
    assert argv[argv.index("--allowed-provider-host", argv.index("--allowed-provider-host") + 1) + 1] == (
        "secondary.example"
    )
    assert captured["credentials"] == [
        ("LLM_GATEWAY_API_KEY", "provider-key"),
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
    } & os.environ.keys()
    agents = captured["agents"]
    assert isinstance(agents, dict)
    assert agents["agents"][0]["provider_name"] == "configured_gateway"
    assert not [agent for agent in agents["agents"] if "embedding" in agent.get("tags", [])]
    assert "LLM_GATEWAY_EMBEDDING_MODEL" not in os.environ
