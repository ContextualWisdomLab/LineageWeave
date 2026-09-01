"""Architecture fitness for the contextual-orchestrator ownership boundary.

LineageWeave is a consumer of contextual-orchestrator. Provider credentials,
provider endpoints, model-agent bootstrap, and provider discovery belong to the
orchestrator deployment and must never leak back into this repository's
production/runtime configuration.
"""

from __future__ import annotations

import ast
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN_PROVIDER_CONFIGURATION = {
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "NVIDIA_NIM_API_KEY",
    "NVIDIA_NIM_API_KEY_SUB",
    "BYTEZ_API_KEY",
    "LLM_GATEWAY_API_KEY",
    "LLM_GATEWAY_API_URL",
    "LLM_GATEWAY_URL",
    "LLM_API_GATEWAY",
    "LLM_API_KEY",
    "CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS",
}


def _python_runtime_paths() -> list[Path]:
    paths: list[Path] = []
    for root_name in ("backend", "lineageweave", "scripts"):
        root = _REPOSITORY_ROOT / root_name
        paths.extend(path for path in root.rglob("*.py") if "tests" not in path.parts)
    return sorted(paths)


def _string_literals(path: Path) -> set[str]:
    """Return exact string literals used by one Python runtime module."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_lineageweave_does_not_embed_an_orchestrator_runtime() -> None:
    """The provider/orchestration runtime is deployed by its canonical owner."""
    assert not (_REPOSITORY_ROOT / "docker" / "contextual-orchestrator").exists()


def test_runtime_python_does_not_accept_provider_boundary_configuration() -> None:
    """Consumer code accepts only the published orchestrator service contract."""
    violations: dict[str, list[str]] = {}
    for path in _python_runtime_paths():
        used = sorted(_FORBIDDEN_PROVIDER_CONFIGURATION & _string_literals(path))
        if used:
            violations[str(path.relative_to(_REPOSITORY_ROOT))] = used
    assert violations == {}


def test_lineageweave_environment_example_exposes_only_consumer_credentials() -> None:
    """The sample environment must not teach operators to configure providers here."""
    sample = (_REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")
    for name in _FORBIDDEN_PROVIDER_CONFIGURATION:
        assert f"{name}=" not in sample
    assert "ORCHESTRATOR_BASE_URL=" in sample
    assert "ORCHESTRATOR_API_KEY=" in sample


def test_compose_does_not_own_contextual_orchestrator_or_provider_config() -> None:
    """Compose consumes an external orchestrator instead of becoming its owner."""
    compose = (_REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "\n  orchestrator:\n" not in compose
    assert "condition: service_healthy\n      orchestrator:" not in compose
    assert "context: ./docker/contextual-orchestrator" not in compose
    for name in _FORBIDDEN_PROVIDER_CONFIGURATION:
        assert f"{name}:" not in compose
    assert "ORCHESTRATOR_BASE_URL: ${ORCHESTRATOR_BASE_URL:-}" in compose
    assert "ORCHESTRATOR_API_KEY: ${ORCHESTRATOR_API_KEY:-}" in compose
