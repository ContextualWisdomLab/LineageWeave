"""Static contracts for frontend Compose build-time configuration."""

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


def test_compose_uses_the_canonical_project_name() -> None:
    """Directory names must not create duplicate production-like stacks."""
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert compose.startswith("name: lineageweave\n")


def test_compose_and_frontend_image_share_vite_build_arguments() -> None:
    """Compose overrides must reach the names Vite reads during its build."""
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    for variable in (
        "VITE_KEYVERSE_ISSUER",
        "VITE_KEYVERSE_CLIENT_ID",
        "VITE_BACKEND_BASE_URL",
    ):
        assert f"{variable}:" in compose
        assert f"ARG {variable}" in dockerfile
        assert f"{variable}=${{{variable}}}" in dockerfile


def test_compose_has_one_default_project_and_complete_service_boundary() -> None:
    """Default Compose runs share one name and expose every owned integration hop."""
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert compose.startswith("name: lineageweave\n")
    for service in (
        "postgres",
        "database_migration",
        "valkey",
        "searxng",
        "keycloak",
        "orchestrator",
        "backend",
        "frontend",
    ):
        assert f"  {service}:\n" in compose
    assert "TEPP_API_KEY: ${TEPP_API_KEY:-}" in compose
    assert "KEYVERSE_ISSUER: ${KEYVERSE_ISSUER:-}" in compose
    assert (
        "VITE_KEYVERSE_ISSUER: "
        "${KEYVERSE_ISSUER:-http://localhost:${KEYCLOAK_PORT:-18080}/realms/lineageweave-demo}"
    ) in compose
