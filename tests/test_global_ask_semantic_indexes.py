from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / "migrations/0054_global_ask_semantic_search.sql"
ROLLBACK = ROOT / "migrations/rollback/0054_global_ask_semantic_search.sql"


EXPECTED_INDEXES = (
    "post_project_mention_name_search_idx",
    "post_project_mention_evidence_search_idx",
    "post_project_mention_ontology_search_idx",
    "post_summary_role_actor_search_idx",
    "post_summary_role_responsibility_search_idx",
    "post_summary_role_affiliation_search_idx",
    "post_person_mention_context_search_idx",
    "cataloged_person_name_search_idx",
    "cataloged_person_title_search_idx",
    "corporate_entity_name_search_idx",
    "cataloged_team_name_search_idx",
    "cataloged_team_affiliation_search_idx",
)


def test_semantic_search_migration_has_multilingual_trigram_indexes_and_rollback() -> None:
    """Contains-search fields have explicit indexes rather than expression scans."""
    forward = FORWARD.read_text(encoding="utf-8")
    rollback = ROLLBACK.read_text(encoding="utf-8")

    assert 'create extension if not exists pg_trgm' in forward.casefold()
    for index_name in EXPECTED_INDEXES:
        assert f"create index if not exists {index_name}" in forward.casefold()
        assert "using gin" in forward.casefold()
        assert "gin_trgm_ops" in forward.casefold()
        assert f"drop index if exists {index_name}" in rollback.casefold()

    # The extension may be shared by other features and is never dropped here.
    assert "drop extension" not in rollback.casefold()


def test_migration_runner_includes_the_semantic_search_slice() -> None:
    """Long-lived Compose databases apply the same index contract as fresh installs."""
    migrate = (ROOT / "docker/postgres-init/migrate.sh").read_text(encoding="utf-8")
    assert "0054_*" in migrate
