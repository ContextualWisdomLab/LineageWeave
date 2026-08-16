"""Seeded period-report analysis runs record the built report, never a theta."""

import inspect

from scripts.seed_demo_data import (
    DEMO_REPORT_IDEMPOTENCY_KEY,
    _seed_demo_report_run,
    seed,
)


class _ReportSeedCursor:
    """Drive ``_seed_demo_report_run`` without a live database."""

    def __init__(self) -> None:
        self.statements: list[str] = []
        self.params: list[object] = []

    def execute(self, sql: str, params=None) -> None:
        self.statements.append(" ".join(sql.split()))
        self.params.append(params)

    def fetchone(self):
        last = self.statements[-1]
        if last.lstrip().startswith("select") and "from analysis_source_snapshot" in last:
            return None
        if "insert into analysis_source_snapshot" in last:
            return ("snapshot-demo",)
        if last.lstrip().startswith("select") and "from analysis_source_count" in last:
            return None
        if last.lstrip().startswith("select") and "from analysis_run" in last:
            return None
        if "insert into analysis_run" in last:
            return ("run-demo-report",)
        return None


def test_seed_calls_report_run_after_period_report_tables() -> None:
    """``seed()`` must persist scored tables before the Succeeded registry row."""
    source = inspect.getsource(seed)
    period_at = source.index("_seed_demo_period_report(")
    report_at = source.index("_seed_demo_report_run(")
    assert period_at < report_at
    assert "theta" not in source[period_at:report_at].lower()
    assert "θ" not in source[period_at:report_at]


def test_seed_demo_report_run_inserts_succeeded_report_without_a_theta() -> None:
    cursor = _ReportSeedCursor()
    _seed_demo_report_run(cursor, "account-1", "corp-1")
    run_inserts = [
        (sql, params)
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run" in sql
    ]
    assert run_inserts, "seed must insert the period-report analysis_run row"
    sql, params = run_inserts[0]
    assert "analysis_run_report" in sql
    assert params is not None
    assert DEMO_REPORT_IDEMPOTENCY_KEY in params
    assert "report-run-v1" in sql
    assert not any(
        isinstance(value, str) and ("theta" in value.lower() or "θ" in value)
        for value in params
    )
    status_params = [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run_status_event" in sql
    ]
    assert any(
        event_params is not None and "analysis_status_succeeded" in event_params
        for event_params in status_params
    )
    assert not any(
        event_params is not None and "analysis_status_failed" in event_params
        for event_params in status_params
    )
    assert not any(
        event_params is not None
        and any(
            isinstance(value, str) and "theta" in value.lower()
            for value in event_params
        )
        for event_params in status_params
    )
    assert not any("analysis_run_outbox" in sql for sql in cursor.statements)
