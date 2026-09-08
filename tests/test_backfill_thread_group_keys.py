"""Tests for scripts/backfill_thread_group_keys.py's backfill logic.

`backfill_thread_group_keys` is the pure per-connection operation, isolated
from pool/connection setup precisely so it can be exercised here without a
real database -- same reasoning as tests/test_customer_hint_ingestion.py's
fakes.
"""

from __future__ import annotations

import asyncio
import runpy
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import asyncpg
import backend.app.config as backend_config

import scripts.backfill_thread_group_keys as thread_group_backfill


class _ThreadGroupDatabaseConnection:
    """Simulates the guard SELECT and the UPDATE...RETURNING this script issues.

    ``placeholder_post_rows`` models every ``source_post`` row carrying the placeholder
    signature (``thread_group_key`` equal to the row's own record key):
    each entry is ``had_project_code`` (True when the row's
    ``source_project_code`` was non-empty, so it now feeds the
    secondary-key evidence channel). A row NOT in ``placeholder_post_rows`` models a
    seeded/genuinely-mapped row the placeholder predicate never touches.
    ``analysis_run_ids`` models existing analysis_scope_thread_group runs
    whose live scope match the rewrite would orphan.
    """

    def __init__(
        self,
        placeholder_post_rows: list[bool],
        analysis_run_ids: list[str] | None = None,
    ) -> None:
        """Initialize the transaction test double."""
        self._placeholder_post_rows = placeholder_post_rows
        self._analysis_run_ids = analysis_run_ids or []
        self.executed_queries: list[str] = []

    @asynccontextmanager
    async def transaction(self):
        """Return the transaction test double context."""
        yield self

    async def fetch(self, query: str, *args: object):
        """Return deterministic records for the requested query."""
        self.executed_queries.append(" ".join(query.split()))
        if "analysis_run_scope" in query:
            return [
                {
                    "analysis_run_id": analysis_run_id,
                    "scope_key": f"key-{analysis_run_id}",
                }
                for analysis_run_id in self._analysis_run_ids
            ]
        return [
            {"had_project_code": had_project_code}
            for had_project_code in self._placeholder_post_rows
        ]


def test_backfill_clears_placeholders_and_routes_project_codes_to_secondary() -> None:
    """Verify placeholders clear and project codes become secondary keys."""
    database_connection = _ThreadGroupDatabaseConnection(
        [True, True, False, False, False]
    )
    backfill_summary = asyncio.run(
        thread_group_backfill.backfill_thread_group_keys(
            database_connection, dry_run=False
        )
    )
    assert backfill_summary == {
        "cleared_placeholder_posts": 5,
        "project_secondary_evidence_posts": 2,
    }
    assert len(database_connection.executed_queries) == 2
    assert "analysis_run_scope" in database_connection.executed_queries[0]
    update_query = database_connection.executed_queries[1]
    assert "update source_post" in update_query
    # The placeholder signature is the only predicate -- seeded rows with
    # real designed keys must never match.
    assert "btrim(thread_group_key) = btrim(source_record_key)" in update_query
    # Project code is routed to the secondary-key evidence channel, never
    # to thread_group_key -- a hard project partition would wall off
    # related posts that lack a project code, exactly the links the
    # reconstruction library exists to find.
    assert "thread_group_key = ''" in update_query
    assert (
        "secondary_grouping_key = coalesce(nullif(btrim(source_project_code), ''), '')"
        in update_query
    )
    assert "source_thread_group_key = coalesce(" in update_query
    assert "source_thread_group_key, thread_group_key" in update_query
    assert "source_secondary_grouping_key = coalesce(" in update_query
    assert "source_secondary_grouping_key, secondary_grouping_key" in update_query


def test_backfill_fails_closed_when_a_thread_group_scoped_run_would_be_orphaned() -> (
    None
):
    """Reject a backfill that would orphan a scoped analysis run."""
    # analysis_scope_thread_group runs resolve `thread_group_key =
    # scope_key` live on every read (ABAC visibility) -- their member
    # posts are snapshot-frozen but the scope match is not. Rewriting
    # the keys out from under such a run silently detaches it, so the
    # backfill must refuse instead, before any UPDATE.
    database_connection = _ThreadGroupDatabaseConnection(
        [True, False], analysis_run_ids=["run-1", "run-2"]
    )
    try:
        asyncio.run(
            thread_group_backfill.backfill_thread_group_keys(
                database_connection, dry_run=False
            )
        )
    except RuntimeError as runtime_error:
        assert "run-1" in str(runtime_error)
        assert "run-2" in str(runtime_error)
    else:
        raise AssertionError("expected RuntimeError")
    assert all(
        "update source_post" not in query
        for query in database_connection.executed_queries
    )


