"""Cutoff-known bodies come from source_post_revision, never an invented sentence."""

import ast
from datetime import UTC, datetime
from pathlib import Path

from backend.app.source_post_revision import (
    fetch_known_at_revisions,
    parse_as_of_clock,
    revision_covers_clock,
)

_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = _ROOT / "migrations" / "0024_source_post_revision.sql"
_ROLLBACK = _ROOT / "migrations" / "rollback" / "0024_source_post_revision.sql"
_CUTOFF = datetime(2026, 1, 12, 12, 0, tzinfo=UTC)


def test_source_post_revision_uses_semantic_owned_identifiers() -> None:
    """Keep revision clocks, persistence rows, and fixtures domain-specific."""
    source_paths = (
        _ROOT / "backend" / "app" / "source_post_revision.py",
        Path(__file__),
    )
    forbidden_identifiers = {
        "_iso",
        "clock",
        "conn",
        "exc",
        "naive",
        "parsed",
        "rollback",
        "row",
        "rows",
        "seed",
        "source",
        "sql",
        "start",
        "superseded",
        "text",
        "value",
        "written",
    }
    required_identifiers = {
        "_iso_timestamp",
        "clock_text",
        "database_connection",
        "normalized_clock_text",
        "parsed_clock",
        "query_clock",
        "revision_start",
        "source_post_revision_row",
        "source_post_revision_rows",
        "timestamp_value",
    }
    owned_identifiers: set[str] = set()
    for source_path in source_paths:
        syntax_tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for syntax_node in ast.walk(syntax_tree):
            if isinstance(
                syntax_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                owned_identifiers.add(syntax_node.name)
            elif isinstance(syntax_node, ast.arg):
                owned_identifiers.add(syntax_node.arg)
            elif isinstance(syntax_node, ast.Name) and isinstance(
                syntax_node.ctx, ast.Store
            ):
                owned_identifiers.add(syntax_node.id)

    assert not (forbidden_identifiers & owned_identifiers)
    assert required_identifiers <= owned_identifiers


def test_parse_as_of_clock_treats_z_and_naive_as_utc() -> None:
    zulu_clock = parse_as_of_clock("2026-01-12T12:00:00Z")
    assert zulu_clock == _CUTOFF
    naive_clock = parse_as_of_clock("2026-01-12T12:00:00")
    assert naive_clock == _CUTOFF


def test_parse_as_of_clock_rejects_empty_or_unparseable() -> None:
    try:
        parse_as_of_clock("   ")
    except ValueError as clock_error:
        assert "empty" in str(clock_error)
    else:
        raise AssertionError("empty as_of must fail closed")
    try:
        parse_as_of_clock("not-a-clock")
    except ValueError:
        return
    raise AssertionError("unparseable as_of must fail closed")


def test_revision_interval_is_half_open() -> None:
    revision_written_at = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)
    revision_superseded_at = datetime(2026, 1, 13, 9, 0, tzinfo=UTC)
    assert (
        revision_covers_clock(
            revision_written_at, revision_superseded_at, revision_written_at
        )
        is True
    )
    assert (
        revision_covers_clock(revision_written_at, revision_superseded_at, _CUTOFF)
        is True
    )
    assert (
        revision_covers_clock(
            revision_written_at, revision_superseded_at, revision_superseded_at
        )
        is False
    )
    assert (
        revision_covers_clock(revision_written_at, None, revision_superseded_at) is True
    )
    assert revision_covers_clock(revision_superseded_at, None, _CUTOFF) is False


def test_revision_migration_records_title_or_body_rewrites_only() -> None:
    migration_sql = _MIGRATION.read_text(encoding="utf-8")
    rollback_sql = _ROLLBACK.read_text(encoding="utf-8")
    assert "source_post_revision" in migration_sql
    assert "record_source_post_revision" in migration_sql
    assert "update of post_title, post_body" in migration_sql
    assert "superseded_at" in migration_sql
    assert "drop table if exists source_post_revision" in rollback_sql
    seed_script = (_ROOT / "scripts" / "seed_demo_data.py").read_text(encoding="utf-8")
    assert "later delivery window" in seed_script
    assert "delayed shipment." in seed_script
    assert seed_script.index("0023_analysis_run_outbox.sql") < seed_script.index(
        "0024_source_post_revision.sql"
    )
    assert seed_script.index("0024_source_post_revision.sql") < seed_script.index(
        "0025_role_person_catalog_identity.sql"
    )


def test_batch_revision_lookup_omits_missing_covers() -> None:
    import inspect

    revision_loader_source = inspect.getsource(fetch_known_at_revisions)
    assert "source_post_revision" in revision_loader_source
    assert "written_at <= $2" in revision_loader_source
    assert "superseded_at is null or superseded_at > $2" in revision_loader_source
    assert (
        "never a live body" in revision_loader_source.lower()
        or "Missing covers are omitted" in revision_loader_source
    )
