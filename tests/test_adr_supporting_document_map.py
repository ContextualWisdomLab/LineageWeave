"""Regression tests for the ADR supporting-document authority map."""

from collections import Counter
from pathlib import Path
import re


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_ADR_INDEX = _REPOSITORY_ROOT / "docs" / "adr" / "README.md"
_SUPPORTING_DOCUMENT_ROW = re.compile(
    r"^\| \[`[^`]+`\]\((?P<target>[^)]+)\) \|"
)


def test_supporting_document_map_has_unique_document_targets() -> None:
    """Keep one normative ADR mapping row per supporting document target."""
    targets = [
        match.group("target")
        for line in _ADR_INDEX.read_text(encoding="utf-8").splitlines()
        if (match := _SUPPORTING_DOCUMENT_ROW.match(line)) is not None
    ]
    duplicate_targets = sorted(
        target for target, count in Counter(targets).items() if count > 1
    )

    assert duplicate_targets == [], (
        "docs/adr/README.md must map each supporting document exactly once; "
        f"duplicate targets: {duplicate_targets}"
    )
