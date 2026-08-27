"""Replay contracts for the official occupational construct catalog schema."""

from pathlib import Path


MIGRATION = Path("migrations/0239_occupational_construct_catalog.sql")
SEARCH_MIGRATION = Path("migrations/0242_occupational_construct_catalog_search.sql")


def test_catalog_migration_is_replay_safe_and_preserves_source_integrity() -> None:
    """Existing volumes can replay the catalog metadata extension safely."""
    sql = MIGRATION.read_text(encoding="utf-8").casefold()
    assert "add column if not exists source_content_sha256" in sql
    assert "source_content_sha256 ~ '^[0-9a-f]{64}$'" in sql
    assert "add column if not exists construct_description" in sql
    assert "construct_description is null" in sql
    assert "btrim(construct_description) <> ''" in sql
    assert "drop constraint if exists" in sql


def test_catalog_search_migration_is_replay_safe() -> None:
    """Label indexes can replay on existing volumes without OFFSET search."""
    sql = SEARCH_MIGRATION.read_text(encoding="utf-8").casefold()
    assert "create index if not exists occupational_construct_preferred_label_trgm_idx" in sql
    assert "create index if not exists occupational_construct_description_trgm_idx" in sql
    assert "post_occupational_construct_assertion_construct_post_idx" in sql
    assert "offset" not in sql
