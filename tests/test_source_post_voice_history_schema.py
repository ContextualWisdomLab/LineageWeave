"""Static contract tests for ADR 0252 temporal primary Voice history."""

from __future__ import annotations

from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0238_source_post_voice_history.sql"
)


def test_primary_voice_history_uses_non_overlapping_half_open_intervals() -> None:
    """The database preserves recurring Voices and rejects overlapping primaries."""
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "add column if not exists effective_to timestamptz" in sql
    assert "primary key (post_id, voice_type_code, effective_from)" in sql
    assert "tstzrange(effective_from, effective_to, '[)') with &&" in sql
    assert "where (is_primary)" in sql
    assert "effective_from < effective_to" in sql


def test_primary_voice_change_closes_current_rows_before_insert() -> None:
    """One transaction instant closes the prior state and opens the new primary."""
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "change_at timestamptz := clock_timestamp()" in sql
    assert "set effective_to = change_at" in sql
    assert "and (is_primary or voice_type_code = new.voc_type_code)" in sql
    assert sql.index("set effective_to = change_at") < sql.index(
        "insert into source_post_voice"
    )
    assert "on conflict" not in sql
