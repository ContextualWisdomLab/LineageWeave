"""Bootstrap the configured gateway credential, then start contextual-orchestrator.

The provider key is transport-only: it is registered in the orchestrator's
process-local credential store before the server starts and removed from Python's
os.environ before request handling begins. This prevents application runtime env
lookups and inheritance by subsequently spawned children, not secret erasure:
the initial process environment (including Linux /proc) and Docker container configuration
may still retain bootstrap values. The host user, Docker daemon and process-memory
inspection remain trusted. Registry and bootstrap locals necessarily hold keys.
Never print keys, put them on argv, or claim env deletion defeats these readers.
"""

from __future__ import annotations

import os
import sys
import json
import secrets
from pathlib import Path


def _pop_first_env(*names: str) -> str:
    """Consume aliases from Python's environment; not kernel/config erasure."""
    first = ""
    for name in names:
        value = os.environ.pop(name, "").strip()
        if value and not first:
            first = value
    return first


def main() -> None:
    """Register the provider credential and delegate to the upstream server."""
    gateway_key = _pop_first_env("LLM_GATEWAY_API_KEY", "LLM_API_KEY")
    provider_credentials = {
        name: value
        for name in (
            "OPENAI_API_KEY",
            "OPENROUTER_API_KEY",
            "NVIDIA_NIM_API_KEY",
            "NVIDIA_NIM_API_KEY_SUB",
            "BYTEZ_API_KEY",
        )
        if (value := os.environ.pop(name, "").strip())
    }
    if not gateway_key:
        raise SystemExit("LLM_GATEWAY_API_KEY or LLM_API_KEY is required to start the real LLM service")
    auth_token = os.environ.pop("CONTEXTUAL_ORCHESTRATOR_TOKEN", "").strip()
    if not auth_token:
        raise SystemExit("CONTEXTUAL_ORCHESTRATOR_TOKEN is required to start the authenticated LLM service")
    if auth_token == "lineageweave-orchestrator-dev-only":
        raise SystemExit("CONTEXTUAL_ORCHESTRATOR_TOKEN must be a private nondefault credential")

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
        agent["provider_name"] = "configured_gateway"
        agent.setdefault("provider_protocol", "auto")
    allowed_hosts = [
        host.strip() for host in os.environ.pop(
            "CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS", ""
        ).split(",") if host.strip()
    ]
    if not allowed_hosts:
        raise SystemExit("CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS is required")
    os.environ.pop("LLM_GATEWAY_EMBEDDING_MODEL", None)
    agents_path.write_text(json.dumps(agents), encoding="utf-8")

    from contextual_orchestrator.credentials import register_credential

    register_credential("LLM_GATEWAY_API_KEY", gateway_key)
    for credential_name, credential_value in provider_credentials.items():
        register_credential(credential_name, credential_value)
    register_credential("CONTEXTUAL_ORCHESTRATOR_INFERENCE_TOKEN", auth_token)
    register_credential("CONTEXTUAL_ORCHESTRATOR_ADMIN_TOKEN", secrets.token_urlsafe(48))
    del gateway_key
    del provider_credentials
    sys.argv = [
        "contextual_orchestrator",
        "--serve",
        "--agents",
        str(agents_path),
        "--auto-discover-model-agents",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--allow-public-bind",
        "--inference-token-key",
        "CONTEXTUAL_ORCHESTRATOR_INFERENCE_TOKEN",
        "--admin-token-key",
        "CONTEXTUAL_ORCHESTRATOR_ADMIN_TOKEN",
        "--max-output-tokens",
        str(max_output_tokens),
        "--max-body-bytes",
        str(max_body_bytes),
    ]
    for host in allowed_hosts:
        sys.argv.extend(["--allowed-provider-host", host])
    del provider_url
    del auth_token
    from contextual_orchestrator.__main__ import main as serve

    serve()


if __name__ == "__main__":
    main()
