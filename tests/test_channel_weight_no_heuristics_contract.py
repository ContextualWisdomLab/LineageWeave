"""Regression contract for evidence-only lineage channel-weight estimation."""

from pathlib import Path


def test_channel_weight_estimator_contains_no_repository_authored_decision_cutoffs() -> None:
    """Reject hand-selected sample, score-threshold, and optimizer budgets."""
    source = Path("lineageweave/channel_weight_estimation.py").read_text()

    assert "_MIN_SAMPLE_PAIRS" not in source
    assert "threshold: float = DEFAULT_MIN_FUSED_SCORE" not in source
    assert "max_iter=3000" not in source
    assert "observed up to ~1850" not in source


def test_channel_weight_operator_contains_no_default_sampling_budget() -> None:
    """Sampling extent must come from an identified design, never a CLI default."""
    source = Path("scripts/estimate_channel_weights.py").read_text()

    assert "default=5000" not in source
    assert "(default: 5000)" not in source


def test_unidentified_weight_design_fails_closed_instead_of_estimating() -> None:
    """The current owner has no validated production design, so estimation is unavailable."""
    source = Path("lineageweave/channel_weight_estimation.py").read_text()

    assert "ChannelWeightEstimationUnavailable" in source
    assert "validated production channel-weight measurement design is unavailable" in source
