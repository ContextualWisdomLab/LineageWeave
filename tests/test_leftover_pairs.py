"""Leftover post–criterion pairs after the main-effect IRT.

Covers ADR 0048 as amended by ADR 0119, ADR 0148, ADR 0163, ADR 0164,
ADR 0182, ADR 0185, ADR 0201, ADR 0233, and ADR 0266.

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
_LEFTOVER_SINGULAR_FLOOR = 1e-12
_LEFTOVER_MAP_AXES = 2


def _load_leftover():
    """Load only the dependency-light leftover module under test."""
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
leftover_map_from_residual = leftover.leftover_map_from_residual
leftover_map_axes_from_singular = leftover.leftover_map_axes_from_singular
leftover_map_coverage_from_residual = leftover.leftover_map_coverage_from_residual


def _assert_residual_reconciles(pair) -> None:
    """Assert the persisted residual is exactly grounded in named Y and E."""
    assert pair.leftover_residual == pytest.approx(
        pair.observed_response - pair.expected_response, abs=1e-6
    )


def _assert_persists_explained_share(pair) -> None:
    """Explained leftover share is persisted with unexplained leftover share."""
    assert hasattr(pair, "leftover_map_explained_share")
    assert hasattr(pair, "leftover_map_unexplained_share")


def _gabriel_positions(filled: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Independent Gabriel coordinates used to prove leftover_distance axes."""
    left, singular, right = np.linalg.svd(filled, full_matrices=False)
    keep = singular > _LEFTOVER_SINGULAR_FLOOR
    scale = np.sqrt(singular[keep])
    return left[:, keep] * scale, right[keep, :].T * scale


def _pad_map_axes(positions: np.ndarray) -> np.ndarray:
    """Independently pad or truncate coordinates to two map axes."""
    padded = np.zeros((positions.shape[0], _LEFTOVER_MAP_AXES), dtype=np.float64)
    width = min(_LEFTOVER_MAP_AXES, positions.shape[1])
    padded[:, :width] = positions[:, :width]
    return padded


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
    assert closest.leftover_map_unexplained == pytest.approx(0.0, abs=1e-6)
    assert farthest.leftover_map_unexplained == pytest.approx(0.0, abs=1e-6)
    # Closest is the origin cell (R = 0, R̂ = 0, U = 0): 0/0 stores 0.
    assert closest.leftover_map_cross_share == pytest.approx(0.0, abs=1e-6)
    # Rank-1 reconstructed opposed cell: U = 0 so x = 0.
    assert farthest.leftover_map_cross_share == pytest.approx(0.0, abs=1e-6)
    assert closest.leftover_map_unexplained_share == pytest.approx(0.0, abs=1e-6)
    assert farthest.leftover_map_unexplained_share == pytest.approx(0.0, abs=1e-6)
    assert closest.leftover_map_explained_share == pytest.approx(0.0, abs=1e-6)
    assert farthest.leftover_map_explained_share == pytest.approx(1.0, abs=1e-6)
    assert closest.leftover_map_reconstruction == pytest.approx(0.0, abs=1e-6)
    assert farthest.leftover_map_reconstruction == pytest.approx(-2.0, abs=1e-6)
    for pair in pairs:
        _assert_residual_reconciles(pair)
        _assert_persists_explained_share(pair)
        assert pair.leftover_map_rank == 1
    coverage = leftover_map_coverage_from_residual(post_ids, item_codes, matrix, expected)
    assert coverage.map_post_count == 3
    assert coverage.scored_post_count == 3
    assert coverage.incomplete_post_count == 0
    assert coverage.map_item_count == 3
    assert coverage.scored_item_count == 3


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
    assert pairs[0].observed_response == pytest.approx(1.0)
    assert pairs[0].expected_response == pytest.approx(1.0)
    assert pairs[1].post_id == "beta-post"
    assert pairs[1].criterion_code == "item_two"
    assert pairs[0].leftover_map_unexplained == pytest.approx(0.0)
    assert pairs[1].leftover_map_unexplained == pytest.approx(0.0)
    assert pairs[0].leftover_map_cross_share == pytest.approx(0.0)
    assert pairs[1].leftover_map_cross_share == pytest.approx(0.0)
    assert pairs[0].leftover_map_unexplained_share == pytest.approx(0.0)
    assert pairs[1].leftover_map_unexplained_share == pytest.approx(0.0)
    assert pairs[0].leftover_map_explained_share == pytest.approx(0.0)
    assert pairs[1].leftover_map_explained_share == pytest.approx(0.0)
    assert pairs[0].leftover_map_reconstruction == pytest.approx(0.0)
    assert pairs[1].leftover_map_reconstruction == pytest.approx(0.0)
    for pair in pairs:
        _assert_residual_reconciles(pair)
        assert pair.leftover_map_rank == 0
    coverage = leftover_map_coverage_from_residual(post_ids, item_codes, matrix, expected)
    assert coverage.map_post_count == 2
    assert coverage.scored_post_count == 2
    assert coverage.incomplete_post_count == 0


