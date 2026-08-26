"""Static contracts for the normalized O*NET rating observation store."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "0222_onet_rating_observation_store.sql"


def test_migration_declares_normalized_partitioned_observation_contract() -> None:
    assert MIGRATION.is_file()
    sql = MIGRATION.read_text(encoding="utf-8").casefold()
    for table_name in (
        "occupational_data_release",
        "occupational_source_table",
        "occupational_scale_definition",
        "occupational_classification_entry",
        "occupational_element_definition",
        "occupational_rating_observation",
    ):
        assert f"create table if not exists {table_name}" in sql
    assert "partition by list (data_release_code)" in sql
    assert "unique nulls not distinct" in sql
    assert "occupational_scale_source_table_fkey" in sql
    assert "recommend_suppress" in sql
    assert "not_relevant" in sql
    assert "standard_error" in sql
    assert "lower_ci_bound" in sql
    assert "upper_ci_bound" in sql
