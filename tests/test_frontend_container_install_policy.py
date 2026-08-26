from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_container_copies_the_single_build_script_policy() -> None:
    """The image install layer must receive the fail-closed pnpm allowlist."""
    workspace = (ROOT / "frontend" / "pnpm-workspace.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    assert workspace == "allowBuilds:\n  esbuild: true\n"
    assert "COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./" in dockerfile
