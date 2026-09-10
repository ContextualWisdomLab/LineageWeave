"""PRD requirement identifier and reference regression contract (issue #807)."""

import re
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_PRD = _ROOT / "docs" / "product-requirements.md"
_ADR_DIR = _ROOT / "docs" / "adr"
_TESTS_DIR = _ROOT / "tests"

_HEADING_RE = re.compile(r"^###\s+(PRD-[A-Z0-9]+(?:-[A-Z0-9]+)*)\s", re.MULTILINE)
_ADR_RE = re.compile(r"ADR (\d{4})")
_TEST_RE = re.compile(r"tests/(test_[A-Za-z0-9_]+\.py)")


def test_reference_patterns_reject_longer_token_prefixes() -> None:
    """Near-miss ADR numbers and backup filenames must not satisfy exact references."""
    assert _ADR_RE.findall("ADR 0256") == ["0256"]
    assert _ADR_RE.findall("ADR 02560") == []
    assert _TEST_RE.findall("tests/test_example.py") == ["test_example.py"]
    assert _TEST_RE.findall("tests/test_example.py.bak") == []


def test_prd_requirement_identifiers_are_unique() -> None:
    """Keep each PRD-FR-* identifier stable and singular (issue #807)."""
    counts: dict[str, int] = {}
    for ident in _HEADING_RE.findall(_PRD.read_text(encoding="utf-8")):
        counts[ident] = counts.get(ident, 0) + 1
    duplicated = sorted(name for name, count in counts.items() if count > 1)
    assert not duplicated, f"duplicated PRD identifiers: {duplicated}"


def test_prd_cited_adrs_exist() -> None:
    """Pin every ADR number the PRD cites to a file on this branch (issue #807)."""
    cited = sorted(set(_ADR_RE.findall(_PRD.read_text(encoding="utf-8"))))
    missing = [
        number for number in cited if not list(_ADR_DIR.glob(f"{number}-*.md"))
    ]
    assert not missing, f"PRD cites ADRs with no file: {missing}"


def test_prd_cited_tests_exist() -> None:
    """Pin every test file the PRD acceptance cites to tests/ (issue #807)."""
    cited = sorted(set(_TEST_RE.findall(_PRD.read_text(encoding="utf-8"))))
    missing = [name for name in cited if not (_TESTS_DIR / name).exists()]
    assert not missing, f"PRD cites missing tests: {missing}"
