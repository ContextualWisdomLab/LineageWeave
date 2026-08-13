"""Tests for lineageweave.post_summary.

parse_summary_response's tests need no live provider. The real-provider
test reuses fixtures.ambiguous_keyman_post -- it already has multiple
people, an implied timeline (a bid workshop, a follow-up, "last quarter"),
and an ambiguous responsibility (Priya's dual role is what made the
warranty language messy), which is exactly the "non-trivial" shape Phase
4's stop condition calls for.
"""

from __future__ import annotations

import os

import pytest

from backend.app.post_summary_ingestion import seeded_fixture_summary
from lineageweave.fixtures import ambiguous_commitment_post, ambiguous_keyman_post, sample_records
from lineageweave.post_summary import (
    ContextualOrchestratorPostSummaryClient,
    NullPostSummaryClient,
    parse_summary_response,
)


def test_null_summary_client_is_unavailable_not_empty_summary() -> None:
    client = NullPostSummaryClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.summarize("any title", "any body")


def test_parses_a_well_formed_json_object() -> None:
    content = (
        '{"korean_summary": "회의 후속 조치에 대한 요약입니다.", '
        '"key_events": ["입찰 워크숍 진행", "검사 일정 확인 요청"], '
        '"roles_and_responsibilities": [{"person_name": "Jordan Hale", "responsibility": "입찰 일정 안내"}]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    assert summary.korean_summary == "회의 후속 조치에 대한 요약입니다."
    assert summary.key_events == ("입찰 워크숍 진행", "검사 일정 확인 요청")
    assert summary.roles_and_responsibilities[0].person_name == "Jordan Hale"


def test_missing_korean_summary_returns_none() -> None:
    content = '{"key_events": [], "roles_and_responsibilities": []}'
    assert parse_summary_response(content) is None


def test_empty_korean_summary_returns_none() -> None:
    content = '{"korean_summary": "   ", "key_events": [], "roles_and_responsibilities": []}'
    assert parse_summary_response(content) is None


def test_invalid_json_returns_none() -> None:
    assert parse_summary_response("not json") is None


def test_every_sample_record_has_a_seeded_korean_summary() -> None:
    """Event Lineage click-through must have a stored Korean summary for
    every reconstruct fixture -- not a shared placeholder, not English.
    """
    seen: set[str] = set()
    for rec in sample_records():
        summary = seeded_fixture_summary(rec.label)
        assert summary is not None, rec.label
        assert any("가" <= ch <= "힣" for ch in summary.korean_summary)
        assert summary.key_events
        assert summary.korean_summary not in seen
        seen.add(summary.korean_summary)
    calendar_title, _ = ambiguous_commitment_post()
    calendar = seeded_fixture_summary(calendar_title)
    assert calendar is not None
    assert "리버벤드" in calendar.korean_summary
    assert seeded_fixture_summary("not a fixture title") is None


def test_malformed_roles_entries_are_skipped_not_crashed_on() -> None:
    content = (
        '{"korean_summary": "요약", "key_events": [], '
        '"roles_and_responsibilities": [{"person_name": "Only Name"}, "not an object"]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    assert summary.roles_and_responsibilities == ()


_ORCHESTRATOR_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL")
_ORCHESTRATOR_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY")


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_contextual_orchestrator_summarizes_a_non_trivial_post() -> None:
    client = ContextualOrchestratorPostSummaryClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY
    )
    title, body = ambiguous_keyman_post()

    summary = client.summarize(title, body)

    assert summary.korean_summary.strip() != ""
    # A genuine Korean summary should contain at least one Hangul syllable
    # block -- not just an English sentence handed back unchanged.
    assert any("가" <= ch <= "힣" for ch in summary.korean_summary)
    assert len(summary.key_events) >= 1
    people_named = {rr.person_name for rr in summary.roles_and_responsibilities}
    assert any("Jordan" in name or "Priya" in name for name in people_named)
