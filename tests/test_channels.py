from __future__ import annotations

from datetime import datetime, timedelta

from lineageweave.channels import secondary_key_match_score, temporal_score, text_similarity_score
from lineageweave.models import Record

_T0 = datetime(2026, 1, 1)


def _record(record_id: str, label: str, offset_days: int = 0, secondary_key: str = "") -> Record:
    return Record(record_id, "G", label, _T0 + timedelta(days=offset_days), secondary_key)


def test_temporal_score_prefers_closer_pairs() -> None:
    record = _record("child", "x", offset_days=10)
    close = temporal_score(_record("near", "x", offset_days=9), record)
    far = temporal_score(_record("far", "x", offset_days=0), record)
    assert close > far


def test_temporal_score_never_negative_for_same_or_reversed_time() -> None:
    record = _record("child", "x", offset_days=0)
    later_candidate = _record("later", "x", offset_days=5)
    assert temporal_score(record, record) == 1.0
    assert temporal_score(later_candidate, record) == 1.0  # clamped, never negative/undefined


def test_secondary_key_match_requires_both_sides_non_empty() -> None:
    a = _record("a", "x", secondary_key="proj-1")
    b = _record("b", "x", secondary_key="proj-1")
    c = _record("c", "x", secondary_key="")

    assert secondary_key_match_score(a, b) == 1.0
    assert secondary_key_match_score(a, c) == 0.0
    assert secondary_key_match_score(c, c) == 0.0


def test_text_similarity_scores_identical_text_as_one() -> None:
    a = _record("a", "pricing renegotiation follow-up")
    b = _record("b", "pricing renegotiation follow-up")
    c = _record("c", "unrelated annual account review")

    assert text_similarity_score(a, b) == 1.0
    assert text_similarity_score(a, c) < text_similarity_score(a, b)
