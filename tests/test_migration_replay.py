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
def test_migrate_sh_replays_source_commercial_context_migration_on_existing_volumes() -> None:
    """Existing Compose volumes must receive the source context columns."""
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "0130_*" in script


def test_migrate_sh_replays_topic_lineage_migrations_on_existing_volumes() -> None:
    """Existing Compose volumes must receive the topic-lineage kind and result table."""
    script = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "postgres-init"
        / "migrate.sh"
    ).read_text(encoding="utf-8")

    assert "0131_*" in script
    assert "0132_*" in script


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
