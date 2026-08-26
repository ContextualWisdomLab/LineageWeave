"""Replay-safe schema contract for source-research citations."""

from pathlib import Path

MIGRATION = Path("migrations/0236_source_research_citation.sql")
ROLLBACK = Path("migrations/rollback/0236_source_research_citation.sql")


def test_source_research_citation_is_third_normal_form_and_replay_safe() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "create table if not exists source_research_citation" in sql
    assert "lead_source_unit_id" in sql
    assert "lead_image_region_id" in sql
    assert "lead_excerpt_text" in sql
    assert "search_query_text" in sql
    assert "evidence_url" in sql
    assert "judgment_code" in sql
    assert "next_action_text" in sql
    assert "on conflict (lookup_code) do nothing" in sql
    assert "research_lead_semantic_unit" in sql
    assert "research_lead_image_region" in sql
    assert "research_supported" in sql
    assert "research_unavailable" in sql
    assert "create unique index if not exists source_research_citation_unit_uidx" in sql
    assert "create unique index if not exists source_research_citation_region_uidx" in sql
    assert "source_research_citation_lead_kind_check" in sql


def test_source_research_citation_rollback_drops_only_this_table() -> None:
    rollback = ROLLBACK.read_text(encoding="utf-8")
    assert "drop table if exists source_research_citation;" in rollback
    assert "drop index if exists source_research_citation_unit_uidx;" in rollback
    assert "research_lead_semantic_unit" in rollback
