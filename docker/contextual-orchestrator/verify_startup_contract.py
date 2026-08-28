"""Build-time integration proof for the pinned gateway discovery seam."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import contextual_orchestrator.__main__ as entrypoint
from contextual_orchestrator.credentials import (
    InMemoryCredentialBackend,
    register_credential,
    set_backend,
)
from contextual_orchestrator.model_discovery import DiscoveredModel
from contextual_orchestrator.orchestrator import (
    ModelClient,
    TaskOrchestrator,
    load_agents,
)
from start import _configured_agents


def main() -> None:
    """Prove wrapper output expands into a same-origin concrete serving pool."""
    gateway_origin = "https://gateway.synthetic.example/v1"
    configured = _configured_agents(
        {"agents": [{"id": "configured_gateway_seed", "model": "", "tags": []}]},
        gateway_origin,
    )
    with TemporaryDirectory() as directory:
        agents_path = Path(directory) / "agents.json"
        agents_path.write_text(json.dumps(configured), encoding="utf-8")
        loaded = load_agents(str(agents_path))

    configured_model = DiscoveredModel(
        provider_name="configured_gateway",
        model_id="catalog-chat-model",
        credential_name="LLM_GATEWAY_API_KEY",
        chat_base_url=gateway_origin,
        auth_scheme="Bearer",
        capabilities=("chat",),
    )
    unrelated_models = [
        DiscoveredModel(
            provider_name="synthetic_provider",
            model_id=f"other-chat-model-{index}",
            credential_name="SYNTHETIC_PROVIDER_KEY",
            chat_base_url="https://other.synthetic.example/v1",
            auth_scheme="Bearer",
            capabilities=("chat",),
        )
        for index in range(20)
    ]
    catalog = [configured_model, *unrelated_models]
    set_backend(InMemoryCredentialBackend())
    register_credential("LLM_GATEWAY_API_KEY", "synthetic-secret")
    orchestrator = TaskOrchestrator(
        loaded,
        client=ModelClient(
            allowed_provider_hosts={
                "gateway.synthetic.example",
                "other.synthetic.example",
            }
        ),
    )
    original_discovery = entrypoint.discover_all_models
    entrypoint.discover_all_models = lambda _sources: (catalog, [])
    try:
        entrypoint._auto_discover_runtime_agents(orchestrator)
    finally:
        entrypoint.discover_all_models = original_discovery

    active_gateway = [
        agent
        for agent in orchestrator.agents
        if agent.provider_name == "configured_gateway"
    ]
    assert len(active_gateway) == 1
    assert active_gateway[0].model == "catalog-chat-model"
    assert all(agent.model for agent in orchestrator.agents)


if __name__ == "__main__":
    main()
