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


def test_make_seed_installs_the_script_runtime_extras() -> None:
    """Keep the documented synthetic seed command executable in a fresh checkout."""
    makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(
        encoding="utf-8"
    )

    assert (
        "uv run --locked --extra dev --extra backend python scripts/seed_demo_data.py"
        in makefile
    )
