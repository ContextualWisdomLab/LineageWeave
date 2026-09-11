from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_COMPOSE = (_REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
_ENV_EXAMPLE = (_REPO_ROOT / ".env.example").read_text(encoding="utf-8")


def _service_block(name: str, next_name: str) -> str:
    """Return one top-level Compose service block for contract assertions."""
    start = _COMPOSE.index(f"  {name}:\n")
    end = _COMPOSE.index(f"  {next_name}:\n", start)
    return _COMPOSE[start:end]


def _depends_on_block(service: str) -> str:
    """Return only dependency declarations, excluding environment references."""
    return service.split("    depends_on:\n", maxsplit=1)[1]


def test_default_compose_keeps_llm_runtime_optional() -> None:
    """Match the documented clean-checkout default with fail-closed LLM absence."""
    assert "`docker compose up` succeeds from a clean checkout" in _ENV_EXAMPLE
    orchestrator = _service_block("orchestrator", "backend")
    backend = _service_block("backend", "mcp")
    mcp = _service_block("mcp", "frontend")

    assert 'profiles: ["llm"]' in orchestrator
    assert "ORCHESTRATOR_BASE_URL: ${ORCHESTRATOR_BASE_URL:-}" in backend
    assert "ORCHESTRATOR_API_KEY: ${ORCHESTRATOR_API_KEY:-}" in backend
    assert "      orchestrator:\n" not in _depends_on_block(backend)
    assert "ORCHESTRATOR_BASE_URL: ${ORCHESTRATOR_BASE_URL:-}" in mcp
    assert "ORCHESTRATOR_API_KEY: ${ORCHESTRATOR_API_KEY:-}" in mcp
    assert "      orchestrator:\n" not in _depends_on_block(mcp)


def test_keycloak_pins_issuer_to_public_url() -> None:
    """Keycloak's ``iss`` must not depend on which host calls it.

    Keycloak 26 hostname v2 derives the issuer from the request host. A bare
    ``localhost`` therefore makes the in-network ``keycloak:8080`` call that
    seeds demo content mint an issuer the backend (``KEYCLOAK_ISSUER`` on the
    public URL) rejects with 401. A full public URL keeps one issuer for every
    caller, in-network or browser.
    """
    keycloak = _service_block("keycloak", "orchestrator")
    assert "KC_HOSTNAME: http://localhost:${KEYCLOAK_PORT:-18080}" in keycloak
    assert "KC_HOSTNAME: localhost\n" not in keycloak
