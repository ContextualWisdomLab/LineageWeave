"""Regression for persisted cross-share transport on the comparison read model."""

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
                    (
                        ("closest", 0.12),
                        ("farthest", 0.0),
                        ("closest", -0.25),
                        ("farthest", None),
                        ("closest", float("nan")),
                        ("farthest", float("inf")),
                        ("closest", float("-inf")),
                    ),
                    start=1,
                )
            ]
        if "from report_leftover_map_coverage" in query or "from report_leftover_map_axis" in query:
            return []
        raise AssertionError(f"unexpected query: {query}")


def test_period_comparison_transports_persisted_cross_share(monkeypatch) -> None:
    """Preserve finite signed x values and normalize null or non-finite x to null."""

    async def _label(_conn: Any, _kind: str, _key: str) -> str:
        return "Process unit 1"

    monkeypatch.setattr(report_ingestion, "resolve_grouping_label", _label)
    connection = _ComparisonConnection()
    payload = asyncio.run(report_ingestion.fetch_period_comparison(connection, "2026-W02"))
    assert "lp.leftover_map_cross_share" in connection.leftover_query
    assert [pair["leftover_map_cross_share"] for pair in payload[0]["leftover_pairs"]] == [
        0.12,
        0.0,
        -0.25,
        None,
        None,
        None,
        None,
    ]
