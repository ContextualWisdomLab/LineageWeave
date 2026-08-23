"""Fail-closed lineage channel-weight boundary (ADR 0145).

Channel-score covariance is not an independent lineage anchor. Until an
accepted upstream anchor contract exists, this module produces no estimate.
"""

from __future__ import annotations


def estimate_channel_weights(
    pair_channel_scores: list[dict[str, float]],
    group_ids: list[int],
) -> None:
    """Report unavailable for unanchored channel scores.

    Args:
        pair_channel_scores: unanchored candidate-pair channel scores.
        group_ids: corresponding reconstruction-group indexes.

    Returns:
        Always ``None`` until ADR 0145's independent-anchor requirement is met.
    """
    if len(pair_channel_scores) != len(group_ids):
        raise ValueError("pair_channel_scores and group_ids must align")
    return None
