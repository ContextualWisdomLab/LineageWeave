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


def test_tenant_settings_migration_is_safe_to_replay() -> None:
    """The newest migration must survive migrate.sh's every-start replay."""
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0103_tenant_settings.sql"
    ).read_text(encoding="utf-8").casefold()

    assert "create table if not exists tenant_settings" in sql
    assert "on conflict (id) do nothing" in sql
