"""Jeon leftover post–criterion pairs after a main-effect IRT.

Implements ADR 0048 as amended by ADR 0119, ADR 0121, ADR 0163, and ADR 0164.

Does not import ``fast_mlsirm`` or ``period_report``. A Gabriel biplot
of the residual ``R = Y − E[Y|θ, item]`` supplies person and item
positions. Missing response cells are excluded from the factorization;
they are never treated as zero residuals. Each pair names observed
``Y`` and expected ``E`` so residual always reconciles to ``Y − E``.
Pair distances are Euclidean
on the two leftover-map axes (Jeon et al., 2021); unused axes pad with
zero rather than inventing a second component, and hidden SVD axes
after the second are dropped. Each pair also names the full leftover-map
rank so a rank-0 collapse is not read as leftover structure. Person and
item leftover-map coordinates ξ / ζ are exposed on
``LeftoverInteractionMap`` for callers that persist the full biplot
(ADR 0121).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PAIR_KIND_CLOSEST = "closest"
PAIR_KIND_FARTHEST = "farthest"
_LEFTOVER_SINGULAR_FLOOR = 1e-12
_RESIDUAL_RECONCILE_TOLERANCE = 1e-6
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
class LeftoverInteractionMap:
    """Gabriel leftover-map points plus the closest and farthest observed pairs."""

    pairs: tuple[LeftoverPair, ...]
    persons: tuple[LeftoverMapPerson, ...]
    items: tuple[LeftoverMapItem, ...]


def leftover_pairs_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> tuple[LeftoverPair, ...]:
    """Closest and farthest leftover-map pairs from residual SVD biplot."""
    return leftover_map_from_residual(post_ids, item_codes, matrix, expected).pairs


def leftover_map_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> LeftoverInteractionMap:
    """Person and item leftover-map coordinates plus closest/farthest pairs.

    Jeon et al. (2021) leftover interaction is ``−γ‖ξ_p − ζ_i‖``. This
    estimator places persons and items from the residual after IRT main
    effects (Gabriel, 1971). Only observed cells become pairs. Distances
    use the two leftover-map axes; a rank-0 residual still emits a
    stable closest/farthest pair so seed is not empty and does not
    invent a leftover score. Unused map axes stay zero when the
    residual rank is below two. Stored residual equals observed ``Y``
    minus expected ``E[Y|θ, item]``. Stored leftover-map rank is the
    number of Gabriel singular values above the floor.
    """
    if matrix.shape != (len(post_ids), len(item_codes)):
        raise ValueError(
            f"matrix shape {matrix.shape} does not match {len(post_ids)} posts × {len(item_codes)} items"
        )
    if expected.shape != matrix.shape:
        raise ValueError(f"expected shape {expected.shape} does not match matrix {matrix.shape}")

    residual = matrix.astype(np.float64) - expected.astype(np.float64)
    observed_mask = (~np.isnan(matrix)) & np.isfinite(residual) & np.isfinite(expected)
    observed: list[tuple[int, int]] = [
        (person, item)
        for person in range(matrix.shape[0])
        for item in range(matrix.shape[1])
        if observed_mask[person, item]
    ]
    if not observed:
        return LeftoverInteractionMap(pairs=(), persons=(), items=())

    keep_person, keep_item = _complete_case_masks(observed_mask)
    person_index = np.flatnonzero(keep_person)
    item_index = np.flatnonzero(keep_item)
    if person_index.size > 0 and item_index.size > 0:
        center = float(np.mean(residual[np.ix_(person_index, item_index)]))
    else:
        center = float(np.mean([residual[person, item] for person, item in observed]))
    person_pos, item_pos, leftover_map_rank = _complete_case_positions(
        residual, center, keep_person, keep_item
    )
    persons: tuple[LeftoverMapPerson, ...] = ()
    items: tuple[LeftoverMapItem, ...] = ()
    candidates: list[tuple[float, str, str, float, float, float]] = []
    if person_pos is not None and item_pos is not None:
        person_index = np.flatnonzero(keep_person)
        item_index = np.flatnonzero(keep_item)
        person_xy = _pad_map_axes(person_pos)
        item_xy = _pad_map_axes(item_pos)
        persons = tuple(
            LeftoverMapPerson(
                post_id=post_ids[int(person)],
                axis_one=float(person_xy[local, 0]),
                axis_two=float(person_xy[local, 1]),
            )
            for local, person in enumerate(person_index)
        )
        items = tuple(
            LeftoverMapItem(
                criterion_code=item_codes[int(item)],
                axis_one=float(item_xy[local, 0]),
                axis_two=float(item_xy[local, 1]),
            )
            for local, item in enumerate(item_index)
        )
        local_person = {int(person): local for local, person in enumerate(person_index)}
        local_item = {int(item): local for local, item in enumerate(item_index)}
        for person, item in observed:
            if person not in local_person or item not in local_item:
                continue
            distance = float(
                np.linalg.norm(person_xy[local_person[person]] - item_xy[local_item[item]])
            )
            if not np.isfinite(distance):
                continue
            candidates.append(
                _candidate_row(post_ids, item_codes, matrix, expected, residual, person, item, distance)
            )
    if not candidates:
        leftover_map_rank = 0
        for person, item in observed:
            distance = abs(float(residual[person, item]) - center)
            candidates.append(
                _candidate_row(
                    post_ids,
                    item_codes,
                    matrix,
                    expected,
                    residual,
                    person,
                    item,
                    max(distance, 0.0),
                )
            )
    closest = min(candidates, key=lambda row: (row[0], row[1], row[2]))
    farthest = max(candidates, key=lambda row: (row[0], row[1], row[2]))
    return LeftoverInteractionMap(
        pairs=(
            _pair_from_candidate(PAIR_KIND_CLOSEST, closest, leftover_map_rank),
            _pair_from_candidate(PAIR_KIND_FARTHEST, farthest, leftover_map_rank),
        ),
        persons=persons,
        items=items,
    )


def _candidate_row(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
    residual: np.ndarray,
    person: int,
    item: int,
    distance: float,
) -> tuple[float, str, str, float, float, float]:
    """One observed leftover cell: distance, ids, residual, Y, E."""
    leftover_residual = float(residual[person, item])
    observed_response = float(matrix[person, item])
    expected_response = float(expected[person, item])
    if abs(leftover_residual - (observed_response - expected_response)) >= _RESIDUAL_RECONCILE_TOLERANCE:
        raise ValueError("leftover residual must equal observed Y minus expected E")
    return (
        max(distance, 0.0),
        post_ids[person],
        item_codes[item],
        leftover_residual,
        observed_response,
        expected_response,
    )


def _pair_from_candidate(
    pair_kind: str,
    row: tuple[float, str, str, float, float, float],
    leftover_map_rank: int,
) -> LeftoverPair:
    """Build a leftover pair from a candidate row."""
    if leftover_map_rank < 0:
        raise ValueError("leftover map rank must be a non-negative integer")
    return LeftoverPair(
        pair_kind=pair_kind,
        post_id=row[1],
        criterion_code=row[2],
        leftover_distance=row[0],
        leftover_residual=row[3],
        observed_response=row[4],
        expected_response=row[5],
        leftover_map_rank=leftover_map_rank,
    )


def _complete_case_masks(observed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop incomplete rows, then incomplete columns among remaining rows."""
    keep_person = observed.any(axis=1)
    keep_item = observed.any(axis=0)
    keep_person = keep_person & observed[:, keep_item].all(axis=1)
    if np.any(keep_person):
        keep_item = keep_item & observed[keep_person, :].all(axis=0)
    return keep_person, keep_item


