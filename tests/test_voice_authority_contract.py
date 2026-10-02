"""Voice composition supporting documents must name their governing ADRs."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_voice_combination_documents_reference_adr_0256_not_0251() -> None:
    """Keep Voice composition distinct from ADR 0251's I/O-Psychology layer."""
    requirements = (ROOT / "docs/voice-combination-technical-requirements.md").read_text()
    history = (ROOT / "docs/adr/0252-temporal-primary-voice-history.md").read_text()
    adr_index = (ROOT / "docs/adr/README.md").read_text()
    storybook_index = (ROOT / "docs/storybook-inventory.md").read_text()

    assert "projects ADR 0246, ADR 0256, and ADR 0252" in requirements
    assert "Extends ADR 0256" in history
    assert "ADR 0256 records when a Voice assignment starts" in history
    assert "[0256](0256-evidence-bearing-voice-combinations.md)" in adr_index
    assert "[0251](0256-evidence-bearing-voice-combinations.md)" not in adr_index
    ontology_row = next(
        line for line in storybook_index.splitlines() if "`Evidence/OntologyExplorer`" in line
    )
    assert "ADR 0184/0222/0256 states" in ontology_row
