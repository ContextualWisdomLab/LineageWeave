"""Bootstrap the local NIM credential, then start contextual-orchestrator.

The provider key is transport-only: it is registered in the orchestrator's
process-local credential store before the server starts and removed from the
process environment before request handling begins.
"""

from __future__ import annotations

import os
import sys
import json
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from provider_policy import is_local_mlx_provider


def _pop_first_env(*names: str) -> str:
    """Read the first configured alias without leaving credentials in the environment."""
    for name in names:
        value = os.environ.pop(name, "").strip()
        if value:
            return value
    return ""


def _discover_chat_model(provider_url: str, provider_key: str) -> str:
    """Select the first provider model that is usable for chat and Vision."""
    request = urllib.request.Request(
        provider_url.rstrip("/") + "/models",
        headers={"authorization": f"Bearer {provider_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15.0) as response:  # noqa: S310 - configured gateway
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise SystemExit("LLM gateway model discovery failed") from exc
    rows = payload.get("data") if isinstance(payload, dict) else None
    for row in rows if isinstance(rows, list) else []:
        model = row.get("id") if isinstance(row, dict) else None
        lowered = model.lower() if isinstance(model, str) else ""
        if model and not any(
            marker in lowered for marker in ("embedding", "moderation", "whisper", "tts", "dall-e")
        ):
            return model
    raise SystemExit("LLM gateway returned no chat-capable model")


def main() -> None:
    """Register the provider credential and delegate to the upstream server."""
    provider_key = _pop_first_env("LLM_GATEWAY_API_KEY", "LLM_API_KEY", "NVIDIA_NIM_API_KEY")
    if not provider_key:
        raise SystemExit("LLM_GATEWAY_API_KEY or LLM_API_KEY is required to start the real LLM service")
    auth_token = os.environ.get("CONTEXTUAL_ORCHESTRATOR_TOKEN", "").strip()
    if not auth_token:
        raise SystemExit("CONTEXTUAL_ORCHESTRATOR_TOKEN is required to start the authenticated LLM service")

    provider_url = _pop_first_env("LLM_GATEWAY_API_URL", "LLM_GATEWAY_URL", "LLM_API_GATEWAY")
    if not provider_url:
        provider_url = "https://integrate.api.nvidia.com/v1"
    if not provider_url.rstrip("/").endswith("/v1"):
        provider_url = provider_url.rstrip("/") + "/v1"
    discovered_chat_model = _discover_chat_model(provider_url, provider_key)
    embedding_provider_url = provider_url
    local_mlx = is_local_mlx_provider(provider_url)
    if local_mlx:
        parsed = urlparse(provider_url)
        provider_url = urlunparse(("local", parsed.netloc, parsed.path, "", "", ""))
    raw_limit = os.environ.pop("LLM_GATEWAY_MAX_OUTPUT_TOKENS", "4096").strip()
    try:
        max_output_tokens = int(raw_limit)
    except ValueError as exc:
        raise SystemExit("LLM_GATEWAY_MAX_OUTPUT_TOKENS must be an integer") from exc
    if not 64 <= max_output_tokens <= 4096:
        raise SystemExit("LLM_GATEWAY_MAX_OUTPUT_TOKENS must be between 64 and 4096")
    embedding_model = os.environ.pop("LLM_GATEWAY_EMBEDDING_MODEL", "").strip()

    agents_path = Path("/tmp/lineageweave-agents.json")
    agents = json.loads(Path("/app/agents.json").read_text(encoding="utf-8"))
    for agent in agents["agents"]:
        agent["base_url"] = provider_url
        if not str(agent.get("model", "")).strip():
            agent["model"] = discovered_chat_model
        agent["credential_key"] = "LLM_GATEWAY_API_KEY"
        if local_mlx:
            agent["local_credential_key"] = "LLM_GATEWAY_API_KEY"
        agent.setdefault("provider_protocol", "auto")
    agents_path.write_text(json.dumps(agents), encoding="utf-8")

    from contextual_orchestrator.credentials import register_credential

    register_credential("NVIDIA_NIM_API_KEY", provider_key)
    register_credential("LLM_GATEWAY_API_KEY", provider_key)
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
        "--max-output-tokens",
        str(max_output_tokens),
        "--embedding-provider-url",
        embedding_provider_url,
        "--embedding-model",
        embedding_model,
    ]
    if local_mlx:
        sys.argv.extend(["--chat-template-args", '{"enable_thinking":false}'])
    del auth_token
    from contextual_orchestrator.__main__ import main as serve

    serve()


if __name__ == "__main__":
    main()
