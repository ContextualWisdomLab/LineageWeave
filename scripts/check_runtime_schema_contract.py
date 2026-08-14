#!/usr/bin/env python3
"""Check persisted LineageWeave schema contracts against the runtime database."""

from __future__ import annotations

import json
import os
import psycopg

DSN = os.environ["LINEAGEWEAVE_DSN"]

REQUIRED_TABLE_COLUMNS = {
    "analysis_run_records": {
        "run_stamp",
        "row_count",
        "document_count",
        "thread_count",
        "metadata_payload",
    },
    "analysis_period_reports": {
        "report_id",
        "period_kind",
        "period_start",
        "period_end",
        "slice_kind",
        "slice_key",
        "document_count",
        "judge_verdict",
        "judge_source",
        "report_payload",
    },
    "analysis_evaluation_metrics": {
        "metric_id",
        "metric_family",
        "metric_code",
        "metric_label",
        "metric_description",
        "source_standard",
    },
    "analysis_report_metric_scores": {
        "report_id",
        "metric_id",
        "score",
        "verdict",
        "metric_source",
        "rationale",
    },
    "analysis_report_metric_evidence": {
        "report_id",
        "metric_id",
        "evidence_id",
    },
}


def _table_columns(cursor: psycopg.Cursor, table: str) -> set[str]:
    """Return the set of column names for a public schema table."""
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    )
    return {row[0] for row in cursor.fetchall()}


def _assert_schema() -> None:
    """Validate required tables and columns exist in the connected database."""
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            for table, required in REQUIRED_TABLE_COLUMNS.items():
                actual = _table_columns(cur, table)
                missing = sorted(required - actual)
                if missing:
                    raise AssertionError(f"{table} missing required columns: {', '.join(missing)}")
            if "evidence_ids" in _table_columns(cur, "analysis_report_metric_scores"):
                raise AssertionError("analysis_report_metric_scores must not store a multi-valued evidence_ids column")
            cur.execute(
                """
                SELECT row_count, document_count, thread_count, metadata_payload
                FROM analysis_run_records
                ORDER BY run_stamp DESC
                LIMIT 1
                """
            )
            run_row = cur.fetchone()
            if not run_row:
                raise AssertionError("analysis_run_records has no rows")
            row_count, document_count, thread_count, metadata = run_row
            metadata = metadata if isinstance(metadata, dict) else json.loads(metadata)
            for key in ("row_count", "document_count", "thread_count"):
                if key not in metadata:
                    raise AssertionError(f"latest analysis_run_records metadata missing {key}")
            if row_count != metadata.get("row_count"):
                raise AssertionError("latest row_count metadata mismatch")
            if document_count != metadata.get("document_count"):
                raise AssertionError("latest document_count metadata mismatch")
            if thread_count != metadata.get("thread_count"):
                raise AssertionError("latest thread_count metadata mismatch")
            cur.execute(
                """
                SELECT COUNT(*), COUNT(*) FILTER (WHERE judge_source IS NOT NULL), COUNT(*) FILTER (WHERE judge_verdict IS NOT NULL)
                FROM analysis_period_reports
                """
            )
            total, judge_source_count, judge_verdict_count = cur.fetchone()
            if total == 0:
                raise AssertionError("analysis_period_reports must not be empty")
            if judge_source_count != total:
                raise AssertionError("all analysis_period_reports rows must have judge_source")
            if judge_verdict_count != total:
                raise AssertionError("all analysis_period_reports rows must have judge_verdict")


def main() -> int:
    """Return process exit code for shell orchestration."""
    _assert_schema()
    print("lineageweave-runtime-schema-contract-ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        raise SystemExit(str(error))
