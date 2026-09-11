from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_COMPOSE = (_REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
_ENV_EXAMPLE = (_REPO_ROOT / ".env.example").read_text(encoding="utf-8")


def _service_block(name: str, next_name: str) -> str:
    """Return one top-level Compose service block for contract assertions."""
    start = _COMPOSE.index(f"  {name}:\n")
    end = _COMPOSE.index(f"  {next_name}:\n", start)
    return _COMPOSE[start:end]


def test_default_compose_keeps_llm_runtime_optional() -> None:
    """Match the documented clean-checkout default with fail-closed LLM absence."""
    assert "`docker compose up` succeeds from a clean checkout" in _ENV_EXAMPLE
    orchestrator = _service_block("orchestrator", "backend")
    backend = _service_block("backend", "mcp")
    mcp = _service_block("mcp", "frontend")

    assert 'profiles: ["llm"]' in orchestrator
    assert "ORCHESTRATOR_BASE_URL: ${ORCHESTRATOR_BASE_URL:-}" in backend
    assert "ORCHESTRATOR_API_KEY: ${ORCHESTRATOR_API_KEY:-}" in backend
    assert "condition: service_healthy\n      orchestrator:" not in backend
    assert "ORCHESTRATOR_BASE_URL: ${ORCHESTRATOR_BASE_URL:-}" in mcp
    assert "ORCHESTRATOR_API_KEY: ${ORCHESTRATOR_API_KEY:-}" in mcp
