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

    migrate.sh replaced the old explicit `0012_*|0013_*|...` case-pattern
    whitelist (which silently fell behind as new migration files were
    added, per the ADR this test guards) with a numeric boundary check.
    Assert on that mechanism instead of the retired literal token.
    """
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    # 0001-0011 are baked into the image; 0012 and up must replay.
    assert '"$migration_number" -lt 12' in script
    # Base-10 forced so a leading-zero migration number (e.g. 0103) isn't
    # misread as octal.
    assert "10#${migration_name%%_*}" in script
