"""Project-history indexes are reversible and cover every exact match key."""

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = _ROOT / "migrations" / "0046_project_history_lookup.sql"
_ROLLBACK = _ROOT / "migrations" / "rollback" / "0046_project_history_lookup.sql"


def test_project_history_migration_indexes_explicit_and_semantic_keys() -> None:
    """Every exact project-identity read has a normalized lookup index."""

    sql = _MIGRATION.read_text(encoding="utf-8")
    assert "source_post_project_code_history_idx" in sql
    assert "source_post_project_name_history_idx" in sql
    assert "post_project_mention_key_history_idx" in sql
    assert "post_project_mention_name_history_idx" in sql
    assert "post_lineage_edge_child_history_idx" in sql
    assert sql.count("normalize(") >= 4


def test_project_history_migration_has_a_complete_idempotent_rollback() -> None:
    """The additive index migration can be rolled back without guessing."""

    sql = _ROLLBACK.read_text(encoding="utf-8").lower()
    for index_name in (
        "post_lineage_edge_child_history_idx",
        "post_project_mention_name_history_idx",
        "post_project_mention_key_history_idx",
        "source_post_project_name_history_idx",
        "source_post_project_code_history_idx",
    ):
        assert f"drop index if exists {index_name}" in sql
