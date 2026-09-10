"""Regression contract for grouping-comparison cross-share evidence composition."""

from pathlib import Path
import re


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = REPOSITORY_ROOT / "frontend" / "src" / "App.tsx"
FORMATTER_SOURCE = REPOSITORY_ROOT / "frontend" / "src" / "leftoverMapCrossShare.ts"


def test_grouping_comparison_projects_persisted_cross_share_into_one_accessible_action() -> None:
    """Require comparison pairs to expose persisted x without duplicate announcements."""

    source = APP_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r"const\s+crossShare\s*=\s*formatLeftoverMapCrossShare\(\s*"
        r"pair\.leftover_map_cross_share\s*,?\s*\)",
        source,
    ), "Grouping comparison must format the persisted pair.leftover_map_cross_share value."
    assert re.search(
        r"const\s+pairAccessibleName\s*=.*?crossShare\s*\?\s*`\s*·\s*\$\{crossShare\}`\s*:\s*\"\".*?;",
        source,
        re.DOTALL,
    ), "The actionable pair name must include formatted cross-share evidence when present."
    assert re.search(
        r"\{crossShare\s*\?\s*\(\s*<span\s+className=\"post-badge\"\s+aria-hidden=\"true\">\s*"
        r"\{crossShare\}\s*</span>\s*\)\s*:\s*null\}",
        source,
        re.DOTALL,
    ), "The visual duplicate must stay visible but hidden from duplicate assistive announcement."
    assert "LEFTOVER_MAP_COMPARE_CROSS_SHARE_LABEL" not in source, (
        "Do not recreate an inline/static comparison-label authority; the persisted formatted evidence "
        "belongs in the existing actionable name while screen copy remains on the versioned ledger path."
    )


def test_cross_share_formatter_remains_fail_closed_and_unclamped() -> None:
    """Preserve missing/non-finite omission and finite signed evidence semantics."""

    source = FORMATTER_SOURCE.read_text(encoding="utf-8")

    assert "value == null || !Number.isFinite(value)" in source
    assert "return null" in source
    assert "value.toFixed(2)" in source
    assert "Math.max" not in source
    assert "Math.min" not in source
    assert "Math.abs" not in source
