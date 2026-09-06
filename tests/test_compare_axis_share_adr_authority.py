"""Governance contract for grouping-comparison axis-share ADR identity."""

from pathlib import Path


_ROOT = Path(__file__).parents[1]
_AXIS_ADR = _ROOT / "docs" / "adr" / "0368-leftover-map-compare-axis-share.md"
_COLLIDING_ADR = _ROOT / "docs" / "adr" / "0304-leftover-map-compare-axis-share.md"


def test_axis_share_uses_unclaimed_proposed_adr_identity() -> None:
    """Keep the axis-share decision distinct from sibling ADR 0304."""
    assert _AXIS_ADR.exists()
    assert not _COLLIDING_ADR.exists()

    text = _AXIS_ADR.read_text(encoding="utf-8")
    assert text.startswith("# ADR 0368")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text


def test_axis_share_owned_references_follow_adr_0368() -> None:
    """Do not leave branch-local axis-share authority split across ADR ids."""
    expected = {
        "docs/adr/0148-leftover-map-axis-share.md": "0368-leftover-map-compare-axis-share.md",
        "frontend/src/leftoverMapCompareAxis.ts": "ADR 0368",
        "frontend/src/components/LeftoverPairList.tsx": "ADR 0368",
        "frontend/src/leftoverMapPlotLayout.ts": "ADR 0368",
    }
    for relative_path, marker in expected.items():
        content = (_ROOT / relative_path).read_text(encoding="utf-8")
        assert marker in content, relative_path