def test_rank_zero_nonzero_constant_residual_keeps_raw_identity() -> None:
    """Centering a constant nonzero residual gives R̂=0 while U remains R."""
    matrix = np.ones((2, 2), dtype=np.float64)
    pairs = leftover_pairs_from_residual(
        ["post-a", "post-b"],
        ("item-a", "item-b"),
        matrix,
        np.zeros_like(matrix),
    )

    assert pairs
    for pair in pairs:
        assert pair.leftover_map_rank == 0
        assert pair.leftover_residual == pytest.approx(1.0)
        assert pair.leftover_map_reconstruction == pytest.approx(0.0)
        assert pair.leftover_map_unexplained == pytest.approx(1.0)
        assert pair.leftover_map_unexplained_share == pytest.approx(1.0)
        assert pair.leftover_map_explained_share == pytest.approx(0.0)
        assert pair.leftover_map_unexplained + pair.leftover_map_reconstruction == pytest.approx(
            pair.leftover_residual
        )


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
        assert pair.leftover_map_rank == 1
        assert pair.leftover_map_unexplained == pytest.approx(0.0, abs=1e-6)
        assert pair.leftover_map_cross_share == pytest.approx(0.0, abs=1e-6)
        assert pair.leftover_map_unexplained_share == pytest.approx(0.0, abs=1e-6)
        assert pair.leftover_map_explained_share == pytest.approx(1.0, abs=1e-6)
    coverage = leftover_map_coverage_from_residual(post_ids, item_codes, matrix, expected)
    assert coverage.map_post_count == 2
    assert coverage.scored_post_count == 3
    assert coverage.incomplete_post_count == 1
    assert coverage.map_item_count == 2
    assert coverage.scored_item_count == 2
    assert coverage.incomplete_item_count == 0


def test_leftover_is_empty_without_observed_cells() -> None:
    """An entirely missing response matrix yields no invented pair."""
    post_ids = ["post-empty"]
    item_codes = ("item_one",)
    matrix = np.array([[np.nan]], dtype=np.float64)
    expected = np.array([[0.0]], dtype=np.float64)
    assert leftover_pairs_from_residual(post_ids, item_codes, matrix, expected) == ()
    coverage = leftover_map_coverage_from_residual(post_ids, item_codes, matrix, expected)
    assert coverage.map_post_count == 0
    assert coverage.scored_post_count == 0
    assert coverage.incomplete_post_count == 0
    assert coverage.map_item_count == 0
    assert coverage.scored_item_count == 0
    assert coverage.incomplete_item_count == 0


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
            None,
            None,
            None,
            None,
            None,
        )


