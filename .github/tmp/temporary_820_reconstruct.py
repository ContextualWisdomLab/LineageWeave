from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PARENT = "f37ca315e3c48fa37bbcafe96e46c5d7dab991b7"
TEST_PATH = Path("frontend/src/components/LeftoverMapPlot.test.tsx")
SOURCE_PATH = Path("frontend/src/components/LeftoverMapPlot.tsx")
ADR_PATH = Path("docs/adr/0289-leftover-map-plot-singular.md")
RUNTIME_PATH = Path("lineageweave/__init__.py")
BASELINE_PATH = Path("docs/product-technical-gap-baseline.md")
GOVERNANCE_TEST_PATH = Path("tests/test_adr_0289_governance.py")

PARENT_ONLY_TITLES = {
    "renders every distinct persisted tick when rounded labels match",
    "captions leftover-map axes with persisted leftover-map axis share",
    "keeps existing leftover-map axis text when share is missing or non-finite",
}
SHARE_ONLY_TITLES = {
    "captions leftover-map axes with persisted leftover-map axis share",
    "keeps existing leftover-map axis text when share is missing or non-finite",
}


def prepare() -> None:
    feature_text = TEST_PATH.read_text(encoding="utf-8")
    parent_text = subprocess.check_output(
        ["git", "show", f"{PARENT}:{TEST_PATH.as_posix()}"], text=True
    )
    title_pattern = re.compile(r'\n  it\("([^"]+)"')
    parent_titles = title_pattern.findall(parent_text)
    feature_titles = set(title_pattern.findall(feature_text))
    missing = set(parent_titles) - feature_titles
    if missing != PARENT_ONLY_TITLES:
        raise SystemExit(f"unexpected parent-only tests: {sorted(missing)!r}")

    blocks: list[str] = []
    for title in [item for item in parent_titles if item in PARENT_ONLY_TITLES]:
        marker = f'\n  it("{title}"'
        start = parent_text.index(marker)
        end = parent_text.find('\n  it("', start + len(marker))
        if end < 0:
            end = parent_text.rfind("\n});")
        if end < 0:
            raise SystemExit(f"could not delimit parent regression: {title}")
        block = parent_text[start:end]
        if title in SHARE_ONLY_TITLES:
            block = re.sub(
                r"leftover_singular_value: ([^,}\n]+)",
                "leftover_singular_value: Number.NaN",
                block,
            )
        blocks.append(block)

    insert_at = feature_text.rfind("\n});")
    if insert_at < 0:
        raise SystemExit("LeftoverMapPlot suite terminator missing")
    TEST_PATH.write_text(
        feature_text[:insert_at] + "".join(blocks) + feature_text[insert_at:],
        encoding="utf-8",
    )

    GOVERNANCE_TEST_PATH.write_text(
        '"""Governance regression for draft ADR 0289."""\n\n'
        "from pathlib import Path\n\n"
        'ADR_PATH = Path(__file__).parents[1] / "docs/adr/0289-leftover-map-plot-singular.md"\n\n'
        "def test_draft_adr_0289_remains_proposed() -> None:\n"
        '    """Keep the unmerged decision proposed until independent acceptance exists."""\n'
        '    text = ADR_PATH.read_text(encoding="utf-8")\n'
        '    assert "**Decision status:** Proposed" in text\n'
        '    assert "**Decision status:** Accepted" not in text\n',
        encoding="utf-8",
    )

    baseline = BASELINE_PATH.read_text(encoding="utf-8")
    title_line = "# Product & Technical Gap Baseline\n"
    if not baseline.startswith(title_line):
        raise SystemExit("gap baseline title missing")
    marker = "> #820 exact-current-parent reconstruction: persisted singular-value axis badges"
    if marker not in baseline:
        note = (
            "\n> #820 exact-current-parent reconstruction: persisted singular-value axis badges\n"
            "> are reconstructed from #819 `f37ca315e3c48fa37bbcafe96e46c5d7dab991b7`.\n"
            "> Preserve finite, non-negative persisted `σ_k`, including rank-0 `σ 0.00`; omit missing,\n"
            "> non-finite, or negative singular values independently of axis share. Parent share-only\n"
            "> regressions run with singular value unavailable so the contracts remain orthogonal.\n"
            "> ADR 0289 stays Proposed while Draft; package/frontend/runtime identity is 2.46.0.\n"
        )
        BASELINE_PATH.write_text(title_line + note + baseline[len(title_line) :], encoding="utf-8")


def fix() -> None:
    adr = ADR_PATH.read_text(encoding="utf-8")
    accepted = "**Decision status:** Accepted"
    if adr.count(accepted) != 1:
        raise SystemExit(f"expected one ADR0289 Accepted marker, found {adr.count(accepted)}")
    ADR_PATH.write_text(adr.replace(accepted, "**Decision status:** Proposed", 1), encoding="utf-8")

    runtime = RUNTIME_PATH.read_text(encoding="utf-8")
    runtime, count = re.subn(
        r'^__version__ = "[^"]+"$',
        '__version__ = "2.46.0"',
        runtime,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise SystemExit("runtime version declaration missing")
    RUNTIME_PATH.write_text(runtime, encoding="utf-8")

    source = SOURCE_PATH.read_text(encoding="utf-8")
    old = (
        '  if (singular === null && percent === null) {\n'
        '    return t(axisIndex === 1 ? "leftover-map axis 1" : "leftover-map axis 2");\n'
        '  }\n'
        '  if (singular === null) {\n'
        '    return tf(LEFTOVER_MAP_PLOT_AXIS_SHARE, { axis: axisIndex, share: percent });\n'
        '  }\n'
    )
    new = (
        '  if (singular === null) {\n'
        '    if (percent === null) {\n'
        '      return t(axisIndex === 1 ? "leftover-map axis 1" : "leftover-map axis 2");\n'
        '    }\n'
        '    return tf(LEFTOVER_MAP_PLOT_AXIS_SHARE, { axis: axisIndex, share: percent });\n'
        '  }\n'
    )
    if source.count(old) != 1:
        raise SystemExit("expected singular/share control-flow block was not unique")
    SOURCE_PATH.write_text(source.replace(old, new, 1), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "fix"}:
        raise SystemExit("usage: temporary_820_reconstruct.py prepare|fix")
    if sys.argv[1] == "prepare":
        prepare()
    else:
        fix()
