"""Static checks for the reproducible frontend container boundary."""

from pathlib import Path


def test_frontend_container_uses_pinned_pnpm_policy_and_keyverse_args() -> None:
    dockerfile = (
        Path(__file__).resolve().parents[1] / "frontend" / "Dockerfile"
    ).read_text(encoding="utf-8")

    assert "COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./" in dockerfile
    assert "ARG VITE_KEYVERSE_ISSUER" in dockerfile
    assert "ARG VITE_KEYVERSE_CLIENT_ID" in dockerfile
    assert "VITE_KEYCLOAK_ISSUER" not in dockerfile
