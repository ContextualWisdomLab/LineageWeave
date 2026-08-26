"""Project Rust-owned residual interaction maps into LineageWeave rows.

The numerical factorization belongs to :mod:`fast_mlsirm`. This module owns
only product identifiers, closest/farthest selection, and persistence-shaped
records (ADR 0208).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from fast_mlsirm import residual_interaction_map

PAIR_KIND_CLOSEST = "closest"
PAIR_KIND_FARTHEST = "farthest"
_LEFTOVER_MAP_AXES = 2


@dataclass(frozen=True)
class LeftoverPair:
    """One post-criterion pair on the leftover interaction map."""

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
    leftover_map_explained_share: float | None = None


@dataclass(frozen=True)
class LeftoverMapAxis:
    """Gabriel inertia for one leftover-map axis on a period report."""

    axis_index: int
    leftover_singular_value: float
    leftover_share: float


@dataclass(frozen=True)
class LeftoverMapCoverage:
    """Complete-case counts for the leftover interaction map."""

    map_post_count: int
    scored_post_count: int
    map_item_count: int
    scored_item_count: int
    incomplete_post_count: int
    incomplete_item_count: int


def leftover_pairs_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> tuple[LeftoverPair, ...]:
    """Return closest and farthest rows from the Rust-owned interaction map."""

    pairs, _axes = leftover_map_from_residual(post_ids, item_codes, matrix, expected)
    return pairs


def leftover_map_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> tuple[tuple[LeftoverPair, ...], tuple[LeftoverMapAxis, ...]]:
    """Project a Rust-owned two-axis Gabriel map into report records."""

    _validate_shapes(post_ids, item_codes, matrix, expected)
    result = residual_interaction_map(matrix, expected, axis_count=_LEFTOVER_MAP_AXES)
    axes = tuple(
        LeftoverMapAxis(
            axis_index=index + 1,
            leftover_singular_value=(
                float(result.singular_values[index])
                if index < len(result.singular_values)
                else 0.0
            ),
            leftover_share=(
                float(result.axis_shares[index])
                if index < len(result.axis_shares)
                else 0.0
            ),
        )
        for index in range(_LEFTOVER_MAP_AXES)
    )
    if not len(result.person_indices) or not len(result.item_indices):
        return (), ()

    rank = int(len(result.singular_values))
    candidates: list[tuple[float, str, str, float, float, float, float, float | None, float]] = []
    for local_person, person in enumerate(result.person_indices):
        for local_item, item in enumerate(result.item_indices):
            observed = float(matrix[int(person), int(item)])
            model_expected = float(expected[int(person), int(item)])
            residual = float(result.residual[local_person, local_item])
            cross_share = float(result.cross_share[local_person, local_item])
            candidates.append(
                (
                    float(result.distance[local_person, local_item]),
                    post_ids[int(person)],
                    item_codes[int(item)],
                    residual,
                    observed,
                    model_expected,
                    float(result.unexplained[local_person, local_item]),
                    cross_share if np.isfinite(cross_share) else None,
                    float(result.reconstruction[local_person, local_item]),
                )
            )
    closest = min(candidates, key=lambda row: (row[0], row[1], row[2]))
    farthest = max(candidates, key=lambda row: (row[0], row[1], row[2]))
    return (
        (_pair(PAIR_KIND_CLOSEST, closest, rank), _pair(PAIR_KIND_FARTHEST, farthest, rank)),
        axes,
    )


def leftover_map_coverage_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> LeftoverMapCoverage:
    """Project Rust-owned complete-case coverage into one report record."""

    _validate_shapes(post_ids, item_codes, matrix, expected)
    result = residual_interaction_map(matrix, expected, axis_count=_LEFTOVER_MAP_AXES)
    map_posts = len(result.person_indices)
    map_items = len(result.item_indices)
    return LeftoverMapCoverage(
        map_post_count=map_posts,
        scored_post_count=int(result.scored_person_count),
        map_item_count=map_items,
        scored_item_count=int(result.scored_item_count),
        incomplete_post_count=int(result.scored_person_count) - map_posts,
        incomplete_item_count=int(result.scored_item_count) - map_items,
    )


def _validate_shapes(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> None:
    """Reject identifier and matrix shapes that cannot be projected safely."""

    if matrix.shape != (len(post_ids), len(item_codes)):
        raise ValueError(
            f"matrix shape {matrix.shape} does not match {len(post_ids)} posts x {len(item_codes)} items"
        )
    if expected.shape != matrix.shape:
        raise ValueError(f"expected shape {expected.shape} does not match matrix {matrix.shape}")


def _pair(
    kind: str,
    row: tuple[float, str, str, float, float, float, float, float | None, float],
    rank: int,
) -> LeftoverPair:
    """Attach product identifiers to one Rust-computed candidate cell."""

    return LeftoverPair(
        pair_kind=kind,
        post_id=row[1],
        criterion_code=row[2],
        leftover_distance=row[0],
        leftover_residual=row[3],
        observed_response=row[4],
        expected_response=row[5],
        leftover_map_rank=rank,
        leftover_map_unexplained=row[6],
        leftover_map_cross_share=row[7],
        leftover_map_reconstruction=row[8],
    )
