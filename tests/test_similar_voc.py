"""Contracts for cited similar-VOC inference and measured ranking."""

import json

from lineageweave.similar_voc import parse_similar_voc_response


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


def test_customer_cohort_must_be_extractable() -> None:
    """A customer cohort label must be the same extractive span in both bodies."""
    focal = "Customer cohort Alpha reported a seal failure."
    candidate = "A seal failure occurred during trial."
    payload = {
        "similar": True,
        "issue_summary": "Equivalent seal failure",
        "focal_evidence_text": focal,
        "candidate_evidence_text": candidate,
        "customer_cohort_text": "invented cohort",
        "action_history": [],
    }
    assert parse_similar_voc_response(json.dumps(payload), "post-2", focal, candidate) is None
    payload["customer_cohort_text"] = "Customer cohort Alpha"
    assert parse_similar_voc_response(json.dumps(payload), "post-2", focal, candidate) is None
    candidate = "Customer cohort Alpha reported a seal failure during trial."
    payload["candidate_evidence_text"] = candidate
    assert parse_similar_voc_response(json.dumps(payload), "post-2", focal, candidate) is not None
