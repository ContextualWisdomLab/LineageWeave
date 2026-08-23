"""Jeon leftover post–criterion pairs after a main-effect IRT (ADR 0048).

Does not import ``fast_mlsirm`` or ``period_report``. A Gabriel biplot
of the residual ``R = Y − E[Y|θ, item]`` supplies person and item
positions. Missing response cells are excluded from the factorization;
they are never treated as zero residuals. Rank-0 and rank-1 maps pad
the unused leftover-map axis with zero rather than inventing a second
component.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PAIR_KIND_CLOSEST = "closest"
PAIR_KIND_FARTHEST = "farthest"
_LEFTOVER_SINGULAR_FLOOR = 1e-12
_LEFTOVER_MAP_AXES = 2


@dataclass(frozen=True)
class LeftoverPair:
    """One post–criterion pair on the leftover interaction map."""

    pair_kind: str
    post_id: str
    criterion_code: str
    leftover_distance: float
    leftover_residual: float


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
    effects (Gabriel, 1971). Only observed cells become pairs. A rank-0
    residual still emits a stable closest/farthest pair so seed is not
    empty; it does not invent a leftover score. Unused map axes stay
    zero when the residual rank is below two.
    """
    if matrix.shape != (len(post_ids), len(item_codes)):
        raise ValueError(
            f"matrix shape {matrix.shape} does not match {len(post_ids)} posts × {len(item_codes)} items"
        )
    if expected.shape != matrix.shape:
        raise ValueError(f"expected shape {expected.shape} does not match matrix {matrix.shape}")

    residual = matrix.astype(np.float64) - expected.astype(np.float64)
    observed_mask = (~np.isnan(matrix)) & np.isfinite(residual)
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
    person_pos, item_pos = _complete_case_positions(residual, center, keep_person, keep_item)
    persons: tuple[LeftoverMapPerson, ...] = ()
    items: tuple[LeftoverMapItem, ...] = ()
    candidates: list[tuple[float, str, str, float]] = []
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
                np.linalg.norm(person_pos[local_person[person]] - item_pos[local_item[item]])
            )
            if not np.isfinite(distance):
                continue
            candidates.append(
                (
                    max(distance, 0.0),
                    post_ids[person],
                    item_codes[item],
                    float(residual[person, item]),
                )
            )
    if not candidates:
        for person, item in observed:
            distance = abs(float(residual[person, item]) - center)
            candidates.append(
                (
                    max(distance, 0.0),
                    post_ids[person],
                    item_codes[item],
                    float(residual[person, item]),
                )
            )
    closest = min(candidates, key=lambda row: (row[0], row[1], row[2]))
    farthest = max(candidates, key=lambda row: (row[0], row[1], row[2]))
    return LeftoverInteractionMap(
        pairs=(
            LeftoverPair(
                pair_kind=PAIR_KIND_CLOSEST,
                post_id=closest[1],
                criterion_code=closest[2],
                leftover_distance=closest[0],
                leftover_residual=closest[3],
            ),
            LeftoverPair(
                pair_kind=PAIR_KIND_FARTHEST,
                post_id=farthest[1],
                criterion_code=farthest[2],
                leftover_distance=farthest[0],
                leftover_residual=farthest[3],
            ),
        ),
        persons=persons,
        items=items,
    )


def _complete_case_masks(observed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop incomplete rows, then incomplete columns among remaining rows."""
    keep_person = observed.any(axis=1)
    keep_item = observed.any(axis=0)
    if np.any(keep_item):
        keep_person = keep_person & observed[:, keep_item].all(axis=1)
    if np.any(keep_person):
        keep_item = keep_item & observed[keep_person, :].all(axis=0)
    return keep_person, keep_item


def _complete_case_positions(
    residual: np.ndarray,
    center: float,
    keep_person: np.ndarray,
    keep_item: np.ndarray,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Gabriel coordinates on the complete-case residual rectangle only."""
    person_index = np.flatnonzero(keep_person)
    item_index = np.flatnonzero(keep_item)
    if person_index.size == 0 or item_index.size == 0:
        return None, None
    filled = residual[np.ix_(person_index, item_index)] - center
    return _leftover_map_positions(filled)


def _leftover_map_positions(filled: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Gabriel biplot coordinates; rank-0 residuals collapse to the origin."""
    n_persons, n_items = filled.shape
    if n_persons == 0 or n_items == 0 or not np.any(np.abs(filled) > _LEFTOVER_SINGULAR_FLOOR):
        return (
            np.zeros((n_persons, 1), dtype=np.float64),
            np.zeros((n_items, 1), dtype=np.float64),
        )
    left, singular, right = np.linalg.svd(filled, full_matrices=False)
    keep = singular > _LEFTOVER_SINGULAR_FLOOR
    if not np.any(keep):
        return (
            np.zeros((n_persons, 1), dtype=np.float64),
            np.zeros((n_items, 1), dtype=np.float64),
        )
    scale = np.sqrt(singular[keep])
    person_pos = left[:, keep] * scale
    item_pos = right[keep, :].T * scale
    return person_pos, item_pos


def _pad_map_axes(positions: np.ndarray) -> np.ndarray:
    """Pad Gabriel coordinates to two leftover-map axes; unused axes stay 0."""
    padded = np.zeros((positions.shape[0], _LEFTOVER_MAP_AXES), dtype=np.float64)
    if positions.size == 0:
        return padded
    width = min(_LEFTOVER_MAP_AXES, positions.shape[1])
    padded[:, :width] = positions[:, :width]
    return padded
