import re
import subprocess
from pathlib import Path


def test_shared_metric_migration_does_not_narrow_later_report_dimensions() -> None:
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0009_shared_metric_bank.sql"
    ).read_text(encoding="utf-8")

    assert "if not exists" in sql
    assert "'team'" in sql
    assert "'project'" in sql
    assert "'shared_metric'" in sql


def test_migrate_sh_replays_leftover_pair_migration_on_existing_volumes() -> None:
    """migrate.sh's replay window must cover 0012 (report_leftover_pair).

    The Dockerfile only bakes migrations into a brand-new Postgres data
    directory via docker-entrypoint-initdb.d; any volume created before a
    migration existed never gets it unless migrate.sh replays it on every
    `docker compose up`. A boundary above 12 silently leaves
    report_leftover_pair missing on such volumes -- GET
    /api/reports/{grouping}/{period} then 500s on undefined_table the
    first time a period actually has leftover pairs.

    ADR 0166 replaces the stale per-file allowlist with one portable filename
    boundary. Assert on that mechanism instead of individual migration names.
    """
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "000[0-9]_*|001[01]_*) continue" in script
    assert "[0-9][0-9][0-9][0-9]_*)" in script
    assert '[ -f "$migration" ] || continue' in script
    assert "10#" not in script
    migration_script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    )
    subprocess.run(["sh", "-n", str(migration_script)], check=True)


def test_interval_relation_backfill_uses_utc_created_day() -> None:
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0140_post_lineage_interval_relation.sql"
    ).read_text(encoding="utf-8")

    assert "created_at at time zone 'UTC'" in sql


def test_semantic_content_unit_kind_migration_is_replay_safe() -> None:
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0221_semantic_content_unit_kinds.sql"
    ).read_text(encoding="utf-8").lower()

    assert "on conflict (lookup_code) do nothing" in sql
    for unit_kind in ("paragraph", "list", "table", "formula", "conversation_turn"):
        assert f"'{unit_kind}'" in sql


def test_source_conversation_turn_evidence_migration_is_replay_safe() -> None:
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0233_source_conversation_turn_evidence.sql"
    ).read_text(encoding="utf-8").lower()

    assert "add column if not exists source_evidence_reference" in sql
    assert "if not exists" in sql
    assert "post_content_unit_source_evidence_reference_check" in sql
    assert "octet_length(source_evidence_reference) <= 24000" in sql


def test_source_conversation_turn_evidence_rollback_matches_forward_number() -> None:
    """Operators can locate the rollback by the forward migration number."""
    rollback_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "rollback"
        / "0233_source_conversation_turn_evidence.sql"
    )

    assert rollback_path.exists()
    assert "source_evidence_reference" in rollback_path.read_text(encoding="utf-8")


def test_interval_relation_foreign_key_validation_is_separate() -> None:
    """Installing the FK must not scan a large existing edge table."""

    migrations = Path(__file__).resolve().parents[1] / "migrations"
    install_sql = (migrations / "0140_post_lineage_interval_relation.sql").read_text(
        encoding="utf-8"
    )
    validate_sql = (
        migrations / "0205_validate_post_lineage_interval_relation.sql"
    ).read_text(encoding="utf-8")

    assert "not valid" in install_sql.lower()
    assert "validate constraint post_lineage_edge_interval_relation_code_fkey" in validate_sql


def test_migrate_sh_replays_leftover_map_axis_migration_on_existing_volumes() -> None:
    """migrate.sh's replay window must cover 0169 (report_leftover_map_axis).

    Volumes created before leftover-map axis share shipped never get
    report_leftover_map_axis unless migrate.sh replays 0169 on every
    `docker compose up`. GET /api/reports/{grouping}/{period} then 500s
    on undefined_table the first time a period actually has leftover-map
    axes.

    ADR 0166's general four-digit filename boundary covers 0169 without a
    per-migration allowlist entry, so this asserts the migration file's
    own name still matches that boundary shape rather than a stale
    literal `migrate.sh` no longer contains.
    """
    migration_name = "0169_report_leftover_map_axis.sql"
    migration_path = Path(__file__).resolve().parents[1] / "migrations" / migration_name
    assert migration_path.exists()
    assert re.fullmatch(r"[0-9]{4}_.+\.sql", migration_name)
    assert int(migration_name[:4]) >= 12


