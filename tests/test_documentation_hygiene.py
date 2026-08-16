"""Permanent hygiene checks for committed architecture-decision records."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ADR_DIRECTORY = _ROOT / "docs" / "adr"
_ADR_NAME = re.compile(r"^(?P<number>[0-9]{4})-.+\.md$")
_FORBIDDEN_MARKERS = (
    "PLACEHOLDER_DO_NOT_WRITE",
    "TODO_WRITE_ADR",
)


def test_adr_numbers_are_unique_and_documents_are_not_placeholders() -> None:
    """Every committed ADR number identifies one substantive UTF-8 document."""
    paths = sorted(_ADR_DIRECTORY.glob("*.md"))
    assert paths, "the repository must contain architecture-decision records"

    numbered_paths: list[tuple[str, Path]] = []
    for path in paths:
        match = _ADR_NAME.fullmatch(path.name)
        assert match is not None, f"ADR filename is not numbered: {path.name}"
        numbered_paths.append((match.group("number"), path))

        content = path.read_text(encoding="utf-8")
        assert content.strip(), f"ADR is empty: {path.relative_to(_ROOT)}"
        for marker in _FORBIDDEN_MARKERS:
            assert marker not in content, (
                f"ADR contains forbidden placeholder {marker!r}: "
                f"{path.relative_to(_ROOT)}"
            )

    counts = Counter(number for number, _ in numbered_paths)
    duplicates = sorted(number for number, count in counts.items() if count > 1)
    assert duplicates == [], f"duplicate ADR numbers: {duplicates}"


def test_agents_md_locks_analysis_run_list_accname() -> None:
    """AGENTS.md is the policy home for the list accessible-name formula."""
    agents = (_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Open analysis run: {caption}. {nextAction}" in agents
    assert "does not claim a calibrated measurement" in agents
    assert "does not say reconstruction" in agents
