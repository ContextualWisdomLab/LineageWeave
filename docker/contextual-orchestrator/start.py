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
from urllib.parse import urlparse

from embedding_compat import install_provider_embedding_support
from vision_compat import install_multimodal_chat_support


def _allow_local_mlx_provider() -> None:
    """Permit only the explicit Compose local-MLX HTTP endpoint.

    ponytail: exact host:port exception for local development; production
    providers retain contextual-orchestrator's HTTPS/public-address checks.
    """
    if os.environ.get("LINEAGEWEAVE_ALLOW_LOCAL_LLM_HTTP") != "1":
        return
    from contextual_orchestrator.credentials import get_credential
    from contextual_orchestrator.orchestrator import ModelClient

    upstream_validate = ModelClient._validate_provider

    def validate_provider(self, agent):
        parsed = urlparse(agent.base_url)
        if (
            parsed.scheme == "http"
            and parsed.hostname == "host.docker.internal"
            and parsed.port == 8080
        ):
            if get_credential(agent.credential_name) is None:
                raise RuntimeError(f"{agent.id} requires a resolvable KV credential")
            return
        upstream_validate(self, agent)

    ModelClient._validate_provider = validate_provider


def main() -> None:
    """Register the provider credential and delegate to the upstream server."""
    provider_key = os.environ.pop("LLM_GATEWAY_API_KEY", "").strip()
    if not provider_key:
        provider_key = os.environ.pop("NVIDIA_NIM_API_KEY", "").strip()
    if not provider_key:
        raise SystemExit("LLM_GATEWAY_API_KEY or NVIDIA_NIM_API_KEY is required to start the real LLM service")
    auth_token = os.environ.get("CONTEXTUAL_ORCHESTRATOR_TOKEN", "").strip()
    if not auth_token:
        raise SystemExit("CONTEXTUAL_ORCHESTRATOR_TOKEN is required to start the authenticated LLM service")

    provider_url = os.environ.pop("LLM_GATEWAY_URL", "").strip()
    if not provider_url:
        provider_url = "https://integrate.api.nvidia.com/v1"
    if not provider_url.rstrip("/").endswith("/v1"):
        provider_url = provider_url.rstrip("/") + "/v1"
    provider_model = os.environ.pop("LLM_GATEWAY_MODEL", "").strip()
    embedding_model = os.environ.pop("LLM_GATEWAY_EMBEDDING_MODEL", "").strip()

    agents_path = Path("/tmp/lineageweave-agents.json")
    agents = json.loads(Path("/app/agents.json").read_text(encoding="utf-8"))
    for agent in agents["agents"]:
        agent["base_url"] = provider_url
        agent["credential_key"] = "LLM_GATEWAY_API_KEY"
        if provider_model:
            agent["model"] = provider_model
    agents_path.write_text(json.dumps(agents), encoding="utf-8")

    from contextual_orchestrator.credentials import register_credential

    register_credential("NVIDIA_NIM_API_KEY", provider_key)
    register_credential("LLM_GATEWAY_API_KEY", provider_key)
    _allow_local_mlx_provider()
    install_provider_embedding_support(provider_url, embedding_model)
    install_multimodal_chat_support()
    del provider_url
    del provider_key
    sys.argv = [
        "contextual_orchestrator",
        "--serve",
        "--agents",
        str(agents_path),
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--allow-public-bind",
        "--auth-token",
        auth_token,
    ]
    del auth_token
    from contextual_orchestrator.__main__ import main as serve

    serve()


if __name__ == "__main__":
    main()
