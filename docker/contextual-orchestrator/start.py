"""Bootstrap the local NIM credential, then start contextual-orchestrator.

The provider key is transport-only: it is registered in the orchestrator's
process-local credential store before the server starts and removed from the
process environment before request handling begins.
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path

_PROVIDER_CREDENTIAL_NAMES = (
    "BYTEZ_API_KEY",
    "NVIDIA_NIM_API_KEY",
    "NVIDIA_NIM_API_KEY_SUB",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
)


def _pop_first_env(*names: str) -> str:
    """Read the first configured alias without leaving credentials in the environment."""
    for name in names:
        value = os.environ.pop(name, "").strip()
        if value:
            return value
    return ""


def _pop_provider_credentials() -> dict[str, str]:
    """Move every configured provider key out of the process environment."""
    return {
        name: value
        for name in _PROVIDER_CREDENTIAL_NAMES
        if (value := os.environ.pop(name, "").strip())
    }


def main() -> None:
    """Register the provider credential and delegate to the upstream server."""
    provider_credentials = _pop_provider_credentials()
    gateway_key = _pop_first_env("LLM_GATEWAY_API_KEY", "LLM_API_KEY")
    provider_key = gateway_key or next(iter(provider_credentials.values()), "")
    if not provider_key:
        raise SystemExit("at least one supported provider credential is required to start the real LLM service")
    auth_token = os.environ.get("CONTEXTUAL_ORCHESTRATOR_TOKEN", "").strip()
    if not auth_token:
        raise SystemExit("CONTEXTUAL_ORCHESTRATOR_TOKEN is required to start the authenticated LLM service")

    provider_url = _pop_first_env("LLM_GATEWAY_API_URL", "LLM_GATEWAY_URL", "LLM_API_GATEWAY")
    if not provider_url:
        raise SystemExit("LLM_GATEWAY_API_URL or LLM_GATEWAY_URL is required to start the gateway")
    if not provider_url.rstrip("/").endswith("/v1"):
        provider_url = provider_url.rstrip("/") + "/v1"
    raw_limit = os.environ.pop("LLM_GATEWAY_MAX_OUTPUT_TOKENS", "4096").strip()
    try:
        max_output_tokens = int(raw_limit)
    except ValueError as exc:
        raise SystemExit("LLM_GATEWAY_MAX_OUTPUT_TOKENS must be an integer") from exc
    if not 64 <= max_output_tokens <= 4096:
        raise SystemExit("LLM_GATEWAY_MAX_OUTPUT_TOKENS must be between 64 and 4096")
    raw_body_limit = os.environ.pop("CONTEXTUAL_ORCHESTRATOR_MAX_BODY_BYTES", str(8 * 1024 * 1024)).strip()
    try:
        max_body_bytes = int(raw_body_limit)
    except ValueError as exc:
        raise SystemExit("CONTEXTUAL_ORCHESTRATOR_MAX_BODY_BYTES must be an integer") from exc
    if not 64 * 1024 <= max_body_bytes <= 64 * 1024 * 1024:
        raise SystemExit("CONTEXTUAL_ORCHESTRATOR_MAX_BODY_BYTES must be between 65536 and 67108864")
    agents_path = Path("/tmp/lineageweave-agents.json")
    agents = json.loads(Path("/app/agents.json").read_text(encoding="utf-8"))
    for agent in agents["agents"]:
        agent["base_url"] = provider_url
        agent["credential_key"] = "LLM_GATEWAY_API_KEY"
        agent.setdefault("provider_protocol", "auto")
    embedding_model = os.environ.get("LLM_GATEWAY_EMBEDDING_MODEL", "").strip()
    if embedding_model:
        embedding_agents = [
            agent
            for agent in agents["agents"]
            if "embedding" in agent.get("tags", [])
        ]
        if embedding_agents:
            for agent in embedding_agents:
                agent["model"] = embedding_model
        else:
            agents["agents"].append(
                {
                    "id": "llm_gateway_embedding_agent",
                    "model": embedding_model,
                    "base_url": provider_url,
                    "credential_key": "LLM_GATEWAY_API_KEY",
                    "provider_protocol": "auto",
                    "tags": ["embedding"],
                    "priority": 0,
                }
            )
    agents_path.write_text(json.dumps(agents), encoding="utf-8")

    from contextual_orchestrator.credentials import register_credential

    registered_names: set[str] = set()

    def register(name: str, value: str) -> None:
        if name not in registered_names:
            register_credential(name, value)
            registered_names.add(name)

    if gateway_key:
        register("NVIDIA_NIM_API_KEY", provider_credentials.get("NVIDIA_NIM_API_KEY", gateway_key))
        register("LLM_GATEWAY_API_KEY", gateway_key)
    else:
        register("LLM_GATEWAY_API_KEY", provider_key)
    for name, value in provider_credentials.items():
        register(name, value)
    del provider_key
    del gateway_key
    del provider_credentials
    del registered_names
    sys.argv = [
        "contextual_orchestrator",
        "--serve",
        "--agents",
        str(agents_path),
        "--auto-discover-model-agents",
        "--allow-discovery-failures",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--allow-public-bind",
        "--auth-token",
        auth_token,
        "--max-output-tokens",
        str(max_output_tokens),
        "--max-body-bytes",
        str(max_body_bytes),
    ]
    del provider_url
    del auth_token
    from contextual_orchestrator.__main__ import main as serve

    serve()


if __name__ == "__main__":
    main()