def test_leftover_pairs_empty_without_complete_case_map() -> None:
    """No complete-case rectangle (ADR 0168): no stand-in pair, coverage instead."""
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
    assert leftover_pairs_from_residual(post_ids, item_codes, matrix, expected) == ()
    coverage = leftover_map_coverage_from_residual(post_ids, item_codes, matrix, expected)
    assert coverage.map_post_count == 0
    assert coverage.scored_post_count == 2
    assert coverage.incomplete_post_count == 2


def test_rank_one_nonzero_center_is_disclosed_by_raw_residual_cross_share() -> None:
    """Raw-residual cross share retains the mean omitted by centered SVD."""
    post_ids = ["post-a", "post-b", "post-c"]
    item_codes = ("item_near", "item_mid", "item_far")
    matrix = np.array(
        [
            [5.0, 3.0, 1.0],
            [3.0, 3.0, 3.0],
            [1.0, 3.0, 5.0],
        ],
        dtype=np.float64,
    )
    expected = np.zeros_like(matrix)
    assert float(np.mean(matrix)) == pytest.approx(3.0)
    pairs = leftover_pairs_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    closest, farthest = pairs
    person_full, item_full, _singular = leftover._leftover_map_positions(matrix - np.mean(matrix))
    reconstruction = leftover._pad_map_axes(person_full) @ leftover._pad_map_axes(item_full).T
    post_index = {post_id: index for index, post_id in enumerate(post_ids)}
    item_index = {code: index for index, code in enumerate(item_codes)}
    for pair in pairs:
        residual = pair.leftover_residual
        recon = float(reconstruction[post_index[pair.post_id], item_index[pair.criterion_code]])
        expected_share = 0.0 if residual == 0.0 and recon == 0.0 else 2.0 * recon * (residual - recon) / residual**2
        assert pair.leftover_map_cross_share == pytest.approx(expected_share, abs=1e-6)
    assert farthest.leftover_residual != pytest.approx(0.0)
    assert farthest.leftover_map_cross_share != pytest.approx(farthest.leftover_residual)
    for pair in pairs:
        _assert_residual_reconciles(pair)
        _assert_persists_explained_share(pair)


def test_rank_one_leftover_map_puts_all_inertia_on_axis_one() -> None:
    """A rank-1 residual must report leftover-map share 1 on axis 1, 0 on axis 2."""
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
    pairs, axes = leftover_map_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    assert [axis.axis_index for axis in axes] == [1, 2]
    assert axes[0].leftover_share == pytest.approx(1.0)
    assert axes[1].leftover_share == pytest.approx(0.0)
    assert axes[0].leftover_singular_value > 0.0
    assert axes[1].leftover_singular_value == pytest.approx(0.0)
    assert leftover_pairs_from_residual(post_ids, item_codes, matrix, expected) == pairs


def test_zero_residual_emits_two_zero_share_leftover_map_axes() -> None:
    post_ids = ["alpha-post", "beta-post"]
    item_codes = ("item_one", "item_two")
    matrix = np.ones((2, 2), dtype=np.float64)
    expected = np.ones((2, 2), dtype=np.float64)
    pairs, axes = leftover_map_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    assert [axis.axis_index for axis in axes] == [1, 2]
    assert axes[0].leftover_share == pytest.approx(0.0)
    assert axes[1].leftover_share == pytest.approx(0.0)
    assert axes[0].leftover_singular_value == pytest.approx(0.0)
    assert axes[1].leftover_singular_value == pytest.approx(0.0)


def test_leftover_map_axes_from_singular_use_gabriel_inertia() -> None:
    """Share is σ_k² / Σ_j σ_j² from the actual singular values, never a leftover score."""
    singular = np.array([3.0, 1.0, 0.5], dtype=np.float64)
    total = float(np.sum(singular * singular))
    axes = leftover_map_axes_from_singular(singular)
    assert [axis.axis_index for axis in axes] == [1, 2]
    assert axes[0].leftover_singular_value == pytest.approx(3.0)
    assert axes[1].leftover_singular_value == pytest.approx(1.0)
    assert axes[0].leftover_share == pytest.approx(9.0 / total)
    assert axes[1].leftover_share == pytest.approx(1.0 / total)
    assert leftover_map_axes_from_singular(np.zeros(0))[0].leftover_share == pytest.approx(0.0)
    assert leftover_map_from_residual(
        ["post-empty"],
        ("item_one",),
        np.array([[np.nan]], dtype=np.float64),
        np.array([[0.0]], dtype=np.float64),
    ) == ((), ())


