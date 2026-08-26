"""Static schema contracts for ADR 0249 occupational assertions."""

from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[1] / "migrations/0238_occupational_construct_assertion.sql"
EXTRACTION_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations/0240_occupational_construct_extraction_run.sql"
)


def test_construct_migration_is_normalized_replay_safe_and_indexed() -> None:
    """The migration owns three replay-safe tables and both query directions."""
    sql = MIGRATION.read_text(encoding="utf-8").casefold()
    for table in (
        "occupational_construct_vocabulary",
        "occupational_construct",
        "post_occupational_construct_assertion",
    ):
        assert f"create table if not exists {table}" in sql
    assert "references post_content_unit(post_content_unit_id)" in sql
    assert "references occupational_construct(construct_id)" in sql
    assert "references common_lookup_value(lookup_code)" in sql
    for truth_status in (
        "truth_authoritative",
        "truth_observed",
        "truth_inferred",
        "truth_proposed",
        "truth_superseded",
        "truth_rejected",
    ):
        assert truth_status in sql
    assert "validate_occupational_construct_evidence" in sql
    assert "strpos(selected_unit_text, new.evidence_text) = 0" in sql
    assert "(post_id, generated_at desc, assertion_id)" in sql
    assert "(construct_id, post_id)" in sql


def test_construct_assertion_schema_contains_no_local_measurement() -> None:
    """Persistence cannot smuggle scores, weights, or person traits into the model."""
    assertion_sql = MIGRATION.read_text(encoding="utf-8").split(
        "create table if not exists post_occupational_construct_assertion", 1
    )[1].split(");", 1)[0].casefold()
    for prohibited in ("score", "weight", "intensity", "importance", "person_id"):
        assert prohibited not in assertion_sql


def test_extraction_run_distinguishes_empty_success_for_one_body_digest() -> None:
    """A replay-safe normalized ledger records successful empty extraction."""
    sql = EXTRACTION_MIGRATION.read_text(encoding="utf-8").casefold()
    assert "create table if not exists post_occupational_construct_extraction" in sql
    assert "post_id uuid primary key references source_post(post_id)" in sql
    assert "source_body_sha256 ~ '^[0-9a-f]{64}$'" in sql
    assert "(source_body_sha256, post_id)" in sql
    assert "job.status_code = 'post_content_ingestion_succeeded'" in sql
    assert "extraction.post_id is null" in sql
    assert "set status_code = 'post_content_ingestion_queued'" in sql
    assert "insert into post_content_ingestion_job_status_event" in sql
