"""Replay contracts for the official occupational construct catalog schema."""

from pathlib import Path


MIGRATION = Path("migrations/0239_occupational_construct_catalog.sql")


def test_catalog_migration_is_replay_safe_and_preserves_source_integrity() -> None:
    """Existing volumes can replay the catalog metadata extension safely."""
    sql = MIGRATION.read_text(encoding="utf-8").casefold()
    assert "add column if not exists source_content_sha256" in sql
    assert "source_content_sha256 ~ '^[0-9a-f]{64}$'" in sql
    assert "add column if not exists construct_description" in sql
    assert "drop constraint if exists" in sql
