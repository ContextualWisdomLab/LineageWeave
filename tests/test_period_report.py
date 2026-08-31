"""Accuracy tests for ADR 0003 slice 3 period calibration.

A high-scoring constructed group must outscore a low-scoring group on
the fitted EAP metric -- not a hardcoded constant, and not a mock of
``fit_polytomous``.
"""

from __future__ import annotations

import numpy as np
import pytest

from lineageweave import period_report as period_report_module

from lineageweave.period_report import (
    LINK_METHOD_FIPC,
    LINK_METHOD_FREE,
    PAIR_KIND_CLOSEST,
    PAIR_KIND_FARTHEST,
    ItemBank,
    assemble_response_matrix,
    calibrate_period_report,
    leftover_pairs_from_residual,
    link_or_calibrate_period_report,
    rank_items_by_information,
    score_groups_on_shared_metric,
    score_period_on_bank,
)
from lineageweave.fixtures import fixture_titles_in_iso_week
from lineageweave.post_evaluation import CRITERION_CODES, IRT_CATEGORY_COUNT


def test_category_probability_axis_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Upstream prediction axes cannot silently corrupt report residuals."""
    bank = _location_shifted_bank()
    monkeypatch.setattr(
        period_report_module,
        "polytomous_category_probabilities",
        lambda _fit, _theta: np.zeros((3, 2, 5)),
    )

    with pytest.raises(ValueError, match="must have shape"):
        period_report_module._category_probabilities(
            "grm", np.asarray([0.0, 1.0]), bank.as_fit()
        )


def test_high_category_posts_outrank_low_category_posts() -> None:
    """True structure: four 'high' posts are all category 4; four 'low'
    posts are all category 0. After a real GRM/GPCM + FIPC + EAP pass,
    the high group's mean theta must exceed the low group's.
    """
    items = CRITERION_CODES
    high_ids = [f"high-{idx}" for idx in range(4)]
    low_ids = [f"low-{idx}" for idx in range(4)]
    rows: list[tuple[str, str, int]] = []
    for post_id in high_ids:
        for item in items:
            rows.append((post_id, item, IRT_CATEGORY_COUNT - 1))
    for post_id in low_ids:
        for item in items:
            rows.append((post_id, item, 0))

    report = calibrate_period_report(high_ids + low_ids, rows)
    by_id = {member.post_id: member.theta_eap for member in report.member_scores}
    high_mean = float(np.mean([by_id[post_id] for post_id in high_ids]))
    low_mean = float(np.mean([by_id[post_id] for post_id in low_ids]))
    assert high_mean > low_mean
    assert report.post_count == 8
    assert report.item_count == 3
    assert report.selected_model in {"grm", "gpcm"}
    assert report.mean_theta == pytest.approx(float(np.mean(list(by_id.values()))), abs=1e-9)


def test_fipc_keeps_all_high_week_above_mixed_reference() -> None:
    """Independent refit of an all-high week recenters near 0. Scoring
    the same rows on the mixed week's item bank must keep mean θ above
    the reference -- that is the buyer-visible week-over-week signal.
    """
    items = CRITERION_CODES
    high_ids = [f"high-{idx}" for idx in range(4)]
    low_ids = [f"low-{idx}" for idx in range(4)]
    ref_rows: list[tuple[str, str, int]] = []
    for post_id in high_ids:
        for item in items:
            ref_rows.append((post_id, item, IRT_CATEGORY_COUNT - 1))
    for post_id in low_ids:
        for item in items:
            ref_rows.append((post_id, item, 0))

    reference = calibrate_period_report(high_ids + low_ids, ref_rows, source_period_code="2026-W02")
    assert reference.link_method == LINK_METHOD_FREE
    assert reference.item_bank.source_period_code == "2026-W02"

    new_ids = [f"next-{idx}" for idx in range(6)]
    new_rows = [(post_id, item, IRT_CATEGORY_COUNT - 1) for post_id in new_ids for item in items]
    linked = score_period_on_bank(new_ids, new_rows, reference.item_bank, reference.mean_theta)
    independent = calibrate_period_report(new_ids, new_rows)

    assert linked.link_method == LINK_METHOD_FIPC
    assert linked.anchor_period_code == "2026-W02"
    assert linked.mean_theta > reference.mean_theta
    assert linked.delta_mean_theta == pytest.approx(linked.mean_theta - reference.mean_theta, abs=1e-9)
    assert independent.mean_theta < linked.mean_theta


def test_link_or_calibrate_uses_bank_when_present() -> None:
    items = CRITERION_CODES
    ref_ids = [f"ref-{idx}" for idx in range(4)]
    ref_rows = [(post_id, item, (0 if idx < 2 else IRT_CATEGORY_COUNT - 1)) for idx, post_id in enumerate(ref_ids) for item in items]
    reference = link_or_calibrate_period_report(ref_ids, ref_rows, source_period_code="2026-W02")
    later_ids = [f"later-{idx}" for idx in range(4)]
    later_rows = [(post_id, item, IRT_CATEGORY_COUNT - 1) for post_id in later_ids for item in items]
    linked = link_or_calibrate_period_report(
        later_ids,
        later_rows,
        item_bank=reference.item_bank,
        previous_mean_theta=reference.mean_theta,
    )
    assert linked.link_method == LINK_METHOD_FIPC
    assert linked.item_bank.slope == reference.item_bank.slope


def test_shared_metric_ranks_high_group_above_low_group() -> None:
    """Two process units in the same week: all-high vs all-low.

    Independent refits each re-center near 0, so the gap collapses.
    Scoring both on one pooled bank must keep the high unit above the
    low unit -- that is the buyer-visible multilevel signal.
    """
    items = CRITERION_CODES
    high_ids = [f"high-{idx}" for idx in range(4)]
    low_ids = [f"low-{idx}" for idx in range(4)]
    high_rows = [(post_id, item, IRT_CATEGORY_COUNT - 1) for post_id in high_ids for item in items]
    low_rows = [(post_id, item, 0) for post_id in low_ids for item in items]

    high_alone = calibrate_period_report(high_ids, high_rows)
    low_alone = calibrate_period_report(low_ids, low_rows)
    bank_report, scored = score_groups_on_shared_metric(
        {"high": (high_ids, high_rows), "low": (low_ids, low_rows)},
        source_period_code="2026-W02",
    )
    assert bank_report is not None
    assert bank_report.link_method == LINK_METHOD_FREE
    assert scored["high"].link_method == LINK_METHOD_FIPC
    assert scored["high"].anchor_period_code == "2026-W02"
    assert scored["high"].delta_mean_theta is None
    assert scored["high"].mean_theta > scored["low"].mean_theta
    shared_gap = scored["high"].mean_theta - scored["low"].mean_theta
    alone_gap = high_alone.mean_theta - low_alone.mean_theta
    assert shared_gap > alone_gap


def test_fixture_titles_in_w02_are_event_lineage_not_dummy_bands() -> None:
    """Period-report fold must pick A-100/B-200 reconstruct titles in W02."""
    titles = fixture_titles_in_iso_week("2026-W02")
    assert "Pricing renegotiation follow-up" in titles
    assert "Specification revision requested" in titles
    assert "Follow-up on the Riverbend order confirmation" in titles
    assert "Initial site visit and project scope discussion" not in titles
    assert "Unrelated: annual account review" not in titles
    assert "Delivery schedule confirmed with logistics" not in titles
    assert fixture_titles_in_iso_week("2026-W03") == (
        "Delivery schedule confirmed with logistics",
        "Revised specification approved",
    )


def _location_shifted_bank() -> ItemBank:
    """GRM bank whose items peak at different θ (strictly decreasing thresholds)."""
    return ItemBank(
        model="grm",
        item_codes=CRITERION_CODES,
        slope=(1.6, 1.6, 1.6),
        cat_params=(
            (1.5, 0.5, -0.5, -1.5),
            (3.0, 2.0, 1.0, 0.0),
            (0.0, -1.0, -2.0, -3.0),
        ),
        source_period_code="2026-W02",
    )


def test_cat_selects_hard_item_at_high_theta() -> None:
    """Lord max-info: a high-θ group is measured by the high-location item.

    Threshold layouts are constructed so ``sales_lead_specificity`` peaks
    at +θ and ``general_sentiment_negative`` peaks at −θ. Information
    itself comes from ``information_polytomous``, not a hand-rolled I(θ).
    """
    bank = _location_shifted_bank()
    high = rank_items_by_information(bank, 2.0)
    low = rank_items_by_information(bank, -2.0)
    assert [item.rank for item in high] == [1, 2, 3]
    assert high[0].item_code == "sales_lead_specificity"
    assert low[0].item_code == "general_sentiment_negative"
    assert high[0].information > high[1].information
    assert low[0].information > low[1].information
    assert high[0].item_code != low[0].item_code


def test_leftover_residual_biplot_separates_aligned_and_opposed_cells() -> None:
    """A rank-1 leftover spike puts the aligned cell closest and the opposed cell farthest."""
    post_ids = ["post-a", "post-b", "post-c"]
    item_codes = ("item_near", "item_mid", "item_far")
    matrix = np.array(
        [
            [2.0, 0.0, -2.0],
            [0.0, 0.0, 0.0],
            [-2.0, 0.0, 2.0],
        ],
        dtype=np.float64,
    )
    expected = np.zeros_like(matrix)
    pairs = leftover_pairs_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    closest, farthest = pairs
    assert closest.leftover_distance < farthest.leftover_distance
    assert closest.leftover_distance == pytest.approx(0.0, abs=1e-9)
    assert (farthest.post_id, farthest.criterion_code) in {
        ("post-a", "item_far"),
        ("post-c", "item_near"),
    }
    assert farthest.leftover_residual == pytest.approx(-2.0)
    assert farthest.leftover_distance == pytest.approx(2.0 * np.sqrt(2.0), rel=1e-6)


def test_zero_residual_still_emits_stable_leftover_pairs() -> None:
    post_ids = ["alpha-post", "beta-post"]
    item_codes = ("item_one", "item_two")
    matrix = np.ones((2, 2), dtype=np.float64)
    expected = np.ones((2, 2), dtype=np.float64)
    pairs = leftover_pairs_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    assert pairs[0].leftover_distance == pytest.approx(0.0)
    assert pairs[1].leftover_distance == pytest.approx(0.0)
    assert pairs[0].post_id == "alpha-post"
    assert pairs[0].criterion_code == "item_one"
    assert pairs[1].post_id == "beta-post"
    assert pairs[1].criterion_code == "item_two"


def test_calibrated_report_attaches_leftover_pairs() -> None:
    items = CRITERION_CODES
    high_ids = [f"high-{idx}" for idx in range(4)]
    low_ids = [f"low-{idx}" for idx in range(4)]
    rows: list[tuple[str, str, int]] = []
    for post_id in high_ids:
        for item in items:
            rows.append((post_id, item, IRT_CATEGORY_COUNT - 1))
    for post_id in low_ids:
        for item in items:
            category = 0 if item != "sales_lead_specificity" else IRT_CATEGORY_COUNT - 1
            rows.append((post_id, item, category))
    report = calibrate_period_report(high_ids + low_ids, rows)
    assert len(report.leftover_pairs) == 2
    kinds = {pair.pair_kind for pair in report.leftover_pairs}
    assert kinds == {PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST}
    by_kind = {pair.pair_kind: pair for pair in report.leftover_pairs}
    assert by_kind[PAIR_KIND_CLOSEST].leftover_distance <= by_kind[PAIR_KIND_FARTHEST].leftover_distance
    member_ids = {member.post_id for member in report.member_scores}
    for pair in report.leftover_pairs:
        assert pair.post_id in member_ids
        assert pair.criterion_code in items
        assert pair.leftover_distance >= 0.0
        assert np.isfinite(pair.leftover_residual)
        assert pair.leftover_residual == pytest.approx(
            pair.observed_response - pair.expected_response, abs=1e-6
        )
        assert pair.leftover_map_rank >= 0
        if pair.leftover_map_unexplained is not None:
            assert np.isfinite(pair.leftover_map_unexplained)
        if pair.leftover_map_cross_share is not None:
            assert np.isfinite(pair.leftover_map_cross_share)
        if pair.leftover_map_reconstruction is not None:
            assert np.isfinite(pair.leftover_map_reconstruction)
        if pair.leftover_map_unexplained_share is not None:
            assert np.isfinite(pair.leftover_map_unexplained_share)
            assert pair.leftover_map_unexplained_share >= 0.0
        if pair.leftover_map_explained_share is not None:
            assert np.isfinite(pair.leftover_map_explained_share)
            assert pair.leftover_map_explained_share >= 0.0
        axes = (
            pair.leftover_map_person_axis_1,
            pair.leftover_map_person_axis_2,
            pair.leftover_map_item_axis_1,
            pair.leftover_map_item_axis_2,
        )
        if any(axis is None for axis in axes):
            assert axes == (None, None, None, None)
        else:
            person_axis_1, person_axis_2, item_axis_1, item_axis_2 = axes
            assert np.isfinite(person_axis_1)
            assert np.isfinite(person_axis_2)
            assert np.isfinite(item_axis_1)
            assert np.isfinite(item_axis_2)
            if pair.leftover_map_reconstruction is not None:
                assert pair.leftover_map_reconstruction == pytest.approx(
                    person_axis_1 * item_axis_1 + person_axis_2 * item_axis_2
                )
            assert pair.leftover_distance == pytest.approx(
                float(np.hypot(person_axis_1 - item_axis_1, person_axis_2 - item_axis_2))
            )
        if (
            pair.leftover_map_explained_share is not None
            and pair.leftover_map_unexplained_share is not None
            and pair.leftover_map_cross_share is not None
            and abs(pair.leftover_residual) > 1e-12
        ):
            assert (
                pair.leftover_map_explained_share
                + pair.leftover_map_unexplained_share
                + pair.leftover_map_cross_share
            ) == pytest.approx(1.0)
    assert [axis.axis_index for axis in report.leftover_map_axes] == [1, 2]
    for axis in report.leftover_map_axes:
        assert axis.leftover_singular_value >= 0.0
        assert 0.0 <= axis.leftover_share <= 1.0
        assert np.isfinite(axis.leftover_singular_value)
        assert np.isfinite(axis.leftover_share)
    assert sum(axis.leftover_share for axis in report.leftover_map_axes) <= 1.0 + 1e-9
    coverage = report.leftover_map_coverage
    assert coverage is not None
    assert coverage.map_post_count == 8
    assert coverage.scored_post_count == 8
    assert coverage.incomplete_post_count == 0
    assert coverage.map_item_count == len(items)
    assert coverage.scored_item_count == len(items)



def test_shared_metric_attaches_cat_ranking() -> None:
    """Scoring a group on the shared bank must persist a CAT ranking."""
    items = CRITERION_CODES
    high_ids = [f"high-{idx}" for idx in range(4)]
    low_ids = [f"low-{idx}" for idx in range(4)]
    high_rows = [(post_id, item, IRT_CATEGORY_COUNT - 1) for post_id in high_ids for item in items]
    low_rows = [(post_id, item, 0) for post_id in low_ids for item in items]
    _, scored = score_groups_on_shared_metric(
        {"high": (high_ids, high_rows), "low": (low_ids, low_rows)},
        source_period_code="2026-W02",
    )
    for report in scored.values():
        assert len(report.selected_items) == 3
        assert [item.rank for item in report.selected_items] == [1, 2, 3]
        assert all(item.information > 0.0 for item in report.selected_items)
        assert {item.item_code for item in report.selected_items} == set(CRITERION_CODES)


def test_assemble_response_matrix_leaves_unknown_items_missing() -> None:
    matrix = assemble_response_matrix(
        ["p1", "p2"],
        [("p1", CRITERION_CODES[0], 3), ("p2", "not_a_criterion", 1)],
    )
    assert matrix.shape == (2, 3)
    assert matrix[0, 0] == 3
    assert np.isnan(matrix[1]).all()
