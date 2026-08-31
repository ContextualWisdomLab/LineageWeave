"""Static contracts for the ADR 0272 Post-search read projection."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRIGGER_RELEVANCE = ROOT / "migrations" / "0270_post_search_trigger_relevance.sql"
POST_LIST_PROJECTION = ROOT / "migrations" / "0265_post_list_read_projection_index.sql"
DASHBOARD_PROJECTION = ROOT / "migrations" / "0264_dashboard_post_read_projection.sql"
MASTER_GROUP_PROJECTION = ROOT / "migrations" / "0266_customer_master_group_read_projection.sql"


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


def test_large_read_projection_backfills_do_not_rewrite_on_replay() -> None:
    """Compose startup must preserve trigger-maintained projections on replay."""
    dashboard_sql = " ".join(
        DASHBOARD_PROJECTION.read_text(encoding="utf-8").lower().split()
    )
    master_sql = " ".join(
        MASTER_GROUP_PROJECTION.read_text(encoding="utf-8").lower().split()
    )

    dashboard_backfill = dashboard_sql.split(
        "insert into dashboard_post_read_projection", maxsplit=2
    )[2]
    assert "on conflict (source_post_id) do nothing" in dashboard_backfill
    assert "truncate dashboard_post_daily_summary" not in dashboard_sql
    assert "where not exists ( select 1 from dashboard_case_rollup_read_projection" in dashboard_sql
    assert "truncate customer_master_post_read_projection" not in master_sql
    assert "if not exists (select 1 from customer_master_post_read_projection) then" in master_sql
