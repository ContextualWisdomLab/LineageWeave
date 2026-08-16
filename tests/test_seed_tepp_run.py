"""Seeded TEPP analysis runs go through tepp_client, never a local model."""

from scripts.seed_demo_data import tepp_seed_outcome


def test_tepp_seed_outcome_is_unavailable_not_a_fake_score() -> None:
    status, failure = tepp_seed_outcome()
    assert status == "analysis_status_failed"
    assert failure == "tepp_not_available"
