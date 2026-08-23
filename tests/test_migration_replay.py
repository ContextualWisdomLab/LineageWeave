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


def test_migrate_sh_replays_context_scoped_name_cache_migration() -> None:
    """Existing volumes must receive the context-scoped resolution key."""
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "0051_*" in script


def test_migrate_sh_replays_global_ask_context_migration() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "0052_*" in script


def test_migrate_sh_replays_project_history_lookup_indexes() -> None:
    """Existing volumes receive the bounded project-history lookup indexes."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker/postgres-init/migrate.sh").read_text(encoding="utf-8")
    forward = (root / "migrations/0053_project_history_lookup.sql").read_text(encoding="utf-8")
    rollback = (root / "migrations/rollback/0053_project_history_lookup.sql").read_text(
        encoding="utf-8"
    )

    assert "0053_*" in script
    for index_name in (
        "source_post_project_history_recent_idx",
        "source_post_project_code_history_idx",
        "source_post_project_name_history_idx",
        "post_project_mention_key_history_idx",
        "post_project_mention_name_history_idx",
        "post_lineage_edge_child_history_idx",
    ):
        assert f"create index if not exists {index_name}" in forward
        assert f"drop index if exists {index_name}" in rollback
