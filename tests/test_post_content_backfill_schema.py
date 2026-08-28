"""Static schema contract for the bounded post-content backfill scan."""

from pathlib import Path


MIGRATION = Path("migrations/0258_post_content_backfill_candidate_index.sql")


def test_backfill_candidate_index_matches_the_ordered_eligibility_scan() -> None:
    """The replay-safe partial index owns ordering and source eligibility."""
    sql = " ".join(MIGRATION.read_text().lower().split())

    assert "create index if not exists source_post_content_backfill_candidate_idx" in sql
    assert (
        "on source_post ( coalesce(event_occurred_at, created_at), created_at, post_id )"
        in sql
    )
    for column in ("source_draft_code", "source_deleted_flag"):
        assert f"nullif(btrim({column}), '')" in sql


def test_backfill_index_owns_its_stacked_migration_identity() -> None:
    """The index owns 0258 rather than reusing the parent stack's 0257."""

    migrations = MIGRATION.parent

    assert MIGRATION.name.startswith("0258_")
    assert not (migrations / "0257_post_content_backfill_candidate_index.sql").exists()
