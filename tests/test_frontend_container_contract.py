"""Frontend container dependency-install contract."""

from pathlib import Path


def test_docker_build_copies_pnpm_build_approval_before_install() -> None:
    """Fresh image installs see the checked-in esbuild approval policy."""
    root = Path(__file__).resolve().parents[1] / "frontend"
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    copy_index = dockerfile.index("COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./")
    install_index = dockerfile.index("RUN pnpm install --frozen-lockfile")
    assert copy_index < install_index
    assert "allowBuilds:\n  esbuild: true" in (
        root / "pnpm-workspace.yaml"
    ).read_text(encoding="utf-8")
