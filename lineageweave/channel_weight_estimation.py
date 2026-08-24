"""Psychometric estimation of lineage channel-fusion weights (ADR 0145).

The convex weights `reconstruct()` fuses its evidence channels with were
historically hand-picked constants. This module replaces assertion with
estimation: each channel is treated as an *item* observing the latent
trait "these two posts are genuinely related", each scored candidate
pair as a *respondent*, and the pair's reconstruction group as the
multilevel nesting factor (Robinson, 1950, on why pooling nested
observations atomistically misleads). Under the two-parameter logistic
model the information-optimal scoring weight of an item is proportional
to its discrimination (Birnbaum, 1968; Lord, 1980), so the estimated
weights are the normalized natural-scale discriminations from
`fast-mlsirm`'s multilevel 2PL (`MLS2PLM`), whose ``MLSIRMParams.alpha``
holds per-item log-discriminations.

Fail-closed like every optional capability in this codebase: when
`fast_mlsirm` is not importable, the sample is too small, any channel is
degenerate (fewer than two distinct dichotomized responses), or the fit
produces a non-finite estimate, :func:`estimate_channel_weights` returns
``None`` and the caller keeps the documented fallback constants -- it
never fabricates a "grounded" weight.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .reconstruct import DEFAULT_MIN_FUSED_SCORE

# Below this many scored pairs a 2PL discrimination estimate is noise,
# not measurement -- refuse rather than persist an unstable weight.
_MIN_SAMPLE_PAIRS = 200

# The library demo's declared generative design (fixtures.sample_records,
# `make seed`, the standalone demo server): per-channel follow
# probabilities of the latent "genuinely related" trait, per-group
# relatedness base rates, and a fixed simulation seed. These are the
# demo scenario's TRUE parameters -- synthetic demo data, never fusion
# weights. The weights the demo fuses with are ESTIMATED from this
# design by fast-mlsirm, exactly like production weights are estimated
# from the real corpus (ADR 0145, second amendment: no hand-picked
# fusion weight exists anywhere, demo included).
_FIXTURE_FOLLOW_PROBABILITY = {"temporal": 0.85, "secondary_key": 0.70, "text": 0.55}
_FIXTURE_GROUP_COUNT = 12
_FIXTURE_PAIR_COUNT = 900
_FIXTURE_SIMULATION_SEED = 20260824


def simulate_fixture_pair_scores() -> tuple[list[dict[str, float]], list[int]]:
    """Simulate the demo design's channel responses, deterministically.

    Each simulated pair carries a latent related/unrelated state drawn
    from its group's base rate (genuine cluster intercept variance --
    the structure MLS2PLM's multilevel random intercept models); each
    channel then reports a high or low score according to its declared
    follow probability. The fixed seed keeps every ``make seed`` and
    demo-server estimate identical run to run.
    """
    generator = random.Random(_FIXTURE_SIMULATION_SEED)

    def channel_score(related: bool, follow_probability: float) -> float:
        follows = generator.random() < follow_probability
        high = related if follows else not related
        return (0.8 if high else 0.05) + generator.uniform(-0.04, 0.04)

    group_base_rate = [
        generator.uniform(0.25, 0.75) for _ in range(_FIXTURE_GROUP_COUNT)
    ]
    pair_scores: list[dict[str, float]] = []
    group_ids: list[int] = []
    for index in range(_FIXTURE_PAIR_COUNT):
        group = index % _FIXTURE_GROUP_COUNT
        related = generator.random() < group_base_rate[group]
        pair_scores.append(
            {
                channel: channel_score(related, follow_probability)
                for channel, follow_probability in _FIXTURE_FOLLOW_PROBABILITY.items()
            }
        )
        group_ids.append(group)
    return pair_scores, group_ids


def estimate_fixture_channel_weights() -> ChannelWeightEstimate | None:
    """Estimate the demo's deterministic-channel weights from its design.

    Returns ``None`` when no grounded estimate can be produced (most
    commonly: ``fast_mlsirm`` is not importable); demo callers then fail
    closed -- the seed and the standalone server refuse to fuse with
    invented weights and instead name the next action (install
    fast-mlsirm from the organization repo).
    """
    pair_scores, group_ids = simulate_fixture_pair_scores()
    return estimate_channel_weights(pair_scores, group_ids)


@dataclass(frozen=True)
class ChannelWeightEstimate:
    """One estimation run's convex weights plus its provenance."""

    weights: dict[str, float]
    sample_pair_count: int
    estimation_method_code: str


