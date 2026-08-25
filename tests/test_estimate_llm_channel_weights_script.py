"""Tests for scripts/estimate_llm_channel_weights.py (ADR 0200 point 5).

The queued judging flow must never make bulk synchronous provider calls
(one batch submission is the only provider interaction in ``submit``),
must map results to pairs by caller-supplied ``custom_id`` only (never
result order), and must fit exclusively over a complete run.
"""

from __future__ import annotations

import pytest

from lineageweave.adjudication_client import judge_prompt, parse_confidence
from lineageweave.http_client import HttpClientError

import scripts.estimate_llm_channel_weights as script


def test_batch_requests_carry_caller_custom_ids_for_every_pair() -> None:
    labels = [("a", "b"), ("c", "d"), ("e", "f")]
    requests = script.batch_requests_for_pairs([0, 2], labels)
    assert [request["custom_id"] for request in requests] == ["pair-0", "pair-2"]
    # Never mix caller ids with generated ids in one batch (upstream
    # guidance on contextual-orchestrator #832): every request has one.
    assert all("custom_id" in request for request in requests)
    assert requests[0]["messages"][0]["content"] == judge_prompt("a", "b")
    assert requests[1]["messages"][0]["content"] == judge_prompt("e", "f")
    assert all(request["mode"] == "auto" for request in requests)


def test_shared_judge_prompt_and_confidence_parse_round_trip() -> None:
    prompt = judge_prompt("Record about pricing", "Follow-up record")
    assert "Record A: Record about pricing" in prompt
    assert "Record B: Follow-up record" in prompt
    assert parse_confidence("0.85") == 0.85
    assert parse_confidence("confidence: 0.4 maybe") == 0.4
    with pytest.raises(HttpClientError):
        parse_confidence("no number here")
    assert parse_confidence("1.7") == 1.0


def test_errored_judgments_stay_unjudged_instead_of_becoming_zero() -> None:
    """An empty or non-numeric answer must never persist as a confident
    0.0 -- the pair stays unjudged and the incomplete-run path reports it.
    Mapping is by custom_id only; foreign or malformed ids are ignored.
    """
    updates = script.judgment_updates_from_results(
        [
            {"custom_id": "pair-3", "answer": "0.7"},
            {"custom_id": "pair-4", "answer": ""},
            {"custom_id": "pair-5", "answer": "provider error: upstream unavailable"},
            {"custom_id": "pair-6", "answer": "0.0"},
            {"custom_id": "req_generated9", "answer": "0.9"},
            {"custom_id": "pair-not-a-number", "answer": "0.9"},
        ]
    )
    assert updates == [(3, 0.7), (6, 0.0)]


def test_batch_completion_is_detected_from_flag_or_status() -> None:
    assert script._is_complete({"is_complete": True})
    assert script._is_complete({"status": "completed"})
    assert script._is_complete({"status": "Succeeded"})
    assert not script._is_complete({"status": "in_progress"})
    assert not script._is_complete({})
