"""Cutoff-known bodies come from source_post_revision, never an invented sentence."""

from datetime import datetime, timezone
from pathlib import Path

from backend.app.source_post_revision import (
    fetch_known_at_revisions,
    parse_as_of_clock,
    revision_covers_clock,
)

_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = _ROOT / "migrations" / "0024_source_post_revision.sql"
_ROLLBACK = _ROOT / "migrations" / "rollback" / "0024_source_post_revision.sql"
_CUTOFF = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)


def test_parse_as_of_clock_treats_z_and_naive_as_utc() -> None:
    parsed = parse_as_of_clock("2026-01-12T12:00:00Z")
    assert parsed == _CUTOFF
    naive = parse_as_of_clock("2026-01-12T12:00:00")
    assert naive == _CUTOFF


def test_parse_as_of_clock_rejects_empty_or_unparseable() -> None:
    try:
        parse_as_of_clock("   ")
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("empty as_of must fail closed")
    try:
        parse_as_of_clock("not-a-clock")
    except ValueError:
        return
    raise AssertionError("unparseable as_of must fail closed")


def test_revision_interval_is_half_open() -> None:
    written = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    superseded = datetime(2026, 1, 13, 9, 0, tzinfo=timezone.utc)
    assert revision_covers_clock(written, superseded, written) is True
    assert revision_covers_clock(written, superseded, _CUTOFF) is True
    assert revision_covers_clock(written, superseded, superseded) is False
    assert revision_covers_clock(written, None, superseded) is True
    assert revision_covers_clock(superseded, None, _CUTOFF) is False


def test_revision_migration_records_title_or_body_rewrites_only() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    rollback = _ROLLBACK.read_text(encoding="utf-8")
    assert "source_post_revision" in sql
    assert "record_source_post_revision" in sql
    assert "update of post_title, post_body" in sql
    assert "superseded_at" in sql
    assert "drop table if exists source_post_revision" in rollback
    seed = (_ROOT / "scripts" / "seed_demo_data.py").read_text(encoding="utf-8")
    assert "later delivery window" in seed
    assert "delayed shipment." in seed
    assert seed.index("0023_analysis_run_outbox.sql") < seed.index(
        "0024_source_post_revision.sql"
    )
    assert seed.index("0024_source_post_revision.sql") < seed.index(
        "0025_role_person_catalog_identity.sql"
    )


def test_batch_revision_lookup_omits_missing_covers() -> None:
    import inspect

    source = inspect.getsource(fetch_known_at_revisions)
    assert "source_post_revision" in source
    assert "written_at <= $2" in source
    assert "superseded_at is null or superseded_at > $2" in source
    assert "never a live body" in source.lower() or "Missing covers are omitted" in source