def dichotomize(score: float, threshold: float = DEFAULT_MIN_FUSED_SCORE) -> int:
    """Binary "evidence of a link" event at the fusion floor.

    `reconstruct` already treats ``DEFAULT_MIN_FUSED_SCORE`` as the
    boundary between a plausible parent and no candidate at all, so the
    measurement model observes the same event the fusion decision acts
    on (ADR 0145 point 2).
    """
    return 1 if score >= threshold else 0


def estimate_channel_weights(
    pair_channel_scores: list[dict[str, float]],
    group_ids: list[int],
) -> ChannelWeightEstimate | None:
    """Estimate convex fusion weights from observed channel scores.

    Args:
        pair_channel_scores: one dict per candidate pair mapping every
            active channel name to its score in [0, 1]. Every dict must
            carry the same channel set -- a pair missing a channel is a
            caller bug, not missing data to impute.
        group_ids: the reconstruction-group index of each pair (same
            length/order), used as MLS2PLM's multilevel ``cluster_id``.

    Returns:
        The estimate, or ``None`` whenever a grounded estimate cannot be
        produced (fail closed -- see module docstring for the cases).
    """
    if len(pair_channel_scores) != len(group_ids):
        raise ValueError("pair_channel_scores and group_ids must align")
    if len(pair_channel_scores) < _MIN_SAMPLE_PAIRS:
        return None
    channels = sorted(pair_channel_scores[0])
    if not channels:
        return None
    for scores in pair_channel_scores:
        if sorted(scores) != channels:
            raise ValueError("every pair must score the same channel set")

    responses = [
        [dichotomize(scores[channel]) for channel in channels]
        for scores in pair_channel_scores
    ]
    for column, channel in enumerate(channels):
        observed = {row[column] for row in responses}
        if len(observed) < 2:
            # A channel that always (or never) clears the floor carries no
            # discriminating information; a 2PL slope for it is undefined
            # in practice. Refuse rather than estimate around it.
            return None

    try:
        import numpy
        from fast_mlsirm import FitConfig, fit
    except ImportError:
        return None

    # One latent "relatedness" trait loads every channel (factor_id maps
    # items to latent dimensions); pairs are nested in reconstruction
    # groups via cluster_id -- fast-mlsirm's multilevel random-intercept
    # structure (Fox & Glas, 2001), which requires the marginal (mmle)
    # estimator.
    result = fit(
        responses=numpy.asarray(responses, dtype=float),
        factor_id=numpy.zeros(len(channels), dtype=numpy.int64),
        cluster_id=numpy.asarray(group_ids, dtype=numpy.int64),
        config=FitConfig(model="MLS2PLM", latent_dim=1, estimator="mmle"),
    )
    log_discriminations = list(numpy.asarray(result.params.alpha, dtype=float).ravel())
    if len(log_discriminations) != len(channels):
        return None
    if any(not math.isfinite(alpha) for alpha in log_discriminations):
        return None

    # exp(alpha) is the natural-scale discrimination -- positive by
    # construction, so the normalization always yields valid convex
    # weights (Birnbaum, 1968: optimal weight proportional to a_j).
    discriminations = [math.exp(alpha) for alpha in log_discriminations]
    total = sum(discriminations)
    if not math.isfinite(total) or total <= 0:
        return None
    return ChannelWeightEstimate(
        weights={
            channel: discrimination / total
            for channel, discrimination in zip(channels, discriminations)
        },
        sample_pair_count=len(pair_channel_scores),
        estimation_method_code="mls2plm_discrimination",
    )