def test_rank_four_pair_distances_match_two_dimensional_gabriel_coords() -> None:
    """Jeon leftover_distance is Euclidean on the 2D map, not the full SVD rank."""
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
    person_full, item_full = _gabriel_positions(filled)
    assert person_full.shape[1] == 4
    person_map = _pad_map_axes(person_full)
    item_map = _pad_map_axes(item_full)
    full_distances = np.linalg.norm(person_full[:, None, :] - item_full[None, :, :], axis=2)
    map_distances = np.linalg.norm(person_map[:, None, :] - item_map[None, :, :], axis=2)
    assert float(np.max(np.abs(full_distances - map_distances))) > 1e-6

    pairs = leftover_pairs_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    post_index = {post_id: index for index, post_id in enumerate(post_ids)}
    item_index = {code: index for index, code in enumerate(item_codes)}
    for pair in pairs:
        assert pair.leftover_map_rank == 4
        person = post_index[pair.post_id]
        item = item_index[pair.criterion_code]
        assert pair.leftover_distance == pytest.approx(float(map_distances[person, item]))
        assert pair.leftover_distance != pytest.approx(
            float(full_distances[person, item]), abs=1e-9
        )

    farthest_map = np.unravel_index(int(np.argmax(map_distances)), map_distances.shape)
    farthest = pairs[1]
    assert (post_index[farthest.post_id], item_index[farthest.criterion_code]) == farthest_map


def test_unexplained_and_cross_share_are_identity_remainder_terms() -> None:
    """Unexplained U is R − R̂; cross share is 2 R̂ U / R². Neither is R or d.

    Uses the same rank-4 matrix as the two-axis distance proof above: R̂ is
    the two-axis Gabriel reconstruction ``person_map @ item_map.T``, built
    from the same padded coordinates ``leftover_distance`` already uses.
    """
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
    center = float(np.mean(matrix))
    filled = matrix - center
    person_full, item_full, singular = leftover._leftover_map_positions(filled)
    rank = int(singular.size)
    assert person_full.shape[1] >= 3
    person_map = leftover._pad_map_axes(person_full)
    item_map = leftover._pad_map_axes(item_full)
    reconstruction = person_map @ item_map.T
    full_inner = person_full @ item_full.T
    map_distances = np.linalg.norm(person_map[:, None, :] - item_map[None, :, :], axis=2)
    assert float(np.max(np.abs(reconstruction - filled))) > 1e-6
    assert float(np.max(np.abs(reconstruction - full_inner))) > 1e-6
    assert abs(center) > 1e-6

    pairs = leftover_pairs_from_residual(post_ids, item_codes, matrix, expected)
    assert [pair.pair_kind for pair in pairs] == [PAIR_KIND_CLOSEST, PAIR_KIND_FARTHEST]
    post_index = {post_id: index for index, post_id in enumerate(post_ids)}
    item_index = {code: index for index, code in enumerate(item_codes)}
    saw_nonzero_cross = False
    for pair in pairs:
        person = post_index[pair.post_id]
        item = item_index[pair.criterion_code]
        recon = float(reconstruction[person, item])
        # Raw unexplained leftover U = R − R̂ (ADR 0182).
        expected_unexplained = float(pair.leftover_residual) - recon
        assert pair.leftover_map_unexplained == pytest.approx(expected_unexplained)
        assert pair.leftover_map_unexplained != pytest.approx(pair.leftover_residual)
        assert pair.leftover_map_unexplained != pytest.approx(pair.leftover_distance)
        assert pair.leftover_map_reconstruction == pytest.approx(recon)
        assert pair.leftover_map_unexplained + pair.leftover_map_reconstruction == pytest.approx(
            pair.leftover_residual
        )
        # Raw-residual cross share x = 2 R̂ U / R² (ADR 0185).
        residual = float(pair.leftover_residual)
        expected_share = (2.0 * recon * expected_unexplained) / (residual * residual)
        explained_share = (recon * recon) / (residual * residual)
        unexplained_share = (expected_unexplained * expected_unexplained) / (residual * residual)
        assert pair.leftover_map_cross_share == pytest.approx(expected_share)
        assert pair.leftover_map_unexplained_share == pytest.approx(unexplained_share)
        assert pair.leftover_map_explained_share == pytest.approx(explained_share)
        assert pair.leftover_map_explained_share + pair.leftover_map_unexplained_share + pair.leftover_map_cross_share == pytest.approx(1.0)
        if abs(expected_share) > 1e-6:
            saw_nonzero_cross = True
        assert pair.leftover_map_cross_share != pytest.approx(pair.leftover_residual)
        assert pair.leftover_map_cross_share != pytest.approx(pair.leftover_distance)
        # Distance is Euclidean on the two leftover-map axes (ADR 0119), the
        # same basis the reconstruction above uses -- not the full-rank
        # Gabriel inner product.
        assert pair.leftover_distance == pytest.approx(float(map_distances[person, item]))
        assert pair.leftover_map_rank == rank
        _assert_persists_explained_share(pair)
    assert saw_nonzero_cross


