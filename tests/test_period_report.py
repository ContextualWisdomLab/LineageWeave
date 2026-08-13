"""Accuracy tests for ADR 0003 slice 3 period calibration.

A high-scoring constructed group must outscore a low-scoring group on
the fitted EAP metric -- not a hardcoded constant, and not a mock of
``fit_polytomous``.
"""

from __future__ import annotations

import numpy as np
import pytest

from lineageweave.period_report import (
    assemble_response_matrix,
    calibrate_period_report,
    gpcm_category_probabilities,
    grm_category_probabilities,
)
from lineageweave.post_evaluation import CRITERION_CODES, IRT_CATEGORY_COUNT


def test_grm_category_probabilities_sum_to_one() -> None:
    theta = np.linspace(-2.0, 2.0, 5)
    slope = np.array([1.1, 0.8, 1.3])
    cat_params = np.array([[1.0, 0.3, -0.4, -1.2], [0.8, 0.1, -0.5, -1.0], [1.2, 0.4, -0.2, -0.9]])
    probs = grm_category_probabilities(theta, slope, cat_params)
    assert probs.shape == (5, 3, 5)
    np.testing.assert_allclose(probs.sum(axis=2), 1.0, atol=1e-6)


def test_gpcm_category_probabilities_sum_to_one() -> None:
    theta = np.linspace(-2.0, 2.0, 5)
    slope = np.array([1.0, 0.9, 1.2])
    cat_params = np.array([[0.2, -0.1, 0.0, 0.1], [0.1, 0.0, -0.2, 0.05], [0.0, 0.15, -0.1, 0.0]])
    probs = gpcm_category_probabilities(theta, slope, cat_params)
    np.testing.assert_allclose(probs.sum(axis=2), 1.0, atol=1e-6)


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


def test_assemble_response_matrix_leaves_unknown_items_missing() -> None:
    matrix = assemble_response_matrix(
        ["p1", "p2"],
        [("p1", CRITERION_CODES[0], 3), ("p2", "not_a_criterion", 1)],
    )
    assert matrix.shape == (2, 3)
    assert matrix[0, 0] == 3
    assert np.isnan(matrix[1]).all()