def test_backfill_no_placeholder_rows_is_a_clean_no_op() -> None:
    """Treat an empty placeholder selection as a successful no-op."""
    database_connection = _ThreadGroupDatabaseConnection([])
    backfill_summary = asyncio.run(
        thread_group_backfill.backfill_thread_group_keys(
            database_connection, dry_run=False
        )
    )
    assert backfill_summary == {
        "cleared_placeholder_posts": 0,
        "project_secondary_evidence_posts": 0,
    }


def test_dry_run_reports_counts_but_raises_to_force_a_rollback() -> None:
    """Require dry-run counts while forcing transaction rollback."""
    database_connection = _ThreadGroupDatabaseConnection([True, False])
    try:
        asyncio.run(
            thread_group_backfill.backfill_thread_group_keys(
                database_connection, dry_run=True
            )
        )
    except thread_group_backfill._RollbackDryRun as rolled_back:
        assert rolled_back.project_evidence_post_count == 1
        assert rolled_back.cleared_post_count == 2
    else:
        raise AssertionError("expected _RollbackDryRun")


class _FakePool:
    def __init__(self, database_connection: _ThreadGroupDatabaseConnection) -> None:
        """Initialize the transaction test double."""
        self._database_connection = database_connection

    @asynccontextmanager
    async def acquire(self):
        """Return the configured database connection test double."""
        yield self._database_connection

    async def close(self) -> None:
        """Record closure of the pool test double."""
        return


def _patch_database_pool(
    monkeypatch, database_connection: _ThreadGroupDatabaseConnection
) -> None:
    """Install deterministic pool and settings test doubles."""

    async def fake_create_pool(*_args, **_kwargs):
        """Return the configured pool test double."""
        return _FakePool(database_connection)

    def fake_load_settings():
        """Return deterministic database settings."""
        return type("S", (), {"database_url": "postgresql://x"})()

    monkeypatch.setattr(thread_group_backfill.asyncpg, "create_pool", fake_create_pool)
    monkeypatch.setattr(thread_group_backfill, "load_settings", fake_load_settings)


def test_run_reports_dry_run_counts_without_the_internal_exception_leaking(
    monkeypatch,
) -> None:
    """Report dry-run counts without exposing the rollback sentinel."""
    import argparse

    database_connection = _ThreadGroupDatabaseConnection([True, True, False])
    _patch_database_pool(monkeypatch, database_connection)
    backfill_summary = asyncio.run(
        thread_group_backfill._run_thread_group_key_backfill(
            argparse.Namespace(dry_run=True)
        )
    )
    assert backfill_summary == {
        "cleared_placeholder_posts": 3,
        "project_secondary_evidence_posts": 2,
        "dry_run": True,
    }


def test_run_reports_write_counts_when_not_a_dry_run(monkeypatch) -> None:
    """Report persisted counts for a write run."""
    import argparse

    database_connection = _ThreadGroupDatabaseConnection([True, False, False])
    _patch_database_pool(monkeypatch, database_connection)
    backfill_summary = asyncio.run(
        thread_group_backfill._run_thread_group_key_backfill(
            argparse.Namespace(dry_run=False)
        )
    )
    assert backfill_summary == {
        "cleared_placeholder_posts": 3,
        "project_secondary_evidence_posts": 1,
        "dry_run": False,
    }


def test_script_entrypoint_reports_dry_run_counts(monkeypatch, capsys) -> None:
    """The documented operator command executes the rollback-safe boundary."""
    database_connection = _ThreadGroupDatabaseConnection([True, False])

    async def fake_create_pool(*_args, **_kwargs):
        """Return the configured pool test double."""
        return _FakePool(database_connection)

    script_path = Path(thread_group_backfill.__file__)
    monkeypatch.setattr(asyncpg, "create_pool", fake_create_pool)
    monkeypatch.setattr(
        backend_config,
        "load_settings",
        lambda: SimpleNamespace(database_url="postgresql://synthetic"),
    )
    monkeypatch.setattr(sys, "argv", [str(script_path), "--dry-run"])

    runpy.run_path(str(script_path), run_name="__main__")

    assert capsys.readouterr().out == (
        '{"cleared_placeholder_posts": 2, "dry_run": true, '
        '"project_secondary_evidence_posts": 1}\n'
    )
