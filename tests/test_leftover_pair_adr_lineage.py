"""Keep LeftoverPairList decision history aligned with accepted amendments."""

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_ADR_0049 = _ROOT / "docs" / "adr" / "0049-leftover-pair-report-ui.md"


def test_leftover_pair_report_retains_segment_amendment_lineage() -> None:
    """Accepted segment amendments remain visible in ADR 0049's live contract."""
    content = _ADR_0049.read_text(encoding="utf-8")
    amendment_section, remainder = content.split("## Context", maxsplit=1)
    decision_section = remainder.split("## Decision", maxsplit=1)[1].split(
        "## Consequences", maxsplit=1
    )[0]

    expected = tuple(f"[ADR {number:04d}]" for number in range(272, 281))
    missing_amendments = [reference for reference in expected if reference not in amendment_section]
    missing_decision_links = [reference for reference in expected if reference not in decision_section]

    assert missing_amendments == [], (
        "ADR 0049 dropped accepted pair-segment amendments: "
        f"{missing_amendments}"
    )
    assert missing_decision_links == [], (
        "ADR 0049 no longer traces live pair-segment behavior to: "
        f"{missing_decision_links}"
    )
