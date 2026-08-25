"""Consumer tests for the Rust-owned residual interaction-map boundary."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from lineageweave import leftover_pairs as leftover


def test_rust_map_projects_pairs_axes_and_coverage() -> None:
    """Rust evidence is attached to stable product identifiers without recomputation."""

    matrix = np.array([[2.0, -2.0], [-2.0, 2.0], [2.0, np.nan]])
    expected = np.zeros_like(matrix)
    post_ids = ["post-a", "post-b", "post-sparse"]
    item_codes = ("item-a", "item-b")

    pairs, axes = leftover.leftover_map_from_residual(
        post_ids, item_codes, matrix, expected
    )
    coverage = leftover.leftover_map_coverage_from_residual(
        post_ids, item_codes, matrix, expected
    )

    assert [pair.pair_kind for pair in pairs] == ["closest", "farthest"]
    assert {pair.post_id for pair in pairs} <= {"post-a", "post-b"}
    assert [axis.axis_index for axis in axes] == [1, 2]
    assert axes[0].leftover_share == pytest.approx(1.0)
    assert axes[1].leftover_share == pytest.approx(0.0)
    assert coverage == leftover.LeftoverMapCoverage(2, 3, 2, 2, 1, 0)
    for pair in pairs:
        assert pair.leftover_residual == pytest.approx(
            pair.observed_response - pair.expected_response
        )
        assert pair.leftover_map_unexplained is not None
        assert pair.leftover_map_reconstruction is not None


def test_rank_zero_keeps_deterministic_pairs_without_inventing_an_axis() -> None:
    """The product selection remains deterministic when Rust reports rank zero."""

    matrix = np.ones((2, 2))
    pairs, axes = leftover.leftover_map_from_residual(
        ["alpha", "beta"], ("one", "two"), matrix, matrix
    )

    assert [(pair.post_id, pair.criterion_code) for pair in pairs] == [
        ("alpha", "one"),
        ("beta", "two"),
    ]
    assert all(pair.leftover_map_rank == 0 for pair in pairs)
    assert all(pair.leftover_distance == pytest.approx(0.0) for pair in pairs)
    assert all(axis.leftover_share == pytest.approx(0.0) for axis in axes)


def test_no_complete_case_rectangle_returns_coverage_without_pairs() -> None:
    """Sparse evidence remains unavailable instead of becoming zero-filled math."""

    matrix = np.array([[1.0, np.nan], [np.nan, 1.0]])
    expected = np.zeros_like(matrix)
    post_ids = ["post-a", "post-b"]
    item_codes = ("item-a", "item-b")

    assert leftover.leftover_pairs_from_residual(
        post_ids, item_codes, matrix, expected
    ) == ()
    assert leftover.leftover_map_coverage_from_residual(
        post_ids, item_codes, matrix, expected
    ) == leftover.LeftoverMapCoverage(0, 2, 0, 2, 2, 2)


@pytest.mark.parametrize(
    ("matrix", "expected", "message"),
    [
        (np.zeros((1, 2)), np.zeros((1, 2)), "matrix shape"),
        (np.zeros((1, 1)), np.zeros((2, 1)), "expected shape"),
    ],
)
def test_identifier_and_matrix_shape_mismatch_fails_closed(
    matrix: np.ndarray, expected: np.ndarray, message: str
) -> None:
    """A result that cannot bind to product identifiers is rejected."""

    with pytest.raises(ValueError, match=message):
        leftover.leftover_map_from_residual(["post"], ("item",), matrix, expected)


def test_owner_failure_is_not_replaced_by_local_math(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing Rust result remains an explicit dependency failure."""

    def unavailable(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("compiled Rust core unavailable")

    monkeypatch.setattr(leftover, "residual_interaction_map", unavailable)
    with pytest.raises(RuntimeError, match="compiled Rust core unavailable"):
        leftover.leftover_map_from_residual(
            ["post"], ("item",), np.zeros((1, 1)), np.zeros((1, 1))
        )


def test_consumer_contains_no_factorization_formula() -> None:
    """Regression guard: numerical interaction-map policy stays upstream."""

    source = inspect.getsource(leftover)
    for forbidden in ("np.linalg", "np.dot", "np.sqrt", "np.mean", "np.sum"):
        assert forbidden not in source
