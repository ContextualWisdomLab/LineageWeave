"""Leftover post–criterion pairs after the main-effect IRT (ADR 0048 / 0163).

Uses a constructed residual matrix so the closest and farthest pair
are known without calling ``fit_polytomous``. Loads
``leftover_pairs.py`` by path so package ``__init__`` / ``period_report``
/ ``fast_mlsirm`` stay out of this module.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

_LEFTOVER_PATH = Path(__file__).resolve().parents[1] / "lineageweave" / "leftover_pairs.py"


def _load_leftover():
    source = _LEFTOVER_PATH.read_text(encoding="utf-8")
    imported = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Import):
            imported.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append((node.module or "").split(".", 1)[0])
    assert "fast_mlsirm" not in imported
    assert "period_report" not in imported
    spec = importlib.util.spec_from_file_location("lineageweave_leftover_pairs", _LEFTOVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


leftover = _load_leftover()
PAIR_KIND_CLOSEST = leftover.PAIR_KIND_CLOSEST
PAIR_KIND_FARTHEST = leftover.PAIR_KIND_FARTHEST
leftover_pairs_from_residual = leftover.leftover_pairs_from_residual


def _assert_residual_reconciles(pair) -> None:
    assert pair.leftover_residual == pytest.approx(
        pair.observed_response - pair.expected_response, abs=1e-6
    )


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
    assert farthest.observed_response == pytest.approx(-2.0)
    assert farthest.expected_response == pytest.approx(0.0)
    assert farthest.leftover_distance == pytest.approx(2.0 * np.sqrt(2.0), rel=1e-6)
    for pair in pairs:
        _assert_residual_reconciles(pair)


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
    assert pairs[0].observed_response == pytest.approx(1.0)
    assert pairs[0].expected_response == pytest.approx(1.0)
    assert pairs[1].post_id == "beta-post"
    assert pairs[1].criterion_code == "item_two"
    for pair in pairs:
        _assert_residual_reconciles(pair)


def test_partial_observation_does_not_treat_missing_as_zero_residual() -> None:
    """A missing cell must not enter the Gabriel factorization as 0."""
    post_ids = ["aligned-post", "opposed-post", "sparse-post"]
    item_codes = ("item_near", "item_far")
    matrix = np.array(
        [
            [2.0, -2.0],
            [-2.0, 2.0],
            [2.0, np.nan],
        ],
        dtype=np.float64,
    )
    expected = np.zeros_like(matrix)
    pairs = leftover_pairs_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    closest, farthest = pairs
    assert {pair.post_id for pair in pairs} <= {"aligned-post", "opposed-post"}
    assert closest.leftover_distance == pytest.approx(0.0, abs=1e-9)
    assert farthest.leftover_distance == pytest.approx(2.0 * np.sqrt(2.0), rel=1e-6)
    assert farthest.leftover_residual == pytest.approx(-2.0)
    assert (farthest.post_id, farthest.criterion_code) in {
        ("aligned-post", "item_far"),
        ("opposed-post", "item_near"),
    }
    for pair in pairs:
        _assert_residual_reconciles(pair)


def test_leftover_is_empty_without_observed_cells() -> None:
    post_ids = ["post-empty"]
    item_codes = ("item_one",)
    matrix = np.array([[np.nan]], dtype=np.float64)
    expected = np.array([[0.0]], dtype=np.float64)
    assert leftover_pairs_from_residual(post_ids, item_codes, matrix, expected) == ()


def test_leftover_residual_equals_observed_minus_expected() -> None:
    """Named Y and E on leftover pairs must reconcile to R = Y − E."""
    post_ids = ["public-post", "spec-post"]
    item_codes = ("sales_lead_specificity", "general_sentiment_negative")
    matrix = np.array(
        [
            [2.4, 0.0],
            [0.0, 0.9],
        ],
        dtype=np.float64,
    )
    expected = np.array(
        [
            [2.0, 0.0],
            [0.0, 2.0],
        ],
        dtype=np.float64,
    )
    pairs = leftover_pairs_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    by_cell = {(pair.post_id, pair.criterion_code): pair for pair in pairs}
    closest_cell = by_cell[("public-post", "sales_lead_specificity")]
    farthest_cell = by_cell[("spec-post", "general_sentiment_negative")]
    assert closest_cell.observed_response == pytest.approx(2.4)
    assert closest_cell.expected_response == pytest.approx(2.0)
    assert closest_cell.leftover_residual == pytest.approx(0.4)
    assert farthest_cell.observed_response == pytest.approx(0.9)
    assert farthest_cell.expected_response == pytest.approx(2.0)
    assert farthest_cell.leftover_residual == pytest.approx(-1.1)
    for pair in pairs:
        _assert_residual_reconciles(pair)


def test_leftover_residual_rejects_database_tolerance_boundary() -> None:
    """Python must reject the exact boundary excluded by the DB check."""
    with pytest.raises(ValueError, match="observed Y minus expected E"):
        leftover._candidate_row(
            ["public-post"],
            ("sales_lead_specificity",),
            np.array([[0.0]]),
            np.array([[0.0]]),
            np.array([[1e-6]]),
            0,
            0,
            0.0,
        )
