"""Contracts for cited similar-VOC inference and measured ranking."""

import json

import pytest

from lineageweave.rankweave_client import RankWeaveClient
from lineageweave.similar_voc import parse_similar_voc_response, rank_similar_voc_candidates


def test_positive_similarity_requires_extractable_evidence() -> None:
    """A positive relation retains focal, candidate, cohort, and action evidence."""
    focal = "A seal failed during acceptance."
    candidate = "A seal failed during trial. Replaced the gasket and verified pressure."
    payload = {
        "similar": True, "issue_summary": "Equivalent seal failure",
        "focal_evidence_text": "A seal failed during acceptance.",
        "candidate_evidence_text": "A seal failed during trial.",
        "customer_cohort_text": None,
        "action_history": ["Replaced the gasket and verified pressure."],
    }
    result = parse_similar_voc_response(json.dumps(payload), "post-2", focal, candidate)
    assert result is not None
    assert result.candidate_post_id == "post-2"
    assert result.action_history == ("Replaced the gasket and verified pressure.",)
    payload["candidate_evidence_text"] = "invented"
    assert parse_similar_voc_response(json.dumps(payload), "post-2", focal, candidate) is None


def test_ranking_uses_only_complete_supplied_measurement_weights() -> None:
    """RankWeave receives the exact persisted estimate and rejects a partial vector."""
    captured = {}

    def transport(channels, weights):
        captured.update(weights)
        return [{"item_id": "post-2"}]

    ranking = rank_similar_voc_candidates(
        {"text": ["post-2"], "secondary_key": ["post-2"]}, {"post-2": "Prior VOC"},
        {"text": 0.7, "secondary_key": 0.3}, RankWeaveClient(transport=transport),
    )
    assert captured == {"text": 0.7, "secondary_key": 0.3}
    assert ranking.items[0].post_id == "post-2"
    with pytest.raises(ValueError, match="complete estimated"):
        rank_similar_voc_candidates(
            {"text": ["post-2"], "secondary_key": ["post-2"]}, {"post-2": "Prior VOC"},
            {"text": 1.0}, RankWeaveClient(transport=transport),
        )