def _complete_case_positions(
    residual: np.ndarray,
    center: float,
    keep_person: np.ndarray,
    keep_item: np.ndarray,
) -> tuple[np.ndarray | None, np.ndarray | None, int]:
    """Gabriel coordinates on the complete-case residual rectangle only."""
    person_index = np.flatnonzero(keep_person)
    item_index = np.flatnonzero(keep_item)
    if person_index.size == 0 or item_index.size == 0:
        return None, None, 0
    filled = residual[np.ix_(person_index, item_index)] - center
    return _leftover_map_positions(filled)


def _leftover_map_positions(filled: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    """Gabriel coordinates ordered by descending singular value.

    NumPy's SVD contract returns singular values largest-first, so filtering
    by the numerical floor preserves a prefix and the first two columns remain
    the two leading leftover-map axes. Rank-0 residuals collapse to the origin.
    """
    n_persons, n_items = filled.shape
    if not np.any(np.abs(filled) > _LEFTOVER_SINGULAR_FLOOR):
        return (
            np.zeros((n_persons, 1), dtype=np.float64),
            np.zeros((n_items, 1), dtype=np.float64),
            0,
        )
    left, singular, right = np.linalg.svd(filled, full_matrices=False)
    keep = singular > _LEFTOVER_SINGULAR_FLOOR
    leftover_map_rank = int(np.count_nonzero(keep))
    scale = np.sqrt(singular[keep])
    person_pos = left[:, keep] * scale
    item_pos = right[keep, :].T * scale
    return person_pos, item_pos, leftover_map_rank


def _pad_map_axes(positions: np.ndarray) -> np.ndarray:
    """Pad or truncate Gabriel coordinates to two leftover-map axes."""
    padded = np.zeros((positions.shape[0], _LEFTOVER_MAP_AXES), dtype=np.float64)
    width = min(_LEFTOVER_MAP_AXES, positions.shape[1])
    padded[:, :width] = positions[:, :width]
    return padded
