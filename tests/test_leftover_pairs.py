"""LineageWeave's identifier adapter for fast-mlsirm interaction maps."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from lineageweave import leftover_pairs as leftover


def _upstream_result() -> SimpleNamespace:
    """Return fixed provider evidence; this repository does not recompute it."""
    return SimpleNamespace(
        person_indices=np.array([0, 1]),
        item_indices=np.array([0, 1]),
        scored_person_count=3,
        scored_item_count=2,
        person_coordinates=np.array([[0.0, 0.0], [2.0, 0.0]]),
        item_coordinates=np.array([[0.1, 0.0], [-1.0, 0.0]]),
        singular_values=np.array([3.0]),
        axis_shares=np.array([1.0, 0.0]),
        residual=np.array([[0.5, 0.25], [-0.5, -1.0]]),
        distance=np.array([[0.1, 1.0], [1.9, 3.0]]),
        reconstruction=np.array([[0.375, 0.125], [-0.25, -0.75]]),
        unexplained=np.array([[0.125, 0.125], [-0.25, -0.25]]),
        cross_share=np.array([[0.375, 0.5], [0.5, 0.375]]),
    )


def _matching_inputs() -> tuple[np.ndarray, np.ndarray]:
    """Return observed and expected arrays consistent with provider residuals."""
    expected = np.full((2, 2), 2.0)
    observed = expected + _upstream_result().residual
    return observed, expected


def test_maps_upstream_evidence_and_selects_closest_and_farthest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only product IDs and closest/farthest selection are added locally."""
    calls: list[tuple[np.ndarray, np.ndarray, int]] = []

    def provider(matrix: np.ndarray, expected: np.ndarray, *, axis_count: int):
        calls.append((matrix, expected, axis_count))
        return _upstream_result()

    monkeypatch.setattr(leftover, "residual_interaction_map", provider)
    matrix = np.array([[2.5, 2.25], [1.5, 1.0], [1.0, np.nan]])
    expected = np.array([[2.0, 2.0], [2.0, 2.0], [1.0, 1.0]])

    interaction_map = leftover.leftover_map_from_residual(
        ["public-post", "spec-post", "sparse-post"],
        ("sales_lead_specificity", "general_sentiment_negative"),
        matrix,
        expected,
    )

    assert len(calls) == 1
    assert calls[0][0] is matrix
    assert calls[0][1] is expected
    assert calls[0][2] == 2
    assert [person.post_id for person in interaction_map.persons] == [
        "public-post",
        "spec-post",
    ]
    assert [item.criterion_code for item in interaction_map.items] == [
        "sales_lead_specificity",
        "general_sentiment_negative",
    ]
    assert [axis.leftover_share for axis in interaction_map.axes] == pytest.approx(
        [1.0, 0.0]
    )
    closest, farthest = interaction_map.pairs
    assert closest.pair_kind == leftover.PAIR_KIND_CLOSEST
    assert (closest.post_id, closest.criterion_code) == (
        "public-post",
        "sales_lead_specificity",
    )
    assert closest.leftover_distance == pytest.approx(0.1)
    assert closest.leftover_residual == pytest.approx(0.5)
    assert closest.leftover_map_reconstruction == pytest.approx(0.375)
    assert closest.leftover_map_unexplained == pytest.approx(0.125)
    assert closest.leftover_map_cross_share == pytest.approx(0.375)
    assert farthest.pair_kind == leftover.PAIR_KIND_FARTHEST
    assert (farthest.post_id, farthest.criterion_code) == (
        "spec-post",
        "general_sentiment_negative",
    )
    assert farthest.leftover_distance == pytest.approx(3.0)
    assert farthest.leftover_map_rank == 1
    assert farthest.observed_response == pytest.approx(1.0)
    assert farthest.expected_response == pytest.approx(2.0)
    assert farthest.leftover_map_cross_share == pytest.approx(0.375)


def test_pair_projection_reuses_the_mapped_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pairs-only compatibility API adds no second provider contract."""
    monkeypatch.setattr(
        leftover,
        "residual_interaction_map",
        lambda *_args, **_kwargs: _upstream_result(),
    )
    observed, expected = _matching_inputs()
    pairs = leftover.leftover_pairs_from_residual(
        ["post-a", "post-b"],
        ("item-a", "item-b"),
        observed,
        expected,
    )
    assert [pair.pair_kind for pair in pairs] == [
        leftover.PAIR_KIND_CLOSEST,
        leftover.PAIR_KIND_FARTHEST,
    ]


def test_maps_upstream_coverage_without_rederiving_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scored and complete-case counts remain fast-mlsirm evidence."""
    monkeypatch.setattr(
        leftover,
        "residual_interaction_map",
        lambda *_args, **_kwargs: _upstream_result(),
    )
    coverage = leftover.leftover_map_coverage_from_residual(
        ["post-a", "post-b", "post-c"],
        ("item-a", "item-b"),
        np.ones((3, 2)),
        np.zeros((3, 2)),
    )
    assert coverage == leftover.LeftoverMapCoverage(
        map_post_count=2,
        scored_post_count=3,
        map_item_count=2,
        scored_item_count=2,
        incomplete_post_count=1,
        incomplete_item_count=0,
    )


