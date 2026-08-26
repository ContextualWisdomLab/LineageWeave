"""Static contract tests for ADR 0247's normalized Voice-of-X associations."""

from __future__ import annotations

from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0237_source_post_voice_combination.sql"
)


def test_voice_combination_schema_is_normalized_and_evidence_bearing() -> None:
    """Additional voices require provenance while the imported primary remains mirrored."""
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create table if not exists source_post_voice" in sql
    assert "primary key (post_id, voice_type_code)" in sql
    assert "check (is_primary or provenance_assertion_id is not null)" in sql
    assert "truth_status_code text not null" in sql
    assert "true, 'truth_observed'" in sql
    assert "where is_primary" in sql
    assert "select post_id, voc_type_code, true" in sql
    assert "after insert or update of voc_type_code on source_post" in sql
    assert "on conflict (post_id, voice_type_code) do update" in sql
    assert "where lookup_category = 'voc_type'" in sql
    assert "errcode = '23514'" in sql


def test_voice_combination_migration_uses_no_compound_or_inferred_voice_codes() -> None:
    """Composition reuses governed atomic codes instead of minting pair codes or heuristics."""
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "insert into common_lookup_value" not in sql
    assert "confidence" not in sql
