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
    `docker compose up`. A window starting above 0012 silently leaves
    report_leftover_pair missing on such volumes -- GET
    /api/reports/{grouping}/{period} then 500s on undefined_table the
    first time a period actually has leftover pairs.
    """
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "0012_*" in script
    assert "0163_*" in script


def test_tenant_settings_migration_is_safe_to_replay() -> None:
    """Existing Compose volumes receive tenant settings without repeat failures."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(
        encoding="utf-8"
    )
    migration = (root / "migrations" / "0103_tenant_settings.sql").read_text(
        encoding="utf-8"
    ).casefold()

    assert "0103_*" in script
    assert "create table if not exists tenant_settings" in migration
    assert "on conflict (id) do nothing" in migration


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
