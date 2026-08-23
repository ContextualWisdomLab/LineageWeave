"""Leftover post–criterion pairs after the main-effect IRT.

Covers ADR 0048 as amended by ADR 0182.

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
    assert closest.leftover_map_unexplained == pytest.approx(0.0, abs=1e-6)
    assert farthest.leftover_map_unexplained == pytest.approx(0.0, abs=1e-6)
    assert not hasattr(closest, "leftover_map_reconstruction")


def test_zero_residual_still_emits_stable_leftover_pairs() -> None:
    """A rank-zero map retains deterministic closest and farthest rows."""
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
    assert pairs[0].leftover_map_unexplained == pytest.approx(0.0)
    assert pairs[1].leftover_map_unexplained == pytest.approx(0.0)


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
        assert pair.leftover_map_unexplained == pytest.approx(0.0, abs=1e-6)


def test_leftover_is_empty_without_observed_cells() -> None:
    """An entirely missing response matrix yields no invented pair."""
    post_ids = ["post-empty"]
    item_codes = ("item_one",)
    matrix = np.array([[np.nan]], dtype=np.float64)
    expected = np.array([[0.0]], dtype=np.float64)
    assert leftover_pairs_from_residual(post_ids, item_codes, matrix, expected) == ()


def test_leftover_fallback_omits_unexplained_without_complete_case_map() -> None:
    """No complete-case rectangle: persist distance from |R − center|, omit U."""
    post_ids = ["sparse-a", "sparse-b"]
    item_codes = ("item_near", "item_far")
    matrix = np.array(
        [
            [2.0, np.nan],
            [np.nan, -2.0],
        ],
        dtype=np.float64,
    )
    expected = np.zeros_like(matrix)
    pairs = leftover_pairs_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    assert {pair.post_id for pair in pairs} == {"sparse-a", "sparse-b"}
    for pair in pairs:
        assert pair.leftover_map_unexplained is None
        assert pair.leftover_distance >= 0.0
        assert not hasattr(pair, "leftover_map_reconstruction")


def test_rank_three_unexplained_equals_residual_minus_two_axis_reconstruction() -> None:
    """Unexplained leftover U is R − R̂, not leftover residual R, not leftover-map distance d."""
    post_ids = ["post-a", "post-b", "post-c", "post-d"]
    item_codes = ("item-a", "item-b", "item-c", "item-d")
    matrix = np.array(
        [
            [4.0, 1.0, 0.0, -1.0],
            [0.0, 3.0, 1.0, -2.0],
            [-2.0, 0.0, 2.0, 1.0],
            [1.0, -1.0, 0.0, 4.0],
        ],
        dtype=np.float64,
    )
    expected = np.zeros_like(matrix)
    filled = matrix - float(np.mean(matrix))
    person_full, item_full = leftover._leftover_map_positions(filled)
    assert person_full.shape[1] >= 3
    person_map = leftover._pad_map_axes(person_full)
    item_map = leftover._pad_map_axes(item_full)
    reconstruction = person_map @ item_map.T
    full_inner = person_full @ item_full.T
    full_distances = np.linalg.norm(person_full[:, None, :] - item_full[None, :, :], axis=2)
    assert float(np.max(np.abs(reconstruction - filled))) > 1e-6
    assert float(np.max(np.abs(reconstruction - full_inner))) > 1e-6

    pairs = leftover_pairs_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    post_index = {post_id: index for index, post_id in enumerate(post_ids)}
    item_index = {code: index for index, code in enumerate(item_codes)}
    for pair in pairs:
        person = post_index[pair.post_id]
        item = item_index[pair.criterion_code]
        expected_unexplained = float(pair.leftover_residual) - float(reconstruction[person, item])
        assert pair.leftover_map_unexplained == pytest.approx(expected_unexplained)
        assert pair.leftover_map_unexplained != pytest.approx(pair.leftover_residual)
        assert pair.leftover_map_unexplained != pytest.approx(pair.leftover_distance)
        assert pair.leftover_distance == pytest.approx(float(full_distances[person, item]))
        assert not hasattr(pair, "leftover_map_reconstruction")


def test_pad_map_axes_truncates_hidden_svd_components() -> None:
    """Axes after the second leftover-map axis do not enter reconstruction."""
    padded = leftover._pad_map_axes(np.array([[1.0, 2.0, 9.0]], dtype=np.float64))
    assert padded.shape == (1, 2)
    assert padded[0].tolist() == pytest.approx([1.0, 2.0])
