"""Leftover post–criterion pairs after the main-effect IRT (ADR 0048 / 0166).

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
    assert farthest.leftover_distance == pytest.approx(2.0 * np.sqrt(2.0), rel=1e-6)


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


def test_leftover_is_empty_without_observed_cells() -> None:
    """An entirely missing response matrix yields no invented pair."""
    post_ids = ["post-empty"]
    item_codes = ("item_one",)
    matrix = np.array([[np.nan]], dtype=np.float64)
    expected = np.array([[0.0]], dtype=np.float64)
    assert leftover_pairs_from_residual(post_ids, item_codes, matrix, expected) == ()


def test_rank_three_pair_distances_match_two_dimensional_gabriel_coords() -> None:
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
    assert person_full.shape[1] >= 3
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
        person = post_index[pair.post_id]
        item = item_index[pair.criterion_code]
        assert pair.leftover_distance == pytest.approx(float(map_distances[person, item]))
        assert pair.leftover_distance != pytest.approx(
            float(full_distances[person, item]), abs=1e-9
        )

    farthest_map = np.unravel_index(int(np.argmax(map_distances)), map_distances.shape)
    farthest = pairs[1]
    assert (post_index[farthest.post_id], item_index[farthest.criterion_code]) == farthest_map


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


def test_sparse_residual_uses_only_observed_cells_for_fallback_distance() -> None:
    """No complete rectangle still yields finite observed-cell distances."""
    matrix = np.array([[1.0, np.nan], [np.nan, -1.0]], dtype=np.float64)
    pairs = leftover_pairs_from_residual(
        ["post-a", "post-b"],
        ("item-a", "item-b"),
        matrix,
        np.zeros_like(matrix),
    )
    assert [(pair.post_id, pair.criterion_code) for pair in pairs] == [
        ("post-a", "item-a"),
        ("post-b", "item-b"),
    ]
    assert [pair.leftover_distance for pair in pairs] == pytest.approx([1.0, 1.0])


def test_nonfinite_map_distance_falls_back_to_centered_residual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unusable factorization coordinate cannot become persisted distance."""
    monkeypatch.setattr(
        leftover,
        "_complete_case_positions",
        lambda *_args: (
            np.array([[np.inf]], dtype=np.float64),
            np.array([[-np.inf]], dtype=np.float64),
        ),
    )
    pairs = leftover_pairs_from_residual(
        ["post-a"],
        ("item-a",),
        np.array([[1.0]], dtype=np.float64),
        np.array([[0.0]], dtype=np.float64),
    )
    assert [pair.leftover_distance for pair in pairs] == [0.0, 0.0]


def test_empty_observation_mask_has_no_complete_case_axes() -> None:
    """The complete-case helpers preserve an empty scientific boundary."""
    observed = np.zeros((1, 1), dtype=bool)
    keep_person, keep_item = leftover._complete_case_masks(observed)
    assert not keep_person.any()
    assert not keep_item.any()
    person_pos, item_pos = leftover._complete_case_positions(
        np.zeros((1, 1), dtype=np.float64),
        0.0,
        keep_person,
        keep_item,
    )
    assert person_pos is None
    assert item_pos is None


def test_pad_map_axes_truncates_hidden_svd_components() -> None:
    """Axes after the second leftover-map axis do not enter distance."""
    padded = leftover._pad_map_axes(np.array([[1.0, 2.0, 9.0]], dtype=np.float64))
    assert padded.shape == (1, 2)
    assert padded[0].tolist() == pytest.approx([1.0, 2.0])
