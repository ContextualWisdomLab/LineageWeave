"""Regression for primary report cross-share JSON safety."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal

from backend.app import report_ingestion


class _PrimaryReportConnection:
    """Minimal asyncpg-compatible boundary for one persisted report pair."""

    def __init__(self, cross_share: Decimal | None) -> None:
        self.cross_share = cross_share

    async def fetch(self, query: str, *_args: object) -> list[dict[str, object]]:
        if "from report_period_score" in query:
            return [
                {
                    "grouping_kind": "thread_group",
                    "grouping_key": "synthetic-thread",
                    "period_code": "2026-W02",
                    "rubric_version": report_ingestion.RUBRIC_VERSION,
                    "selected_model": "rasch",
                    "mean_theta": 0.1,
                    "mean_theta_sd": 0.2,
                    "post_count": 2,
                    "item_count": 1,
                    "fit_loglik": -1.0,
                    "fit_converged": True,
                    "calibration_score": 0.9,
                    "computed_at": datetime(2026, 1, 5, tzinfo=timezone.utc),
                    "link_method": "synthetic",
                    "anchor_period_code": None,
                    "delta_mean_theta": None,
                }
            ]
        if "from report_member_score" in query:
            return []
        if "from report_item_information" in query:
            return []
        if "from report_leftover_pair" in query:
            assert "lp.leftover_map_cross_share" in query
            return [
                {
                    "grouping_key": "synthetic-thread",
                    "pair_kind": "closest",
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "post_title": "Synthetic report post",
                    "criterion_code": "synthetic_criterion",
                    "leftover_distance": 0.5,
                    "leftover_residual": 0.4,
                    "observed_response": None,
                    "expected_response": None,
                    "leftover_map_rank": None,
                    "leftover_map_unexplained": None,
                    "leftover_map_cross_share": self.cross_share,
                    "leftover_map_reconstruction": None,
                    "leftover_map_unexplained_share": None,
                    "leftover_map_explained_share": None,
                    "leftover_map_person_axis_1": None,
                    "leftover_map_person_axis_2": None,
                    "leftover_map_item_axis_1": None,
                    "leftover_map_item_axis_2": None,
                    "visibility_code": "public",
                    "corporate_entity_id": "00000000-0000-0000-0000-000000000002",
                    "process_unit_id": None,
                    "has_real_source_context": False,
                }
            ]
        if "from report_leftover_map_axis" in query:
            return []
        if "from report_leftover_map_coverage" in query:
            return []
        raise AssertionError(f"unexpected report query: {query}")


def test_fetch_period_reports_normalizes_only_nonfinite_cross_share() -> None:
    """Finite signed values survive; non-finite persisted values become JSON-safe null."""
    cases = (
        (Decimal("0.42"), 0.42),
        (Decimal("0"), 0.0),
        (Decimal("-0.24"), -0.24),
        (None, None),
        (Decimal("NaN"), None),
        (Decimal("Infinity"), None),
        (Decimal("-Infinity"), None),
    )
    for persisted, expected in cases:
        payload = asyncio.run(
            report_ingestion.fetch_period_reports(
                _PrimaryReportConnection(persisted),  # type: ignore[arg-type]
                "thread_group",
                "2026-W02",
            )
        )
        actual = payload[0]["leftover_pairs"][0]["leftover_map_cross_share"]
        assert actual == expected
        json.dumps(payload, allow_nan=False)