def test_empty_upstream_map_does_not_invent_product_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No admitted rectangle means no points, axes, or selected pairs."""
    result = _upstream_result()
    result.person_indices = np.array([], dtype=np.int64)
    result.item_indices = np.array([], dtype=np.int64)
    monkeypatch.setattr(
        leftover, "residual_interaction_map", lambda *_args, **_kwargs: result
    )
    interaction_map = leftover.leftover_map_from_residual(
        ["post-a"], ("item-a",), np.ones((1, 1)), np.zeros((1, 1))
    )
    assert interaction_map == leftover.LeftoverInteractionMap(
        pairs=(), persons=(), items=(), axes=()
    )


def test_nullable_cross_share_remains_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An upstream NaN is translated to None rather than a fabricated score."""
    result = _upstream_result()
    result.cross_share[0, 0] = np.nan
    monkeypatch.setattr(
        leftover, "residual_interaction_map", lambda *_args, **_kwargs: result
    )
    observed, expected = _matching_inputs()
    interaction_map = leftover.leftover_map_from_residual(
        ["post-a", "post-b"],
        ("item-a", "item-b"),
        observed,
        expected,
    )
    assert interaction_map.pairs[0].leftover_map_cross_share is None


def test_non_finite_upstream_values_never_enter_selection_or_map_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-finite provider evidence remains unavailable instead of persisting."""
    result = _upstream_result()
    result.distance[0, 0] = np.nan
    result.residual[1, 1] = np.inf
    result.unexplained[0, 1] = np.nan
    result.reconstruction[0, 1] = np.inf
    monkeypatch.setattr(
        leftover, "residual_interaction_map", lambda *_args, **_kwargs: result
    )
    observed, expected = _matching_inputs()
    interaction_map = leftover.leftover_map_from_residual(
        ["post-a", "post-b"],
        ("item-a", "item-b"),
        observed,
        expected,
    )
    assert [pair.leftover_distance for pair in interaction_map.pairs] == [1.0, 1.9]
    assert interaction_map.pairs[0].leftover_map_unexplained is None
    assert interaction_map.pairs[0].leftover_map_reconstruction is None

    result.person_coordinates[0, 0] = np.nan
    assert leftover.leftover_map_from_residual(
        ["post-a", "post-b"],
        ("item-a", "item-b"),
        observed,
        expected,
    ) == leftover.LeftoverInteractionMap(pairs=(), persons=(), items=(), axes=())


def test_malformed_rank_one_provider_shape_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-padded rank-one envelope cannot reach two-axis indexing."""
    result = _upstream_result()
    result.person_coordinates = result.person_coordinates[:, :1]
    result.item_coordinates = result.item_coordinates[:, :1]
    result.axis_shares = result.axis_shares[:1]
    monkeypatch.setattr(
        leftover, "residual_interaction_map", lambda *_args, **_kwargs: result
    )
    observed, expected = _matching_inputs()
    assert leftover.leftover_map_from_residual(
        ["post-a", "post-b"], ("item-a", "item-b"), observed, expected
    ) == leftover.LeftoverInteractionMap(pairs=(), persons=(), items=(), axes=())


def test_inconsistent_provider_residual_is_excluded_before_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only cells satisfying the auditable R equals Y minus E identity persist."""
    result = _upstream_result()
    result.residual[0, 0] = 0.75
    monkeypatch.setattr(
        leftover, "residual_interaction_map", lambda *_args, **_kwargs: result
    )
    observed, expected = _matching_inputs()
    interaction_map = leftover.leftover_map_from_residual(
        ["post-a", "post-b"], ("item-a", "item-b"), observed, expected
    )
    assert [
        (pair.post_id, pair.criterion_code) for pair in interaction_map.pairs
    ] == [("post-a", "item-b"), ("post-b", "item-b")]


def test_rejects_identifier_shape_mismatch_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Product identifiers must address every supplied response cell."""
    called = False

    def provider(*_args, **_kwargs):
        nonlocal called
        called = True
        return _upstream_result()

    monkeypatch.setattr(leftover, "residual_interaction_map", provider)
    with pytest.raises(ValueError, match="matrix shape"):
        leftover.leftover_map_from_residual(
            ["post-a"], ("item-a",), np.ones((2, 1)), np.zeros((2, 1))
        )
    assert not called


def test_upstream_rejects_expectation_shape_mismatch() -> None:
    """The supplier owns scientific array-shape validation."""
    with pytest.raises(ValueError, match="same two-dimensional shape"):
        leftover.leftover_map_from_residual(
            ["post-a"], ("item-a",), np.ones((1, 1)), np.zeros((1, 2))
        )
