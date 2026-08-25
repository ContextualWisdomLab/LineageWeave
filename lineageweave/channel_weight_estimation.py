"""Psychometric estimation of lineage channel-fusion weights (ADR 0200).

The convex weights `reconstruct()` fuses its evidence channels with were
historically hand-picked constants. This module replaces assertion with
estimation: each channel is treated as an *item* observing the latent
trait "these two posts are genuinely related", each scored candidate
pair as a *respondent*, and the pair's reconstruction group as the
multilevel nesting factor (Robinson, 1950, on why pooling nested
observations atomistically misleads; Fox & Glas, 2001, for the
multilevel IRT structure).

Because Birnbaum's item information is conditional on trait location --
``I_j(theta) = a_j^2 P_j(theta) Q_j(theta)`` (Birnbaum, 1968; Lord,
1980) -- a weight proportional to the discrimination alone is not a
global information-optimal rule. The fusion weight here is therefore
the normalized EXPECTED item information over the fitted latent
distribution, approximated on the fitted person parameters with the
package's own item response function (van der Linden, 2005, on
expected/target information as the design quantity). Estimates carry
the ``mls2plm_expected_information`` method code; activation
additionally requires an authorized anchor method (ADR 0200 point 3)
enforced by the product loader, not here.

Fail-closed like every optional capability in this codebase: when
`fast_mlsirm` is not importable, the sample is too small, any channel is
degenerate (fewer than two distinct dichotomized responses), the fit
does not converge, or any estimate is non-finite,
:func:`estimate_channel_weights` returns ``None`` and the caller fails
closed -- product paths refuse to reconstruct, the demo refuses to fuse
-- it never fabricates a "grounded" weight.
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
# from the real corpus (ADR 0200: no hand-picked
# fusion weight exists anywhere, demo included).
_FIXTURE_FOLLOW_PROBABILITY = {"temporal": 0.80, "secondary_key": 0.72, "text": 0.66}
_FIXTURE_GROUP_COUNT = 12
_FIXTURE_PAIR_COUNT = 900
_FIXTURE_SIMULATION_SEED = 20260824


def fixture_design_digest() -> str:
    """Reproducible SHA-256 of the demo's declared generative design.

    Plays the role the corpus snapshot digest plays for production
    estimates: the provenance row names exactly which design supported
    the demo estimate. Deterministic by construction.
    """
    import hashlib

    material = "\n".join(
        [
            *(
                f"{channel}\t{probability}"
                for channel, probability in sorted(_FIXTURE_FOLLOW_PROBABILITY.items())
            ),
            f"groups\t{_FIXTURE_GROUP_COUNT}",
            f"pairs\t{_FIXTURE_PAIR_COUNT}",
            f"seed\t{_FIXTURE_SIMULATION_SEED}",
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


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
        """One channel's noisy report of the pair's latent related state."""
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
    on (the dichotomization rule both lines' ADR 0145 texts share,
    carried forward by ADR 0200).
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
    distinct_columns = {
        tuple(row[column] for row in responses) for column in range(len(channels))
    }
    if len(distinct_columns) != len(channels):
        # Identical channels are one signal copied twice, not independent
        # measurement evidence. Refuse instead of double-counting it.
        return None
    for column, channel in enumerate(channels):
        observed = {row[column] for row in responses}
        if len(observed) < 2:
            # A channel that always (or never) clears the floor carries no
            # discriminating information; a 2PL slope for it is undefined
            # in practice. Refuse rather than estimate around it.
            return None

    try:
        import numpy
        from fast_mlsirm import FitConfig, fit, predict_proba
    except ImportError:
        return None

    # One latent "relatedness" trait loads every channel (factor_id maps
    # items to latent dimensions); pairs are nested in reconstruction
    # groups via cluster_id -- fast-mlsirm's multilevel random-intercept
    # structure (Fox & Glas, 2001), which requires the marginal (mmle)
    # estimator.
    factor_id = numpy.zeros(len(channels), dtype=numpy.int64)
    result = fit(
        responses=numpy.asarray(responses, dtype=float),
        factor_id=factor_id,
        cluster_id=numpy.asarray(group_ids, dtype=numpy.int64),
        # fast-mlsirm's default max_iter=1000 is tuned against its GPU/f32
        # path; the f64 CPU fallback (no wgpu adapter -- every CI runner)
        # needs materially more EM iterations to reach the same optimum at
        # full precision, observed up to ~1850 on this module's own fixture.
        # Raising the budget only slows an already-non-converged path; a
        # fit that would converge sooner still stops the moment it does.
        config=FitConfig(model="MLS2PLM", latent_dim=1, estimator="mmle", max_iter=3000),
    )
    # ADR 0200: a non-converged fit is rejected outright -- its point
    # estimates are not measurement evidence.
    if result.convergence_status != "converged":
        return None
    discriminations = numpy.asarray(result.params.a, dtype=float).ravel()
    if len(discriminations) != len(channels):
        return None
    if not numpy.all(numpy.isfinite(discriminations)):
        return None

    # ADR 0200 point 2: Birnbaum item information is conditional,
    # I_j(theta) = a_j^2 P_j(theta) Q_j(theta) -- so the fusion weight is
    # the normalized EXPECTED information over the fitted latent
    # distribution, approximated by averaging over the fitted person
    # parameters (the empirical distribution the multilevel model
    # produced), using the package's own item response function
    # (predict_proba) rather than a re-derived one (van der Linden,
    # 2005, on expected/target information as the design quantity).
    probabilities = numpy.asarray(predict_proba(result.params, factor_id), dtype=float)
    if probabilities.shape[1] != len(channels):
        return None
    information = (discriminations**2) * probabilities * (1.0 - probabilities)
    expected_information = information.mean(axis=0)
    if not numpy.all(numpy.isfinite(expected_information)):
        return None
    total = float(expected_information.sum())
    if not math.isfinite(total) or total <= 0:
        return None
    return ChannelWeightEstimate(
        weights={
            channel: float(value) / total
            for channel, value in zip(channels, expected_information)
        },
        sample_pair_count=len(pair_channel_scores),
        estimation_method_code="mls2plm_expected_information",
    )
