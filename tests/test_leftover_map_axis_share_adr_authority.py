"""ADR authority regression for the grouping-comparison axis-share decision."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ADR_DIRECTORY = _ROOT / "docs" / "adr"


def test_axis_share_decision_uses_unclaimed_proposed_adr_0367() -> None:
    """Keep the parallel axis-share decision off reconstruction ADR 0293."""
    colliding = _ADR_DIRECTORY / "0293-leftover-map-compare-axis-share.md"
    canonical = _ADR_DIRECTORY / "0367-leftover-map-compare-axis-share.md"

    assert not colliding.exists(), "axis-share must not reuse reconstruction ADR 0293"
    assert canonical.exists(), "axis-share decision must move to unclaimed ADR 0367"

    content = canonical.read_text(encoding="utf-8")
    assert content.startswith("# ADR 0367 —")
    assert "**Decision status:** Proposed" in content
    assert "**Decision status:** Accepted" not in content