def test_explained_share_stores_square_share_of_raw_residual() -> None:
    """e = R̂² / R² is stored; a share greater than 1 is not clamped."""
    assert leftover._leftover_map_explained_share(1.0, 2.0) == pytest.approx(4.0)
    assert leftover._leftover_map_explained_share(1.0, 0.0) == pytest.approx(0.0)
    assert leftover._leftover_map_explained_share(2.0, 2.0) == pytest.approx(1.0)
    assert leftover._leftover_map_explained_share(0.0, 0.0) == pytest.approx(0.0)
    assert leftover._leftover_map_explained_share(float("nan"), 1.0) is None
    assert leftover._leftover_map_explained_share(1.0, float("inf")) is None


def test_unexplained_share_stores_square_share_of_raw_residual() -> None:
    """s = U² / R² is stored; a share greater than 1 is not clamped."""
    assert leftover._leftover_map_unexplained_share(1.0, 2.0) == pytest.approx(1.0)
    assert leftover._leftover_map_unexplained_share(1.0, 3.0) == pytest.approx(4.0)
    assert leftover._leftover_map_unexplained_share(2.0, 2.0) == pytest.approx(0.0)
    assert leftover._leftover_map_unexplained_share(0.0, 0.0) == pytest.approx(0.0)
    assert leftover._leftover_map_unexplained_share(float("nan"), 1.0) is None
    assert leftover._leftover_map_unexplained_share(1.0, float("inf")) is None


def test_cross_share_stores_negative_finite_identity_remainder() -> None:
    """A negative identity remainder is stored, never omitted or clamped."""
    assert leftover._leftover_map_cross_share(1.0, 2.0) == pytest.approx(-4.0)
    assert leftover._leftover_map_cross_share(2.0, 2.0) == pytest.approx(0.0)
    assert leftover._leftover_map_cross_share(0.0, 0.0) == pytest.approx(0.0)
    assert leftover._leftover_map_cross_share(float("nan"), 1.0) is None
    assert leftover._leftover_map_cross_share(1.0, float("inf")) is None


def test_pad_map_axes_truncates_hidden_svd_components() -> None:
    """Axes after the second leftover-map axis do not enter reconstruction."""
    padded = leftover._pad_map_axes(np.array([[1.0, 2.0, 9.0]], dtype=np.float64))
    assert padded.shape == (1, 2)
    assert padded[0].tolist() == pytest.approx([1.0, 2.0])


