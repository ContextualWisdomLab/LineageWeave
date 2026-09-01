"""Repository-owned Linux workflows use an explicit supported hosted image."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "tests.yml",
    ROOT / ".github" / "workflows" / "ontology-pages.yml",
    ROOT / ".github" / "workflows" / "prov-o-contract.yml",
)


def test_repository_workflows_pin_ubuntu_2404() -> None:
    """Reject floating Linux aliases after repeated pre-checkout queue starvation."""
    combined = "\n".join(path.read_text(encoding="utf-8") for path in WORKFLOWS)
    assert "runs-on: ubuntu-latest" not in combined
    assert combined.count("runs-on: ubuntu-24.04") == 5
