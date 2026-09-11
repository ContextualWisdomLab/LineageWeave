"""Regression for persisted cross-share transport on the primary report read model."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from backend.app import report_ingestion


class _ReportConnection:
    """Minimal asyncpg-shaped fixture for one primary report grouping."""

    def __init__(self) -> None:
        self.leftover_query = ""

    async def fetch(self, query: str, *_args: Any) -> list[dict[str, Any]]:
        if "from report_period_score" in query:
            return [
                {
                    "grouping_kind": "process_unit",
                    "grouping_key": "PU-1",
                    "period_code": "2026-W02",
                    "rubric_version": "v1",
                    "selected_model": "fast-mlsirm",
                    "mean_theta": 0.25,
                    "mean_theta_sd": 0.5,
                    "post_count": 4,
                    "item_count": 3,
                    "fit_loglik": -1.5,
                    "fit_converged": True,
                    "calibration_score": 0.9,
                    "computed_at": datetime(2026, 1, 6, tzinfo=timezone.utc),
                    "link_method": "fixture",
                    "anchor_period_code": None,
                    "delta_mean_theta": None,
                }
            ]
        if "from report_member_score" in query or "from report_item_information" in query:
            return []
        if "from report_leftover_pair" in query:
            self.leftover_query = query
            return [
                {
                    "grouping_key": "PU-1",
                    "pair_kind": pair_kind,
                    "post_id": f"post-{index}",
                    "criterion_code": "criterion-a",
                    "leftover_distance": 1.0,
                    "leftover_residual": -0.5,
                    "observed_response": 1.0,
                    "expected_response": 0.5,
                    "leftover_map_rank": index,
                    "leftover_map_unexplained": -0.25,
                    "leftover_map_cross_share": cross_share,
                    "leftover_map_reconstruction": None,
                    "leftover_map_unexplained_share": None,
                    "leftover_map_explained_share": None,
                    "leftover_map_person_axis_1": None,
                    "leftover_map_person_axis_2": None,
                    "leftover_map_item_axis_1": None,
                    "leftover_map_item_axis_2": None,
                    "post_title": f"Post {index}",
                    "visibility_code": "public",
                    "corporate_entity_id": "entity-1",
                    "process_unit_id": "PU-1",
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
        if "from report_leftover_map_axis" in query or "from report_leftover_map_coverage" in query:
            return []
        raise AssertionError(f"unexpected query: {query}")

    async def fetchrow(self, query: str, *_args: Any) -> dict[str, Any] | None:
        if "from process_unit" in query:
            return {"process_unit_name": "Process unit 1"}
        raise AssertionError(f"unexpected fetchrow: {query}")


def test_period_reports_transports_persisted_cross_share() -> None:
    """Preserve finite signed x values and normalize null or non-finite x to null."""

    connection = _ReportConnection()
    payload = asyncio.run(
        report_ingestion.fetch_period_reports(connection, "process_unit", "2026-W02")
    )
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
