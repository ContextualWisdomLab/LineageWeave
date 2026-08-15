"""Exercise the product Compose preflight without exposing configuration values."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_fake_docker(tmp_path: Path, configuration: dict) -> None:
    """Make the preflight consume one deterministic resolved Compose payload."""
    docker = tmp_path / "docker"
    docker.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ \"$*\" != \"compose --profile product config --format json\" ]]; then\n"
        "  exit 64\n"
        "fi\n"
        "cat <<'JSON'\n"
        + json.dumps(configuration)
        + "\nJSON\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)


def _run_preflight(tmp_path: Path, configuration: dict) -> subprocess.CompletedProcess[str]:
    """Run the actual shell preflight with a fake secret-free Compose result."""
    _write_fake_docker(tmp_path, configuration)
    environment = os.environ | {"PATH": f"{tmp_path}:{os.environ['PATH']}"}
    return subprocess.run(
        ["bash", "scripts/preflight_product_compose.sh"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        env=environment,
    )


def _product_configuration(**environment: str) -> dict:
    """Return the smallest resolved product shape the preflight accepts."""
    return {"services": {"lineageweave": {"environment": environment}}}


def test_preflight_accepts_resolved_direct_database_and_oidc_settings(tmp_path: Path) -> None:
    """Preflight succeeds when all required values are non-empty without printing them."""
    result = _run_preflight(
        tmp_path,
        _product_configuration(
            LINEAGEWEAVE_DSN="postgresql://fixture",
            LINEAGE_SOURCE_TABLE="schema.table",
            KEYVERSE_ISSUER="https://identity.example/realm",
            LINEAGEWEAVE_OIDC_CLIENT_ID="product-client",
            LINEAGEWEAVE_OIDC_CLIENT_SECRET="fixture-secret",
            LINEAGEWEAVE_OIDC_REDIRECT_URI="https://product.example/api/oidc/callback",
        ),
    )
    assert result.returncode == 0
    assert "preflight-product-compose-ok" in result.stdout
    assert "fixture-secret" not in result.stdout + result.stderr


def test_preflight_rejects_missing_required_settings_without_value_disclosure(tmp_path: Path) -> None:
    """Preflight names only missing keys before product startup can fail later."""
    result = _run_preflight(
        tmp_path,
        _product_configuration(
            LINEAGEWEAVE_DSN="postgresql://fixture",
            LINEAGE_SOURCE_TABLE="schema.table",
            KEYVERSE_ISSUER="https://identity.example/realm",
            LINEAGEWEAVE_OIDC_CLIENT_ID="product-client",
            LINEAGEWEAVE_OIDC_CLIENT_SECRET="",
            LINEAGEWEAVE_OIDC_REDIRECT_URI="https://product.example/api/oidc/callback",
        ),
    )
    assert result.returncode == 1
    assert "LINEAGEWEAVE_OIDC_CLIENT_SECRET" in result.stderr
    assert "postgresql://fixture" not in result.stdout + result.stderr


def test_container_images_pin_base_digests_and_run_non_root() -> None:
    """Keep shipped and conformance images reproducible and non-root at runtime."""
    expected_images = {
        "Dockerfile": (
            "node:24.18.0-alpine@sha256:a0b9bf06e4e6193cf7a0f58816cc935ff8c2a908f81e6f1a95432d679c54fbfd",
            "ghcr.io/astral-sh/uv:0.9.27-python3.13-bookworm-slim@sha256:fb12b20e86027dac1b4c78a359ba091b639df39b85d9e9f5d93a91bd08e01666",
            "USER node",
            "USER lineageweave",
        ),
        "compose/Dockerfile": (
            "python:3.13-alpine@sha256:540c7d91f98ff6880174c40e99067bf5941eb54d818a7a5e094d188b196a934d",
            "USER lineageweave",
        ),
        "compose/searxng/Dockerfile": (
            "searxng/searxng@sha256:c2dc2d9e6b910653e8628361c23443222490e4cabbb9e02667b7847143db843b",
            "USER searxng",
        ),
        "tests/Dockerfile.oidc-conformance": (
            "quay.io/keycloak/keycloak:26.0.8@sha256:09a381c715ab0b111835b70f2905955274843a219c6f27efb348e4d9f4086858",
            "USER 1000",
        ),
    }
    for relative_path, markers in expected_images.items():
        source = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert all(marker in source for marker in markers), relative_path
