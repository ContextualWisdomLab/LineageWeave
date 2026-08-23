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


def test_superseded_body_search_indexes_are_skipped_on_replay() -> None:
    """0035 must not rebuild indexes that 0036 immediately removes."""
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0035_body_search_prefix.sql"
    ).read_text(encoding="utf-8")

    assert "to_regclass('public.source_post_search_prefix_trgm_idx') is null" in migration
    assert "to_regclass('public.source_post_search_fts_idx') is null" in migration
    assert migration.count("\\if :build_legacy_") == 2


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


def test_migrate_sh_replays_tenant_identity_metadata_migration_on_existing_volumes() -> None:
    """Existing Compose volumes must receive explicit shell identity metadata."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(encoding="utf-8")
    migration = (root / "migrations" / "0176_tenant_identity_metadata.sql").read_text(
        encoding="utf-8"
    )

    assert "0176_*" in script
    assert "add column if not exists system_name" in migration
    assert "tenant_settings_copyright_year_range_check" in migration


def test_migrate_sh_replays_analysis_run_status_same_clock_on_existing_volumes() -> None:
    """Existing volumes must replace the analysis-run status trigger from one clock."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(encoding="utf-8")
    migration = (root / "migrations" / "0173_analysis_run_status_same_clock.sql").read_text(
        encoding="utf-8"
    )

    assert "0173_*" in script
    assert "create or replace function enforce_analysis_run_status_transition" in migration
    assert "write_clock" in migration


def test_migrate_sh_replays_leftover_observed_expected_on_existing_volumes() -> None:
    """Existing leftover pair rows must receive nullable observed Y and expected E."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(encoding="utf-8")
    migration = (root / "migrations" / "0177_report_leftover_observed_expected.sql").read_text(
        encoding="utf-8"
    )

    assert "0177_*" in script
    assert "add column if not exists observed_response" in migration
    assert "add column if not exists expected_response" in migration
    assert "leftover_pair_observed_expected_reconcile_chk" in migration


def test_migrate_sh_replays_catalog_unresolved_reason_migration_on_existing_volumes() -> None:
    """Existing Compose volumes must receive the new unresolved-reason column."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(encoding="utf-8")
    migration = (root / "migrations" / "0134_catalog_unresolved_reason.sql").read_text(
        encoding="utf-8"
    )

    assert "0134_*" in script
    assert "add column if not exists catalog_unresolved_reason_code" in migration
    assert "add column if not exists affiliation_catalog_unresolved_reason_code" in migration
    assert "reason_tied_candidates" in migration
    assert "reason_no_live_client" in migration
    assert "reason_not_corroborated" in migration
    assert "reason_no_catalog_entry" in migration


def test_migrate_sh_replays_source_reference_research_on_existing_volumes() -> None:
    """Existing Compose volumes must receive source-research evidence tables."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(
        encoding="utf-8"
    )
    migration = (root / "migrations" / "0133_source_reference_research.sql").read_text(
        encoding="utf-8"
    )

    assert "0133_*" in script
    assert "post_source_research_lead" in migration


def test_migrate_sh_replays_post_ask_history_on_existing_volumes() -> None:
    """Compose must create per-post Ask history tables on every volume."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(encoding="utf-8")
    migration = (root / "migrations" / "0136_post_ask_conversation_history.sql").read_text(
        encoding="utf-8"
    )

    assert "0136_*" in script
    assert "create table if not exists post_ask_session" in migration
    assert "post_ask_session_account_post_idx" in migration


def test_migrate_sh_replays_cross_post_customer_identity_on_existing_volumes() -> None:
    """Existing Compose volumes must receive governed Customer Master tables."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(
        encoding="utf-8"
    )
    migration = (root / "migrations" / "0137_cross_post_customer_identity.sql").read_text(
        encoding="utf-8"
    )

    assert "0137_*" in script
    assert "customer_identity_judgment_response" in migration
    assert "UNIQUE NULLS NOT DISTINCT (source_system_code, source_customer_code)" in migration


def test_migrate_sh_replays_planned_facility_predicate_on_existing_volumes() -> None:
    """Existing relationship tables must accept the ADR 0142 predicate."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "docker" / "postgres-init" / "migrate.sh").read_text(
        encoding="utf-8"
    )
    migration = (
        root / "migrations" / "0138_planned_facility_relation_predicate.sql"
    ).read_text(encoding="utf-8")
    rollback = (
        root
        / "migrations"
        / "rollback"
        / "0138_planned_facility_relation_predicate.sql"
    ).read_text(encoding="utf-8")

    assert "0138_*" in script
    assert "'lw_plans_to_operate'" in migration
    assert "'lw_plans_to_operate'" not in rollback


def test_tenant_identity_migration_repairs_legacy_values_before_constraints() -> None:
    """Legacy blank settings cannot make an existing-volume replay fail closed."""
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0176_tenant_identity_metadata.sql"
    ).read_text(encoding="utf-8")

    repair_position = migration.index("update public.tenant_settings")
    constraint_position = migration.index("tenant_settings_brand_name_nonempty_check")
    assert repair_position < constraint_position
    assert "nullif(btrim(brand_name), '') is null then 'LineageWeave'" in migration
    assert "copyright_year not between 1900 and 2100" in migration
    assert "nullif(btrim(copyright_holder), '') is null then 'LineageWeave'" in migration
