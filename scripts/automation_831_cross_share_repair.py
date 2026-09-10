"""One-shot #831 source repair; removed by its owning workflow after GREEN."""

from __future__ import annotations

from pathlib import Path
import re


def require_once(text: str, needle: str, label: str) -> None:
    count = text.count(needle)
    if count != 1:
        raise SystemExit(f"{label} count={count}")


def write_backend_regression() -> None:
    path = Path("backend/tests/test_period_comparison_cross_share.py")
    path.write_text(
        '''"""Regression for persisted cross-share transport on the comparison read model."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app import report_ingestion


class _ComparisonConnection:
    """Minimal asyncpg-shaped fixture for one comparison grouping."""

    def __init__(self) -> None:
        self.leftover_query = ""

    async def fetch(self, query: str, *_args: Any) -> list[dict[str, Any]]:
        if "from report_period_score" in query:
            return [{"grouping_kind": "process_unit", "grouping_key": "PU-1", "mean_theta": 0.25, "post_count": 4, "link_method": "fixture"}]
        if "from report_member_score" in query:
            return []
        if "from report_leftover_pair" in query:
            self.leftover_query = query
            return [
                {
                    "grouping_kind": "process_unit",
                    "grouping_key": "PU-1",
                    "pair_kind": pair_kind,
                    "post_id": f"post-{index}",
                    "criterion_code": "criterion-a",
                    "leftover_distance": 1.0,
                    "leftover_residual": -0.5,
                    "leftover_map_reconstruction": None,
                    "leftover_map_unexplained_share": None,
                    "leftover_map_cross_share": cross_share,
                    "post_title": f"Post {index}",
                    "visibility_code": "public",
                    "corporate_entity_id": f"entity-{index}",
                    "has_real_source_context": True,
                }
                for index, (pair_kind, cross_share) in enumerate(
                    (("closest", 0.12), ("farthest", 0.0), ("closest", -0.25), ("farthest", None)),
                    start=1,
                )
            ]
        if "from report_leftover_map_coverage" in query or "from report_leftover_map_axis" in query:
            return []
        raise AssertionError(f"unexpected query: {query}")


def test_period_comparison_transports_persisted_cross_share(monkeypatch) -> None:
    """Finite signed, zero, and null x values survive the persisted pair boundary."""

    async def _label(_conn: Any, _kind: str, _key: str) -> str:
        return "Process unit 1"

    monkeypatch.setattr(report_ingestion, "resolve_grouping_label", _label)
    connection = _ComparisonConnection()
    payload = asyncio.run(report_ingestion.fetch_period_comparison(connection, "2026-W02"))
    assert "lp.leftover_map_cross_share" in connection.leftover_query
    assert [pair["leftover_map_cross_share"] for pair in payload[0]["leftover_pairs"]] == [0.12, 0.0, -0.25, None]
''',
        encoding="utf-8",
    )


def repair_frontend() -> None:
    path = Path("frontend/src/App.tsx")
    app = path.read_text(encoding="utf-8")

    import_anchor = '''import {
  formatLeftoverMapUnexplainedShare,
  LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL,
} from "./leftoverMapUnexplainedShare";
import {
  leftoverMapCompareAxisShare,'''
    import_value = '''import {
  formatLeftoverMapUnexplainedShare,
  LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL,
} from "./leftoverMapUnexplainedShare";
import { formatLeftoverMapCrossShare } from "./leftoverMapCrossShare";
import {
  leftoverMapCompareAxisShare,'''
    require_once(app, import_anchor, "frontend import anchor")
    app = app.replace(import_anchor, import_value, 1)

    declaration = re.compile(
        r'(\s+const unexplainedShare = formatLeftoverMapUnexplainedShare\(\n'
        r'\s+pair\.leftover_map_unexplained_share,\n'
        r'\s+\);\n)'
        r'(\s+const pairAccessibleName = )'
    )
    app, count = declaration.subn(
        r'\1                    const crossShare = formatLeftoverMapCrossShare(\n'
        r'                      pair.leftover_map_cross_share,\n'
        r'                    );\n\2',
        app,
        count=1,
    )
    if count != 1:
        raise SystemExit(f"frontend declaration anchor count={count}")

    accessible = re.compile(
        r'(?P<u>\$\{\n\s+unexplainedShare\n\s+\? ` · \$\{t\(LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL\)\} \$\{unexplainedShare\}`\n\s+: ""\n\s+\})(?P<end>`;)'
    )
    app, count = accessible.subn(
        r'\g<u>${crossShare ? ` · ${crossShare}` : ""}\g<end>', app, count=1
    )
    if count != 1:
        raise SystemExit(f"frontend accessible-name anchor count={count}")

    pair_start = app.index("const pairAccessibleName =")
    prefix, tail = app[:pair_start], app[pair_start:]
    badge = re.compile(
        r'(?P<u>\s+\{unexplainedShare \? \(\n'
        r'\s+<span className="post-badge" aria-hidden="true">\n'
        r'\s+\{unexplainedShare\}\n'
        r'\s+</span>\n'
        r'\s+\) : null\}\n)'
        r'(?P<close>\s+</button>)'
    )
    tail, count = badge.subn(
        r'\g<u>                          {crossShare ? (\n'
        r'                            <span className="post-badge" aria-hidden="true">\n'
        r'                              {crossShare}\n'
        r'                            </span>\n'
        r'                          ) : null}\n\g<close>',
        tail,
        count=1,
    )
    if count != 1:
        raise SystemExit(f"frontend badge anchor count={count}")
    app = prefix + tail
    if "LEFTOVER_MAP_COMPARE_CROSS_SHARE_LABEL" in app:
        raise SystemExit("forbidden static comparison cross-share label authority")
    path.write_text(app, encoding="utf-8")


def repair_backend() -> None:
    path = Path("backend/app/report_ingestion.py")
    backend = path.read_text(encoding="utf-8")

    query_anchor = "lp.leftover_map_reconstruction, lp.leftover_map_unexplained_share,\n"
    require_once(backend, query_anchor, "backend select anchor")
    backend = backend.replace(
        query_anchor,
        query_anchor + "               lp.leftover_map_cross_share,\n",
        1,
    )

    payload_anchor = '''                        "leftover_map_unexplained_share": (
                            None
                            if pair["leftover_map_unexplained_share"] is None
                            else float(pair["leftover_map_unexplained_share"])
                        ),
'''
    require_once(backend, payload_anchor, "backend payload anchor")
    payload_value = payload_anchor + '''                        "leftover_map_cross_share": (
                            None
                            if pair["leftover_map_cross_share"] is None
                            else float(pair["leftover_map_cross_share"])
                        ),
'''
    path.write_text(backend.replace(payload_anchor, payload_value, 1), encoding="utf-8")


if __name__ == "__main__":
    write_backend_regression()
    repair_frontend()
    repair_backend()
