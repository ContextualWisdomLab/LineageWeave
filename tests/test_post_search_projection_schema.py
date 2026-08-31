"""Static contracts for the ADR 0272 Post-search read projection."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRIGGER_RELEVANCE = ROOT / "migrations" / "0270_post_search_trigger_relevance.sql"
POST_LIST_PROJECTION = ROOT / "migrations" / "0265_post_list_read_projection_index.sql"


def test_member_preferences_do_not_refresh_authored_post_search_rows() -> None:
    """Only user fields represented in search text may fire its refresh trigger."""
    sql = " ".join(TRIGGER_RELEVANCE.read_text(encoding="utf-8").lower().split())

    assert "drop trigger if exists post_search_related_master_reconcile on user_account" in sql
    assert "after insert or delete or update of display_name, email_address" in sql
    assert "preferred_locale" not in sql


def test_post_list_projection_replay_backfills_only_missing_rows() -> None:
    """Startup replay must not rewrite projections already maintained by triggers."""
    sql = " ".join(POST_LIST_PROJECTION.read_text(encoding="utf-8").lower().split())

    backfill = sql.rsplit("insert into post_list_read_projection", maxsplit=1)[1]
    assert "on conflict (post_id) do nothing" in backfill
    assert "do update" not in backfill
