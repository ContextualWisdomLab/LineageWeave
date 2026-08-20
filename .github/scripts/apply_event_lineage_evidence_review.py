#!/usr/bin/env python3
"""Apply the bounded RED then GREEN repair for Event Lineage evidence review."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    """Read one repository text file."""

    return (ROOT / relative_path).read_text(encoding="utf-8")


def _write(relative_path: str, content: str) -> None:
    """Write one repository text file with normalized UTF-8 content."""

    (ROOT / relative_path).write_text(content, encoding="utf-8")


def _replace_once(relative_path: str, old: str, new: str) -> None:
    """Replace one exact source fragment and fail if the parent moved."""

    content = _read(relative_path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(
            f"expected exactly one replacement in {relative_path}, found {count}"
        )
    _write(relative_path, content.replace(old, new, 1))


def _append_once(relative_path: str, marker: str, addition: str) -> None:
    """Append one test block exactly once."""

    content = _read(relative_path)
    if marker in content:
        raise RuntimeError(f"test marker already exists in {relative_path}: {marker}")
    _write(relative_path, content.rstrip() + "\n\n" + addition.strip() + "\n")


def apply_red() -> None:
    """Add regressions for replay, stored edge direction, and locale completeness."""

    _append_once(
        "tests/test_migration_replay.py",
        "test_migrate_sh_replays_lineage_edge_channel_evidence_migration",
        '''

def test_migrate_sh_replays_lineage_edge_channel_evidence_migration() -> None:
    """Existing volumes must receive normalized Event Lineage channel evidence."""
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "0052_*" in script
''',
    )

    _append_once(
        "frontend/src/LineageDag.test.tsx",
        "describes the child as following the stored parent",
        '''

describe("LineageDag edge direction and locale", () => {
  it("describes the child as following the stored parent", () => {
    const { container } = render(
      <LineageDag graph={graph} onSelectPost={vi.fn()} />,
    );

    expect(
      container.querySelector(".lineage-dag-edge title")?.textContent,
    ).toMatch(/^Follow-up event follows Initial event /);
  });

  it("localizes the parent-to-child relation instead of falling back to English", () => {
    setLocale("ko");
    const { container } = render(
      <LineageDag graph={graph} onSelectPost={vi.fn()} />,
    );

    const edgeTitle = container.querySelector(".lineage-dag-edge title")?.textContent;
    expect(edgeTitle).toContain(
      "Follow-up event은(는) Initial event 이후의 기록입니다",
    );
    expect(edgeTitle).not.toContain("Initial event follows Follow-up event");
  });
});
''',
    )


def apply_green() -> None:
    """Apply the minimum production changes that satisfy the RED contracts."""

    _replace_once(
        "docker/postgres-init/migrate.sh",
        "        0051_*) ;;",
        "        0051_*|0052_*) ;;",
    )

    _replace_once(
        "frontend/src/lineageEvidenceI18n.ts",
        '  "notAvailable",\n] as const;',
        '  "notAvailable",\n  "edgeDescription",\n] as const;',
    )
    _replace_once(
        "frontend/src/lineageEvidenceI18n.ts",
        '  notAvailable: "Not available",\n};',
        '  notAvailable: "Not available",\n  edgeDescription: "{child} follows {parent} ({score})",\n};',
    )
    _replace_once(
        "frontend/src/lineageEvidenceI18n.ts",
        '    notAvailable: "사용할 수 없음",\n  },',
        '    notAvailable: "사용할 수 없음",\n    edgeDescription: "{child}은(는) {parent} 이후의 기록입니다 ({score})",\n  },',
    )
    _replace_once(
        "frontend/src/lineageEvidenceI18n.ts",
        '    notAvailable: "不可用",\n  },',
        '    notAvailable: "不可用",\n    edgeDescription: "{child} 接续 {parent}（{score}）",\n  },',
    )
    _replace_once(
        "frontend/src/lineageEvidenceI18n.ts",
        '    notAvailable: "利用不可",\n  },',
        '    notAvailable: "利用不可",\n    edgeDescription: "{child} は {parent} に続く記録です（{score}）",\n  },',
    )
    _replace_once(
        "frontend/src/lineageEvidenceI18n.ts",
        '    notAvailable: "Không khả dụng",\n  },',
        '    notAvailable: "Không khả dụng",\n    edgeDescription: "{child} tiếp nối {parent} ({score})",\n  },',
    )
    _append_once(
        "frontend/src/lineageEvidenceI18n.ts",
        "export function lineageEvidenceEdgeDescription",
        '''

/** Format one stored parent-to-child edge without treating labels as templates. */
export function lineageEvidenceEdgeDescription(
  child: string,
  parent: string,
  score: string,
  locale: Locale = getLocale(),
): string {
  const values = { child, parent, score };
  return TRANSLATIONS[locale].edgeDescription.replace(
    /\\{(child|parent|score)\\}/g,
    (_placeholder, key: string) => values[key as keyof typeof values],
  );
}
''',
    )

    _replace_once(
        "frontend/src/LineageDag.tsx",
        'import { lineageEvidenceText } from "./lineageEvidenceI18n";',
        '''import {
  lineageEvidenceEdgeDescription,
  lineageEvidenceText,
} from "./lineageEvidenceI18n";''',
    )
    _replace_once(
        "frontend/src/LineageDag.tsx",
        '''  return tf("{from} follows {to} ({score})", {
    from: from.label,
    to: to.label,
    score: parts.join("; "),
  });''',
        '''  return lineageEvidenceEdgeDescription(
    to.label,
    from.label,
    parts.join("; "),
  );''',
    )


def main() -> int:
    """Apply exactly one requested phase."""

    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("red", "green"))
    args = parser.parse_args()
    if args.phase == "red":
        apply_red()
    else:
        apply_green()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
