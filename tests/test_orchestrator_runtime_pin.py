"""Keep the reviewed contextual-orchestrator archive pin and ADR synchronized."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR_COMMIT = "4c31c3549537ba4813fe25e2bf4efc3e5b56aa3f"


def test_orchestrator_runtime_pin_matches_adr() -> None:
    """The image and decision record must identify the same immutable commit."""
    dockerfile = (ROOT / "docker/contextual-orchestrator/Dockerfile").read_text(
        encoding="utf-8"
    )
    adr = (ROOT / "docs/adr/0083-orchestrator-runtime-commit-pin.md").read_text(
        encoding="utf-8"
    )

    assert f"contextual-orchestrator/archive/{ORCHESTRATOR_COMMIT}.tar.gz" in dockerfile
    assert f"commit `{ORCHESTRATOR_COMMIT}`" in adr
    upstream_pr = "ContextualWisdomLab/contextual-orchestrator#791"
    assert upstream_pr in dockerfile and upstream_pr in adr
