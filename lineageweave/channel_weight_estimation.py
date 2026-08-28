"""Fail-closed Lineage channel-weight boundary (ADR 0145 / ADR 0208).

The protected fast-mlsirm contract validates independently anchored evidence,
but does not yet fit or normalize weights. LineageWeave therefore exposes no
local simulation, dichotomization, or Python/NumPy estimator. Callers receive
``None`` until a fitted Rust owner artifact is available and accepted.
"""

from __future__ import annotations


def estimate_channel_weights(
    pair_channel_scores: list[dict[str, float]],
    group_ids: list[int],
) -> None:
    """Refuse local estimation while preserving caller-shape validation."""
    if len(pair_channel_scores) != len(group_ids):
        raise ValueError("pair_channel_scores and group_ids must align")
    if pair_channel_scores:
        channels = sorted(pair_channel_scores[0])
        if any(sorted(scores) != channels for scores in pair_channel_scores):
            raise ValueError("every pair must score the same channel set")
    return None


def estimate_fixture_channel_weights() -> None:
    """Refuse the retired arbitrary synthetic-weight simulation."""
    return None
