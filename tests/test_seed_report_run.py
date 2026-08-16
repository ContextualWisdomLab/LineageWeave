"""Seeded period-report analysis runs record the built report, never a theta."""

import inspect

from scripts.seed_demo_data import (
    DEMO_REPORT_IDEMPOTENCY_KEY,
    _demo_period_report_persisted,
    _seed_demo_report_run,
    seed,
)


class _ReportSeedCursor:
    """Drive ``_seed_demo_report_run`` without a live database."""

    def __init__(self, *, report_persisted: bool = True) -> None:
        self.report_persisted = report_persisted
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
        if last.lstrip().startswith("select") and "from report_period_score" in last:
            return (1,) if self.report_persisted else None
        return None


def _report_run_inserts(cursor: _ReportSeedCursor) -> list[tuple[str, object]]:
    return [
        (sql, params)
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run" in sql
    ]


def _status_params(cursor: _ReportSeedCursor) -> list[object]:
    return [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run_status_event" in sql
    ]


def test_seed_calls_period_report_before_report_run() -> None:
    source = inspect.getsource(seed)
    assert source.index("_seed_demo_period_report(") < source.index(
        "_seed_demo_report_run("
    )


def test_demo_period_report_persisted_is_presence_only() -> None:
    cursor = _ReportSeedCursor(report_persisted=True)
    assert _demo_period_report_persisted(cursor, "corp-1") is True
    presence_sql = next(
        sql for sql in cursor.statements if "from report_period_score" in sql
    )
    assert "select 1" in presence_sql
    assert "mean_theta" not in presence_sql
    assert "theta" not in presence_sql.lower()
    assert cursor.params[-1] == ("corp-1",)


def test_seed_demo_report_run_inserts_succeeded_report_without_a_theta() -> None:
    cursor = _ReportSeedCursor(report_persisted=True)
    _seed_demo_report_run(cursor, "account-1", "corp-1")
    run_inserts = _report_run_inserts(cursor)
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
    status_params = _status_params(cursor)
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


def test_seed_demo_report_run_fails_closed_when_report_tables_are_missing() -> None:
    cursor = _ReportSeedCursor(report_persisted=False)
    _seed_demo_report_run(cursor, "account-1", "corp-1")
    status_params = _status_params(cursor)
    assert any(
        event_params is not None
        and "analysis_status_failed" in event_params
        and "period_report_not_persisted" in event_params
        for event_params in status_params
    )
    assert not any(
        event_params is not None and "analysis_status_succeeded" in event_params
        for event_params in status_params
    )
    assert not any(
        event_params is not None
        and any(
            isinstance(value, str) and ("theta" in value.lower() or "θ" in value)
            for value in event_params
        )
        for event_params in status_params
    )
