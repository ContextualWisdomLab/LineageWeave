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
