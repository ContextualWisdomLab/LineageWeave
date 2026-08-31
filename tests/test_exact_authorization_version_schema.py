from pathlib import Path


MIGRATION = Path("migrations/0272_global_ask_exact_authorization_version.sql")


def test_exact_authorization_version_tracks_every_scope_authority() -> None:
    """Authorization snapshots must invalidate on every normalized authority."""
    sql = MIGRATION.read_text()

    assert "create table if not exists global_ask_exact_authorization_state" in sql
    assert "authorization_version = authorization_version + 1" in sql
    for relation in (
        "account_affiliation",
        "account_role_assignment",
        "role_permission",
        "process_unit",
        "source_post",
    ):
        assert f"on {relation}" in sql
    assert "after insert or update or delete or truncate" in sql
