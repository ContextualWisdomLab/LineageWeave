from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_selected_topic_context_ranking_contract() -> None:
    adr = (ROOT / "docs/adr/0278-selected-topic-context-rankings.md").read_text()
    sql = (ROOT / "migrations/0268_selected_topic_context_ranking_access.sql").read_text()
    for field in (
        "topic_model_run_id", "topic_influence_run_id", "topic_index",
        "dimension_code", "context_id",
    ):
        assert field in adr
    lowered = (adr + sql).lower()
    assert "no keyword" in lowered
    assert "renormalized" in lowered
    assert "drop trigger" not in lowered
    assert "topic_context_membership_selected_ranking_idx" in sql
    assert "topic_influence_selected_ranking_idx" in sql