def test_migrate_sh_replays_leftover_map_explained_share_on_existing_volumes() -> None:
    """migrate.sh's replay window covers ADR 0266's explained-share column.

    Volumes created before leftover-map explained share shipped never get
    leftover_map_explained_share unless migrate.sh replays 0244 on every
    ``docker compose up``. GET /api/reports/{grouping}/{period} then 500s
    on undefined_column the first time a period actually has leftover pairs.

    ADR 0166's general four-digit filename boundary covers 0244 without a
    per-migration allowlist entry. The column add is nullable and
    idempotent so a second start does not invent a leftover score.
    """
    migration_name = "0244_report_leftover_map_explained_share.sql"
    migration_path = Path(__file__).resolve().parents[1] / "migrations" / migration_name
    assert migration_path.exists()
    assert re.fullmatch(r"[0-9]{4}_.+\.sql", migration_name)
    assert int(migration_name[:4]) >= 12
    sql = migration_path.read_text(encoding="utf-8").casefold()
    assert "add column if not exists leftover_map_explained_share" in sql
    assert "add column if not exists leftover_map_unexplained_share" not in sql
    assert "check (" not in sql


def test_tenant_settings_migration_is_safe_to_replay() -> None:
    """The newest migration must survive migrate.sh's every-start replay."""
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0103_tenant_settings.sql"
    ).read_text(encoding="utf-8").casefold()

    assert "create table if not exists tenant_settings" in sql
    assert "on conflict (id) do nothing" in sql


def test_global_ask_migrations_are_safe_to_replay() -> None:
    """Fresh Compose databases also run the existing-volume migration service."""
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    job_sql = (migrations / "0165_global_ask_job.sql").read_text(encoding="utf-8").casefold()
    scope_sql = (migrations / "0203_global_ask_authorization_scope.sql").read_text(
        encoding="utf-8"
    ).casefold()

    assert "create table if not exists global_ask_job" in job_sql
    assert "create index if not exists global_ask_job_account_idx" in job_sql
    assert "create index if not exists global_ask_job_queued_idx" in job_sql
    assert "create table if not exists global_ask_job_corporate_entity_scope" in scope_sql
    assert "create table if not exists global_ask_job_process_unit_scope" in scope_sql


def test_public_claim_envelope_migration_is_replay_safe_and_provenance_bound() -> None:
    """Persisted public egress admission requires the exact PROV-O source post."""

    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0257_public_claim_envelope.sql"
    ).read_text(encoding="utf-8").casefold()

    assert "create table if not exists public_claim_envelope" in sql
    assert "provenance_assertion_id uuid not null" in sql
    assert "prov_was_derived_from" in sql
    assert "evidence_post_id is distinct from new.source_post_id" in sql
    assert "when count(binding.node_id) = 1" in sql
    assert "then (array_agg(binding.node_id))[1]" in sql
    assert "min(binding.node_id)" not in sql
    assert "group by assertion.relation_code" in sql
    assert "public_claim_requires_public_post" in sql
    assert "on conflict (lookup_code) do nothing" in sql


def test_channel_weight_migration_preserves_raw_source_grouping() -> None:
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0135_lineage_channel_weight.sql"
    ).read_text(encoding="utf-8")

    assert "source_thread_group_key" in migration
    assert "source_secondary_grouping_key" in migration


def test_channel_weight_migration_enforces_integrity_and_provenance() -> None:
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0135_lineage_channel_weight.sql"
    ).read_text(encoding="utf-8").casefold()

    for field in (
        "estimation_run_id",
        "estimator_version",
        "anchor_method_code",
        "source_snapshot_sha256",
        "knowledge_cutoff",
    ):
        assert field in migration
    assert "channel_code in ('temporal', 'secondary_key', 'text', 'llm')" in migration
    assert "weight_value > 0 and weight_value <= 1" in migration
    assert "sample_pair_count >= 200" in migration
    assert "source_snapshot_sha256 ~ '^[0-9a-f]{64}$'" in migration


def test_migrate_sh_replays_topic_lineage_migrations_on_existing_volumes() -> None:
    """Existing Compose volumes must receive the topic-lineage kind and result table.

    ADR 0166's general four-digit filename boundary covers 0131/0132 without a
    per-migration allowlist entry, so this asserts both migration files' own
    names still match that boundary shape rather than a stale literal
    `migrate.sh` no longer contains.
    """
    for migration_name in (
        "0131_analysis_run_topic_lineage_kind.sql",
        "0132_analysis_run_topic_lineage_result.sql",
        "0204_validate_topic_lineage_kind.sql",
    ):
        migration_path = Path(__file__).resolve().parents[1] / "migrations" / migration_name
        assert migration_path.exists()
        assert re.fullmatch(r"[0-9]{4}_.+\.sql", migration_name)
        assert int(migration_name[:4]) >= 12


def test_topic_lineage_kind_migration_is_idempotent_for_replay() -> None:
    """The kind-widening migration must not fail after a second apply."""
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0131_analysis_run_topic_lineage_kind.sql"
    ).read_text(encoding="utf-8")

    assert "on conflict (lookup_code) do nothing" in migration
    assert "drop constraint if exists analysis_run_kind_check" in migration
    assert "analysis_run_topic_lineage" in migration


