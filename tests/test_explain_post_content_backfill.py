"""Tests for non-identifying backfill plan evidence."""

from scripts.explain_post_content_backfill import summarize_plan


def test_summarize_plan_reports_aggregate_buffers_and_relations_only() -> None:
    """The evidence summary contains plan metrics but no source-row values."""
    result = summarize_plan([{"Planning Time": 1.25, "Execution Time": 2.5, "Plan": {"Node Type": "Limit", "Actual Rows": 12, "Shared Hit Blocks": 2, "Plans": [{"Node Type": "Index Scan", "Relation Name": "source_post", "Shared Hit Blocks": 3, "Shared Read Blocks": 1}]}}])

    assert result == {
        "planning_time_ms": 1.25,
        "execution_time_ms": 2.5,
        "actual_rows": 12,
        "shared_hit_blocks": 2,
        "shared_read_blocks": 0,
        "temp_read_blocks": 0,
        "temp_written_blocks": 0,
        "node_counts": {"Index Scan": 1, "Limit": 1},
        "relation_scans": {"source_post": 1},
    }
