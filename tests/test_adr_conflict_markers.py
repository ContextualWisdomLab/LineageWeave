"""ADR files stay free of unresolved merge markers and wrong ordinal links."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = ROOT / "docs" / "adr"


def test_adr_files_do_not_keep_merge_conflict_markers() -> None:
    """A committed conflict marker is not an architecture decision."""
    offenders = [
        path.name
        for path in ADR_DIR.glob("*.md")
        if "<<<<<<<" in path.read_text(encoding="utf-8")
        or ">>>>>>>" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_voice_history_adr_is_not_relabeled_as_the_soc_hierarchy() -> None:
    """ADR 0252 is temporal primary Voice history, not a SOC expansion."""
    voice = (ADR_DIR / "0252-temporal-primary-voice-history.md").read_text(encoding="utf-8")
    occupational = (
        ADR_DIR / "0245-io-occupational-taxonomy-in-the-published-ontology.md"
    ).read_text(encoding="utf-8")
    assert "temporal" in voice.lower() or "Voice" in voice
    assert "0252-complete-2018-soc-hierarchy.md" not in occupational
    assert not (ADR_DIR / "0252-complete-2018-soc-hierarchy.md").exists()
