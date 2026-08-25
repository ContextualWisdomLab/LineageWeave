"""Map fast-mlsirm residual interaction results to LineageWeave identifiers.

fast-mlsirm owns residual, complete-case admission, Gabriel factorization,
coordinates, axis inertia, distances, reconstruction, unexplained residual,
and cross-share arithmetic. This module owns only product identifiers and the
closest/farthest selection persisted by ADR 0048.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from fast_mlsirm import residual_interaction_map

PAIR_KIND_CLOSEST = "closest"
PAIR_KIND_FARTHEST = "farthest"
_LEFTOVER_MAP_AXES = 2


@dataclass(frozen=True)
class LeftoverPair:
    """One post–criterion pair on the leftover interaction map."""

    pair_kind: str
    post_id: str
    criterion_code: str
    leftover_distance: float
    leftover_residual: float
    observed_response: float
    expected_response: float
    leftover_map_rank: int
    leftover_map_unexplained: float | None = None
    leftover_map_cross_share: float | None = None
    leftover_map_reconstruction: float | None = None


@dataclass(frozen=True)
class LeftoverMapPerson:
    """One post's leftover-map coordinates ξ after IRT main effects."""

    post_id: str
    axis_one: float
    axis_two: float


@dataclass(frozen=True)
class LeftoverMapItem:
    """One criterion's leftover-map coordinates ζ after IRT main effects."""

    criterion_code: str
    axis_one: float
    axis_two: float


@dataclass(frozen=True)
class LeftoverMapAxis:
    """Gabriel inertia for one leftover-map axis on a period report."""

    axis_index: int
    leftover_singular_value: float
    leftover_share: float


@dataclass(frozen=True)
class LeftoverInteractionMap:
    """Mapped points, axis evidence, and closest/farthest observed pairs."""

    pairs: tuple[LeftoverPair, ...]
    persons: tuple[LeftoverMapPerson, ...]
    items: tuple[LeftoverMapItem, ...]
    axes: tuple[LeftoverMapAxis, ...]


@dataclass(frozen=True)
class LeftoverMapCoverage:
    """Complete-case counts returned by fast-mlsirm."""

    map_post_count: int
    scored_post_count: int
    map_item_count: int
    scored_item_count: int
    incomplete_post_count: int
    incomplete_item_count: int


def _validate_identifiers(
    post_ids: list[str], item_codes: tuple[str, ...], matrix: np.ndarray
) -> None:
    """Require identifier cardinality to match the supplied response matrix."""
    expected_shape = (len(post_ids), len(item_codes))
    if matrix.shape != expected_shape:
        raise ValueError(
            f"matrix shape {matrix.shape} does not match "
            f"{len(post_ids)} posts × {len(item_codes)} items"
        )


def _optional_finite(value: float) -> float | None:
    """Translate the upstream nullable-array NaN representation to Optional."""
    return float(value) if np.isfinite(value) else None


def _upstream_map_coordinates_are_finite(result: Any) -> bool:
    """Return whether every required upstream map coordinate is persistable."""
    return all(
        np.isfinite(values).all()
        for values in (
            result.person_coordinates,
            result.item_coordinates,
            result.singular_values,
            result.axis_shares,
        )
    )


def _upstream_map_has_expected_shape(result: Any) -> bool:
    """Return whether the provider envelope matches the pinned two-axis contract."""
    person_count = result.person_indices.size
    item_count = result.item_indices.size
    return (
        result.person_indices.ndim == 1
        and result.item_indices.ndim == 1
        and result.person_coordinates.shape == (person_count, _LEFTOVER_MAP_AXES)
        and result.item_coordinates.shape == (item_count, _LEFTOVER_MAP_AXES)
        and result.axis_shares.shape == (_LEFTOVER_MAP_AXES,)
        and result.singular_values.ndim == 1
        and all(
            values.shape == (person_count, item_count)
            for values in (
                result.residual,
                result.distance,
                result.reconstruction,
                result.unexplained,
                result.cross_share,
            )
        )
    )


def _upstream_map_indices_are_valid(
    result: Any, post_count: int, item_count: int
) -> bool:
    """Require unique integer indices inside the supplied identifier bounds."""
    return all(
        np.issubdtype(indices.dtype, np.integer)
        and np.unique(indices).size == indices.size
        and (indices.size == 0 or (indices.min() >= 0 and indices.max() < bound))
        for indices, bound in (
            (result.person_indices, post_count),
            (result.item_indices, item_count),
        )
    )


