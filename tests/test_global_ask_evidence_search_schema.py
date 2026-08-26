"""Schema contract for index-backed Global Ask evidence nomination."""

from pathlib import Path

MIGRATION = Path("migrations/0210_global_ask_evidence_search_indexes.sql")
ROLLBACK = Path("migrations/rollback/0210_global_ask_evidence_search_indexes.sql")


def test_evidence_search_indexes_cover_every_normalized_owner_table() -> None:
    """Every searched evidence field has a replay-safe owning-table index."""
    sql = MIGRATION.read_text(encoding="utf-8")
    for table_name in (
        "post_project_mention",
        "post_summary_role",
        "cataloged_person",
        "person_affiliation",
        "corporate_entity",
        "cataloged_team",
        "source_post",
        "common_lookup_value",
        "knowledge_graph_edge",
    ):
        assert f"on {table_name}" in sql
    assert sql.count("create index concurrently if not exists") == 9
    assert "create table" not in sql.lower()


def test_evidence_search_indexes_have_a_replay_safe_rollback() -> None:
    """Operators can remove only this migration's indexes by exact name."""
    forward = MIGRATION.read_text(encoding="utf-8")
    rollback = ROLLBACK.read_text(encoding="utf-8")
    index_names = [
        line.split()[6]
        for line in forward.splitlines()
        if line.startswith("create index concurrently if not exists ")
    ]

    assert len(index_names) == 9
    for index_name in index_names:
        assert f"drop index concurrently if exists {index_name};" in rollback
