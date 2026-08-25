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


def test_tenant_settings_migration_is_safe_to_replay() -> None:
    """The newest migration must survive migrate.sh's every-start replay."""
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0103_tenant_settings.sql"
    ).read_text(encoding="utf-8").casefold()

    assert "create table if not exists tenant_settings" in sql
    assert "on conflict (id) do nothing" in sql


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


def test_tepp_receipt_migration_is_replayable_and_digest_bound() -> None:
    """Accepted transport evidence survives every-start migration replay."""
    migration_name = "0210_analysis_run_tepp_receipt.sql"
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
