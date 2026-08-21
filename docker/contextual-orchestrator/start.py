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


def _pop_first_env(*names: str) -> str:
    """Read the first alias, removing quotes preserved by Docker env files."""
    for name in names:
        value = os.environ.pop(name, "").strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value:
            return value
    return ""


def main() -> None:
    """Register the provider credential and delegate to the upstream server."""
    provider_key = _pop_first_env("LLM_GATEWAY_API_KEY", "LLM_API_KEY", "NVIDIA_NIM_API_KEY")
    if not provider_key:
        raise SystemExit("LLM_GATEWAY_API_KEY or LLM_API_KEY is required to start the real LLM service")
    auth_token = _pop_first_env("CONTEXTUAL_ORCHESTRATOR_TOKEN")
    if not auth_token:
        raise SystemExit("CONTEXTUAL_ORCHESTRATOR_TOKEN is required to start the authenticated LLM service")

    provider_url = _pop_first_env("LLM_GATEWAY_API_URL", "LLM_GATEWAY_URL", "LLM_API_GATEWAY")
    if not provider_url:
        raise SystemExit("LLM_GATEWAY_API_URL or LLM_GATEWAY_URL is required to start the gateway")
    if not provider_url.rstrip("/").endswith("/v1"):
        provider_url = provider_url.rstrip("/") + "/v1"
    raw_limit = _pop_first_env("LLM_GATEWAY_MAX_OUTPUT_TOKENS") or "4096"
    try:
        max_output_tokens = int(raw_limit)
    except ValueError as exc:
        raise SystemExit("LLM_GATEWAY_MAX_OUTPUT_TOKENS must be an integer") from exc
    if not 64 <= max_output_tokens <= 4096:
        raise SystemExit("LLM_GATEWAY_MAX_OUTPUT_TOKENS must be between 64 and 4096")
    raw_body_limit = _pop_first_env("CONTEXTUAL_ORCHESTRATOR_MAX_BODY_BYTES") or str(8 * 1024 * 1024)
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
    embedding_model = _pop_first_env("LLM_GATEWAY_EMBEDDING_MODEL")
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

    register_credential("NVIDIA_NIM_API_KEY", provider_key)
    register_credential("LLM_GATEWAY_API_KEY", provider_key)
    del provider_key
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
