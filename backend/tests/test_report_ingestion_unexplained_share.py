"""Regression for persisted grouping-comparison unexplained-share transport."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from backend.app import report_ingestion


class _ComparisonConnection:
    """Minimal asyncpg-compatible read boundary for one comparison row."""

    async def fetch(self, query: str, *_args: object) -> list[dict[str, object]]:
        if "from report_period_score" in query:
            return [{"grouping_kind": "thread_group", "grouping_key": "synthetic-thread", "mean_theta": 0.1, "post_count": 2, "link_method": "synthetic"}]
        if "from report_member_score" in query:
            return []
        if "from report_leftover_pair" in query:
            assert "lp.leftover_map_unexplained_share" in query, "leftover_map_unexplained_share is absent from comparison SELECT"
            common = {
                "grouping_kind": "thread_group",
                "grouping_key": "synthetic-thread",
                "post_id": "00000000-0000-0000-0000-000000000001",
                "post_title": "Synthetic comparison post",
                "criterion_code": "synthetic_criterion",
                "leftover_distance": 0.5,
                "leftover_residual": 0.4,
                "leftover_map_reconstruction": Decimal("0.25"),
                "leftover_map_cross_share": None,
                "visibility_code": "public",
                "corporate_entity_id": "00000000-0000-0000-0000-000000000002",
                "has_real_source_context": False,
            }
            return [
                {**common, "pair_kind": "closest", "leftover_map_unexplained_share": Decimal("0.02")},
                {**common, "pair_kind": "farthest", "leftover_map_unexplained_share": None},
            ]
        if "from report_leftover_map_coverage" in query or "from report_leftover_map_axis" in query:
            return []
        raise AssertionError(f"unexpected comparison query: {query}")


def test_fetch_period_comparison_transports_persisted_unexplained_share() -> None:
    """Persisted finite values reach the read model while SQL NULL remains unknown."""
    payload = asyncio.run(report_ingestion.fetch_period_comparison(_ComparisonConnection(), "2026-W02"))  # type: ignore[arg-type]
    pairs = payload[0]["leftover_pairs"]
    assert pairs[0]["leftover_map_unexplained_share"] == 0.02
    assert pairs[1]["leftover_map_unexplained_share"] is None