def test_rejects_response_and_expectation_shape_mismatches() -> None:
    """Scientific inputs must match their declared post and criterion axes."""
    with pytest.raises(ValueError, match="matrix shape"):
        leftover_pairs_from_residual(
            ["post-a"],
            ("item-a",),
            np.zeros((2, 1), dtype=np.float64),
            np.zeros((2, 1), dtype=np.float64),
        )
    with pytest.raises(ValueError, match="expected shape"):
        leftover_pairs_from_residual(
            ["post-a"],
            ("item-a",),
            np.zeros((1, 1), dtype=np.float64),
            np.zeros((1, 2), dtype=np.float64),
        )


def test_nonfinite_map_distance_emits_no_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unusable factorization coordinate cannot become persisted distance."""
    monkeypatch.setattr(
        leftover,
        "_complete_case_positions",
        lambda *_args: (
            np.array([[np.inf]], dtype=np.float64),
            np.array([[-np.inf]], dtype=np.float64),
            np.array([1.0], dtype=np.float64),
        ),
    )
    pairs = leftover_pairs_from_residual(
        ["post-a"],
        ("item-a",),
        np.array([[1.0]], dtype=np.float64),
        np.array([[0.0]], dtype=np.float64),
    )
    assert pairs == ()


def test_empty_observation_mask_has_no_complete_case_axes() -> None:
    """The complete-case helpers preserve an empty scientific boundary."""
    observed = np.zeros((1, 1), dtype=bool)
    keep_person, keep_item = leftover._complete_case_masks(observed)
    assert not keep_person.any()
    assert not keep_item.any()
    person_pos, item_pos, singular = leftover._complete_case_positions(
        np.zeros((1, 1), dtype=np.float64),
        0.0,
        keep_person,
        keep_item,
    )
    assert person_pos is None
    assert item_pos is None
    assert singular.size == 0


def test_leftover_map_rank_rejects_negative_rank() -> None:
    """Python must reject a leftover-map rank excluded by the DB check."""
    with pytest.raises(ValueError, match="non-negative integer"):
        leftover._pair_from_candidate(
            PAIR_KIND_CLOSEST,
            (0.0, "public-post", "sales_lead_specificity", 0.0, 1.0, 1.0, None, None, None, None, None),
            -1,
        )


def test_small_finite_residual_keeps_cross_share() -> None:
    """A tiny-but-finite residual keeps its cross share.

    Squaring before the floor made the effective threshold 1e-6, so
    R = 1e-7 with reconstruction 5e-8 collapsed to an omitted badge
    even though x = 0.5 is well-defined (coderabbit review thread).
    """
    share = leftover._leftover_map_cross_share(1e-7, 5e-8)
    assert share == pytest.approx(0.5)
    unexplained_share = leftover._leftover_map_unexplained_share(1e-7, 5e-8)
    assert unexplained_share == pytest.approx(0.25)
    explained_share = leftover._leftover_map_explained_share(1e-7, 5e-8)
    assert explained_share == pytest.approx(0.25)
    assert explained_share + unexplained_share + share == pytest.approx(1.0)


def test_leftover_is_unavailable_without_a_complete_case_rectangle() -> None:
    """Observed cells alone cannot invent Gabriel positions or map coverage."""
    post_ids = ["post-a", "post-b"]
    item_codes = ("item-one", "item-two")
    matrix = np.array([[1.0, np.nan], [np.nan, 1.0]], dtype=np.float64)
    expected = np.zeros_like(matrix)

    assert leftover_pairs_from_residual(post_ids, item_codes, matrix, expected) == ()
    coverage = leftover_map_coverage_from_residual(post_ids, item_codes, matrix, expected)
    assert coverage.map_post_count == 0
    assert coverage.scored_post_count == 2
    assert coverage.map_item_count == 0
    assert coverage.scored_item_count == 2
    assert coverage.incomplete_post_count == 2
    assert coverage.incomplete_item_count == 2
