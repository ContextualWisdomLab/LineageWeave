"""Tests for lineageweave.channel_weight_estimation (ADR 0145).

The fail-closed paths run everywhere. The parameter-recovery test --
the organization's standard for measurement code (planted true
parameters recovered by the estimate) -- runs when `fast_mlsirm` is
importable and skips honestly otherwise, same as this repo's
live-service skips.
"""

from __future__ import annotations

import importlib.util
import math
import random

import pytest

from lineageweave.channel_weight_estimation import (
    _MIN_SAMPLE_PAIRS,
    dichotomize,
    estimate_channel_weights,
    estimate_fixture_channel_weights,
    simulate_fixture_pair_scores,
)
from lineageweave.models import Record
from lineageweave.reconstruct import DEFAULT_MIN_FUSED_SCORE

_FAST_MLSIRM_AVAILABLE = importlib.util.find_spec("fast_mlsirm") is not None


def test_dichotomize_uses_the_fusion_floor_as_the_link_event_boundary() -> None:
    assert dichotomize(DEFAULT_MIN_FUSED_SCORE) == 1
    assert dichotomize(DEFAULT_MIN_FUSED_SCORE - 1e-9) == 0
    assert dichotomize(1.0) == 1
    assert dichotomize(0.0) == 0


def test_too_small_a_sample_fails_closed() -> None:
    pairs = [{"temporal": 0.9, "text": 0.1}] * (_MIN_SAMPLE_PAIRS - 1)
    assert estimate_channel_weights(pairs, [0] * len(pairs)) is None


def test_misaligned_inputs_are_a_caller_bug_not_missing_data() -> None:
    with pytest.raises(ValueError):
        estimate_channel_weights([{"temporal": 0.5}], [0, 1])
    pairs = [{"temporal": 0.5}, {"text": 0.5}] * _MIN_SAMPLE_PAIRS
    with pytest.raises(ValueError):
        estimate_channel_weights(pairs, [0] * len(pairs))


def test_a_degenerate_channel_fails_closed() -> None:
    # `text` never clears the floor: its 2PL slope is undefined in
    # practice, so the whole estimate is refused, never worked around.
    pairs = [
        {"temporal": 0.9 if index % 2 else 0.1, "text": 0.0}
        for index in range(_MIN_SAMPLE_PAIRS)
    ]
    assert estimate_channel_weights(pairs, [0] * len(pairs)) is None


@pytest.mark.skipif(
    _FAST_MLSIRM_AVAILABLE, reason="exercises the import-failure fallback"
)
def test_without_fast_mlsirm_a_valid_sample_still_fails_closed() -> None:
    generator = random.Random(20260823)
    pairs = [
        {
            "temporal": generator.random(),
            "text": generator.random(),
        }
        for _ in range(_MIN_SAMPLE_PAIRS)
    ]
    assert estimate_channel_weights(pairs, [0] * len(pairs)) is None


@pytest.mark.skipif(
    not _FAST_MLSIRM_AVAILABLE, reason="requires fast_mlsirm -- install from the org repo"
)
def test_recovery_a_more_discriminating_channel_earns_a_larger_weight() -> None:
    """Parameter-recovery-shaped check per the org's measurement standard.

    Three channels, matching production's deterministic channel count (a
    two-item 2PL leaves discriminations weakly identified). Plant a
    latent per-pair relatedness; `strong` tracks it almost
    deterministically, `mid` moderately, `weak` barely better than
    chance. The estimated convex weights must recover the Birnbaum
    (1968) ordering strong > weak and form a valid convex combination.
    """
    generator = random.Random(20260823)

    def channel_score(related: bool, follow_probability: float) -> float:
        follows = generator.random() < follow_probability
        high = related if follows else not related
        return (0.8 if high else 0.05) + generator.uniform(-0.04, 0.04)

    # Follow probabilities stay away from the quasi-separation regime: a
    # near-deterministic item's slope is unstable under regularized
    # estimation and can be shrunk below a moderate item's, which would
    # test the estimator's penalty behavior rather than the Birnbaum
    # ordering this check is about. Clusters carry genuine intercept
    # variance (per-group relatedness base rates) -- the structure the
    # multilevel random intercept exists to model; clusters that are a
    # meaningless round-robin instead flatten the slope estimates.
    group_base_rate = [generator.uniform(0.25, 0.75) for _ in range(12)]
    pairs: list[dict[str, float]] = []
    group_ids: list[int] = []
    for index in range(900):
        group = index % 12
        related = generator.random() < group_base_rate[group]
        pairs.append(
            {
                "strong": channel_score(related, 0.85),
                "mid": channel_score(related, 0.70),
                "weak": channel_score(related, 0.55),
            }
        )
        group_ids.append(group)

    estimate = estimate_channel_weights(pairs, group_ids)
    assert estimate is not None
    weights = estimate.weights
    assert set(weights) == {"strong", "mid", "weak"}
    assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-9)
    assert all(weight > 0 for weight in weights.values())
    assert weights["strong"] > weights["weak"]
    assert weights["strong"] > weights["mid"] > weights["weak"]
    assert estimate.sample_pair_count == 900
    assert estimate.estimation_method_code == "mls2plm_discrimination"


def test_fixture_simulation_is_deterministic_and_carries_the_demo_design() -> None:
    """Runs everywhere: the demo design must reproduce exactly so every
    `make seed` and demo-server estimate lands on identical weights.
    """
    first_scores, first_groups = simulate_fixture_pair_scores()
    second_scores, second_groups = simulate_fixture_pair_scores()
    assert first_scores == second_scores
    assert first_groups == second_groups
    assert len(first_scores) == 900
    assert set(first_scores[0]) == {"temporal", "secondary_key", "text"}
    assert len(set(first_groups)) == 12


@pytest.mark.skipif(
    not _FAST_MLSIRM_AVAILABLE, reason="requires fast_mlsirm -- install from the org repo"
)
def test_fixture_estimate_recovers_the_demo_design_and_keeps_the_designed_tree() -> None:
    """The demo fuses only with this estimate (ADR 0145, second
    amendment: no hand-picked weight exists anywhere). It must recover
    the declared follow-probability ordering AND still reconstruct the
    designed A-100 fork the demo walkthroughs rely on.
    """
    from lineageweave.fixtures import sample_records
    from lineageweave.lineage_persistence import lineage_edge_specs

    estimate = estimate_fixture_channel_weights()
    assert estimate is not None
    weights = estimate.weights
    assert weights["temporal"] > weights["secondary_key"] > weights["text"]
    assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-9)

    edges = lineage_edge_specs(sample_records(), weights=weights)
    pairs = {(edge.parent_id, edge.child_id) for edge in edges}
    assert ("rec-002", "rec-003") in pairs
    assert ("rec-002", "rec-004") in pairs
    assert "rec-006" not in {edge.child_id for edge in edges}