def test_topic_lineage_result_migration_is_idempotent_for_replay() -> None:
    """The result-table migration must not fail after a second apply."""
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0132_analysis_run_topic_lineage_result.sql"
    ).read_text(encoding="utf-8")

    assert "create table if not exists analysis_run_topic_lineage_result" in migration
    assert "create index if not exists" in migration


def test_topic_influence_job_migration_is_replay_safe_and_fail_closed() -> None:
    """Existing TEPP projections gain one durable, score-free producer lease."""
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0260_topic_influence_job.sql"
    ).read_text(encoding="utf-8").casefold()

    assert "create table if not exists topic_influence_job" in sql
    assert "not_before" in sql
    assert "lease_expires_at" in sql
    assert "awaiting_evidence" in sql
    assert "wake_topic_influence_job_for_analysis" in sql
    assert "topic_model_run_influence_wake" in sql
    assert "analysis_run_influence_wake" in sql
    assert "after insert or update on topic_post_coordinate" in sql
    assert "after insert or update on topic_context_membership" in sql
    assert "after insert or update on topic_definition" in sql
    assert "add column if not exists lease_expires_at" in sql
    assert "drop constraint if exists topic_influence_job_check" in sql
    assert "and (lease_expires_at is null or lease_token is null)" in sql
    assert "add column if not exists lease_token uuid" in sql
    assert "create trigger topic_model_run_influence_queue" in sql
    assert "on conflict (topic_model_run_id) do nothing" in sql
    assert "where status_code = 'queued'" in sql
    assert "influence_value" not in sql


def test_tepp_receipt_migration_is_replayable_and_digest_bound() -> None:
    """Accepted transport evidence survives every-start migration replay."""
    migration_name = "0217_analysis_run_tepp_receipt.sql"
    sql = (
        Path(__file__).resolve().parents[1] / "migrations" / migration_name
    ).read_text(encoding="utf-8").casefold()

    assert re.fullmatch(r"[0-9]{4}_.+\.sql", migration_name)
    assert "create table if not exists analysis_run_tepp_receipt" in sql
    assert "remote_run_id text not null unique" in sql
    assert "request_sha256 ~ '^[0-9a-f]{64}$'" in sql
    assert "receipt_sha256 ~ '^[0-9a-f]{64}$'" in sql
    assert "accepted_status_code = 'accepted'" in sql
    assert "create index if not exists" in sql


def test_tepp_receipt_read_requires_the_replayed_schema() -> None:
    """A missing required table must fail before it poisons a claim transaction."""
    source = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "app"
        / "analysis_run_ingestion.py"
    ).read_text(encoding="utf-8")
    receipt_block = source.split('if row["run_kind_code"] == _TEPP_RUN_KIND:', 1)[1]
    receipt_block = receipt_block.split("return detail", 1)[0]

    assert "from analysis_run_tepp_receipt" in receipt_block
    assert "UndefinedTableError" not in receipt_block

def test_global_ask_job_migrations_are_idempotent_for_replay() -> None:
    """Existing volumes must replay the queue and authorization scope safely."""
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    job_sql = (migrations / "0165_global_ask_job.sql").read_text(encoding="utf-8")
    scope_sql = (migrations / "0203_global_ask_authorization_scope.sql").read_text(
        encoding="utf-8"
    )

    assert "create table if not exists global_ask_job" in job_sql
    assert job_sql.count("create index if not exists") == 2
    assert scope_sql.count("create table if not exists") == 2


def test_global_ask_public_verification_opt_in_is_replay_safe() -> None:
    """The durable worker receives explicit consent on old and new volumes."""

    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0218_global_ask_public_verification.sql"
    ).read_text(encoding="utf-8")

    assert "verify_external_requested boolean not null default false" in sql
    assert "add column if not exists" in sql
    assert "data_type <> 'boolean'" in sql


def test_global_ask_knowledge_cutoff_is_replay_safe() -> None:
    """Existing queue tables accept the optional as-of clock on every restart."""

    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0212_global_ask_knowledge_cutoff.sql"
    ).read_text(encoding="utf-8")

    assert "knowledge_cutoff timestamptz" in sql
    assert "add column if not exists" in sql
    assert "data_type <> 'timestamp with time zone'" in sql


def test_post_content_failure_validation_migration_is_replay_safe() -> None:
    """The union-free validation migration replays without losing its constraint."""

    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0256_post_content_failure_validation.sql"
    ).read_text(encoding="utf-8")

    assert sql.count("add column if not exists") == 2
    assert "drop constraint if exists post_content_failure_validation_check" in sql
    assert "failure_validation_code = 'operations_case_evidence_contract'" in sql
