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


def test_migrate_sh_replays_tenant_settings_migration_on_existing_volumes() -> None:
    """Existing Compose volumes must receive the tenant-settings table."""
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "0103_*" in script


def test_tenant_settings_migration_is_idempotent_for_replay() -> None:
    """The replayed migration must not fail after its table already exists."""
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0103_tenant_settings.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS tenant_settings" in migration
    assert "ON CONFLICT (id) DO NOTHING" in migration


def test_migrate_sh_replays_database_identifier_migration_on_existing_volumes() -> None:
    """Existing Compose volumes must receive the canonical identifier names."""
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "0104_*" in script


def test_migrate_sh_replays_global_ask_history_migration_on_existing_volumes() -> None:
    """Compose must create Global Ask history tables on every volume."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(encoding="utf-8")
    migration = (root / "migrations" / "0105_global_ask_conversation_history.sql").read_text(
        encoding="utf-8"
    )

    assert "0105_*" in script
    assert "create table if not exists global_ask_session" in migration


def test_migrate_sh_replays_source_commercial_context_migration_on_existing_volumes() -> None:
    """Existing Compose volumes must receive the source context columns."""
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "0130_*" in script