def leftover_pairs_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> tuple[LeftoverPair, ...]:
    """Return the product-selected closest and farthest upstream map cells."""
    return leftover_map_from_residual(post_ids, item_codes, matrix, expected).pairs


def leftover_map_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> LeftoverInteractionMap:
    """Map fast-mlsirm's two-axis residual interaction result to product IDs."""
    _validate_identifiers(post_ids, item_codes, matrix)
    result = residual_interaction_map(matrix, expected, axis_count=_LEFTOVER_MAP_AXES)
    if result.person_indices.size == 0 or result.item_indices.size == 0:
        return LeftoverInteractionMap(pairs=(), persons=(), items=(), axes=())
    if not _upstream_map_has_expected_shape(result):
        return LeftoverInteractionMap(pairs=(), persons=(), items=(), axes=())
    if not _upstream_map_indices_are_valid(result, len(post_ids), len(item_codes)):
        return LeftoverInteractionMap(pairs=(), persons=(), items=(), axes=())
    if not _upstream_map_coordinates_are_finite(result):
        return LeftoverInteractionMap(pairs=(), persons=(), items=(), axes=())

    persons = tuple(
        LeftoverMapPerson(
            post_id=post_ids[int(person)],
            axis_one=float(result.person_coordinates[local, 0]),
            axis_two=float(result.person_coordinates[local, 1]),
        )
        for local, person in enumerate(result.person_indices)
    )
    items = tuple(
        LeftoverMapItem(
            criterion_code=item_codes[int(item)],
            axis_one=float(result.item_coordinates[local, 0]),
            axis_two=float(result.item_coordinates[local, 1]),
        )
        for local, item in enumerate(result.item_indices)
    )
    axes = tuple(
        LeftoverMapAxis(
            axis_index=axis + 1,
            leftover_singular_value=float(
                result.singular_values[axis]
                if axis < result.singular_values.size
                else 0.0
            ),
            leftover_share=float(result.axis_shares[axis]),
        )
        for axis in range(_LEFTOVER_MAP_AXES)
    )
    rank = int(result.singular_values.size)
    candidates: list[tuple[float, str, str, LeftoverPair]] = []
    for local_person, person in enumerate(result.person_indices):
        person_index = int(person)
        for local_item, item in enumerate(result.item_indices):
            item_index = int(item)
            distance = float(result.distance[local_person, local_item])
            residual = float(result.residual[local_person, local_item])
            observed = float(matrix[person_index, item_index])
            expected_value = float(expected[person_index, item_index])
            if not all(
                np.isfinite(value)
                for value in (distance, residual, observed, expected_value)
            ):
                continue
            if residual != observed - expected_value:
                continue
            candidates.append(
                (
                    distance,
                    post_ids[person_index],
                    item_codes[item_index],
                    LeftoverPair(
                        pair_kind="",
                        post_id=post_ids[person_index],
                        criterion_code=item_codes[item_index],
                        leftover_distance=distance,
                        leftover_residual=residual,
                        observed_response=observed,
                        expected_response=expected_value,
                        leftover_map_rank=rank,
                        leftover_map_unexplained=_optional_finite(
                            result.unexplained[local_person, local_item]
                        ),
                        leftover_map_cross_share=_optional_finite(
                            result.cross_share[local_person, local_item]
                        ),
                        leftover_map_reconstruction=_optional_finite(
                            result.reconstruction[local_person, local_item]
                        ),
                    ),
                )
            )
    pairs: tuple[LeftoverPair, ...] = ()
    if candidates:
        closest = min(candidates, key=lambda row: row[:3])[3]
        farthest = max(candidates, key=lambda row: row[:3])[3]
        pairs = (
            replace(closest, pair_kind=PAIR_KIND_CLOSEST),
            replace(farthest, pair_kind=PAIR_KIND_FARTHEST),
        )
    return LeftoverInteractionMap(
        pairs=pairs,
        persons=persons,
        items=items,
        axes=axes,
    )


def leftover_map_coverage_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> LeftoverMapCoverage:
    """Map fast-mlsirm's scored and complete-case coverage counts."""
    _validate_identifiers(post_ids, item_codes, matrix)
    result = residual_interaction_map(matrix, expected, axis_count=_LEFTOVER_MAP_AXES)
    map_post_count = int(result.person_indices.size)
    map_item_count = int(result.item_indices.size)
    return LeftoverMapCoverage(
        map_post_count=map_post_count,
        scored_post_count=result.scored_person_count,
        map_item_count=map_item_count,
        scored_item_count=result.scored_item_count,
        incomplete_post_count=result.scored_person_count - map_post_count,
        incomplete_item_count=result.scored_item_count - map_item_count,
    )
