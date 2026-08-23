"""Tests for scripts/backfill_thread_group_keys.py's backfill logic.

`backfill_thread_group_keys` is the pure per-connection operation, isolated
from pool/connection setup precisely so it can be exercised here without a
real database -- same reasoning as tests/test_customer_hint_ingestion.py's
fakes.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import scripts.backfill_thread_group_keys as backfill


class _Connection:
    """Simulates the guard SELECT and the UPDATE...RETURNING this script issues.

    ``rows`` models every ``source_post`` row carrying the placeholder
    signature (``thread_group_key`` equal to the row's own record key):
    each entry is ``had_project_code`` (True when the row's
    ``source_project_code`` was non-empty, so it now feeds the
    secondary-key evidence channel). A row NOT in ``rows`` models a
    seeded/genuinely-mapped row the placeholder predicate never touches.
    ``anchored_runs`` models existing analysis_scope_thread_group runs
    whose live scope match the rewrite would orphan.
    """

    def __init__(self, rows: list[bool], anchored_runs: list[str] | None = None) -> None:
        self._rows = rows
        self._anchored_runs = anchored_runs or []
        self.executed: list[str] = []

    @asynccontextmanager
    async def transaction(self):
        yield self

    async def fetch(self, query: str, *args: object):
        self.executed.append(" ".join(query.split()))
        if "analysis_run_scope" in query:
            return [
                {"analysis_run_id": run_id, "scope_key": f"key-{run_id}"}
                for run_id in self._anchored_runs
            ]
        return [{"had_project_code": had_project_code} for had_project_code in self._rows]


def test_backfill_clears_placeholders_and_routes_project_codes_to_secondary() -> None:
    conn = _Connection([True, True, False, False, False])
    result = asyncio.run(backfill.backfill_thread_group_keys(conn, dry_run=False))
    assert result == {
        "cleared_placeholder_posts": 5,
        "project_secondary_evidence_posts": 2,
    }
    assert len(conn.executed) == 2
    assert "analysis_run_scope" in conn.executed[0]
    update = conn.executed[1]
    assert "update source_post" in update
    # The placeholder signature is the only predicate -- seeded rows with
    # real designed keys must never match.
    assert "btrim(thread_group_key) = btrim(source_record_key)" in update
    # Project code is routed to the secondary-key evidence channel, never
    # to thread_group_key -- a hard project partition would wall off
    # related posts that lack a project code, exactly the links the
    # reconstruction library exists to find.
    assert "set thread_group_key = ''" in update
    assert "secondary_grouping_key = coalesce(nullif(btrim(source_project_code), ''), '')" in update


def test_backfill_fails_closed_when_a_thread_group_scoped_run_would_be_orphaned() -> None:
    # analysis_scope_thread_group runs resolve `thread_group_key =
    # scope_key` live on every read (ABAC visibility) -- their member
    # posts are snapshot-frozen but the scope match is not. Rewriting
    # the keys out from under such a run silently detaches it, so the
    # backfill must refuse instead, before any UPDATE.
    conn = _Connection([True, False], anchored_runs=["run-1", "run-2"])
    try:
        asyncio.run(backfill.backfill_thread_group_keys(conn, dry_run=False))
    except RuntimeError as exc:
        assert "run-1" in str(exc)
        assert "run-2" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
    assert all("update source_post" not in query for query in conn.executed)


def test_backfill_no_placeholder_rows_is_a_clean_no_op() -> None:
    conn = _Connection([])
    result = asyncio.run(backfill.backfill_thread_group_keys(conn, dry_run=False))
    assert result == {
        "cleared_placeholder_posts": 0,
        "project_secondary_evidence_posts": 0,
    }


def test_dry_run_reports_counts_but_raises_to_force_a_rollback() -> None:
    conn = _Connection([True, False])
    try:
        asyncio.run(backfill.backfill_thread_group_keys(conn, dry_run=True))
    except backfill._RollbackDryRun as rolled_back:
        assert rolled_back.project_evidence == 1
        assert rolled_back.cleared == 2
    else:
        raise AssertionError("expected _RollbackDryRun")


class _FakePool:
    def __init__(self, conn: _Connection) -> None:
        self._conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self._conn

    async def close(self) -> None:
        return None


def _patch_pool(monkeypatch, conn: _Connection) -> None:
    async def fake_create_pool(*_args, **_kwargs):
        return _FakePool(conn)

    monkeypatch.setattr(backfill.asyncpg, "create_pool", fake_create_pool)
    monkeypatch.setattr(
        backfill, "load_settings", lambda: type("S", (), {"database_url": "postgresql://x"})()
    )


def test_run_reports_dry_run_counts_without_the_internal_exception_leaking(monkeypatch) -> None:
    import argparse

    conn = _Connection([True, True, False])
    _patch_pool(monkeypatch, conn)
    result = asyncio.run(backfill._run(argparse.Namespace(dry_run=True)))
    assert result == {
        "cleared_placeholder_posts": 3,
        "project_secondary_evidence_posts": 2,
        "dry_run": True,
    }


def test_run_reports_write_counts_when_not_a_dry_run(monkeypatch) -> None:
    import argparse

    conn = _Connection([True, False, False])
    _patch_pool(monkeypatch, conn)
    result = asyncio.run(backfill._run(argparse.Namespace(dry_run=False)))
    assert result == {
        "cleared_placeholder_posts": 3,
        "project_secondary_evidence_posts": 1,
        "dry_run": False,
    }
