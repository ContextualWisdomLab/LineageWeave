"""Provider URL policy shared by the orchestrator bootstrap and its tests."""

from __future__ import annotations

from urllib.parse import urlparse


def is_local_mlx_provider(provider_url: str) -> bool:
    """True only for the explicitly permitted Compose MLX endpoint."""
    parsed = urlparse(provider_url)
    return (
        parsed.scheme == "http"
        and parsed.hostname == "host.docker.internal"
        and parsed.port == 8080
    )
