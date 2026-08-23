"""Jeon leftover post–criterion pairs after a main-effect IRT.

Implements ADR 0048 as amended by ADR 0182.

Does not import ``fast_mlsirm`` or ``period_report``. A Gabriel biplot
of the residual ``R = Y − E[Y|θ, item]`` supplies person and item
positions. Missing response cells are excluded from the factorization;
they are never treated as zero residuals. Each map pair names
unexplained leftover ``U = R − R̂`` so the leftover cell the two-axis
map does not reconstruct is not confused with leftover residual ``R``,
two-axis reconstruction ``R̂ = ξ_{1:2} · ζ_{1:2}``, or leftover-map
distance ``d``. Reconstruction is computed internally and is not
persisted.
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
    leftover_map_unexplained: float | None = None


def leftover_pairs_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> tuple[LeftoverPair, ...]:
    """Closest and farthest leftover-map pairs from residual SVD biplot.

    Jeon et al. (2021) leftover interaction is ``−γ‖ξ_p − ζ_i‖``. This
    estimator places persons and items from the residual after IRT main
    effects (Gabriel, 1971). Only observed cells become pairs. A rank-0
    residual still emits a stable closest/farthest pair so seed is not
    empty; it does not invent a leftover score. When Gabriel coordinates
    exist, unexplained leftover ``U = R − R̂`` names the leftover cell
    the two-axis map does not reconstruct. ``R̂ = ξ_{1:2} · ζ_{1:2}``
    stays internal and is never persisted. Fallback pairs (no
    complete-case map) omit unexplained leftover rather than fabricating
    one. Leftover-map distance stays full-rank Euclidean.
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
        return ()

    keep_person, keep_item = _complete_case_masks(observed_mask)
    person_index = np.flatnonzero(keep_person)
    item_index = np.flatnonzero(keep_item)
    if person_index.size > 0 and item_index.size > 0:
        center = float(np.mean(residual[np.ix_(person_index, item_index)]))
    else:
        center = float(np.mean([residual[person, item] for person, item in observed]))
    person_pos, item_pos = _complete_case_positions(residual, center, keep_person, keep_item)
    candidates: list[tuple[float, str, str, float, float | None]] = []
    if person_pos is not None and item_pos is not None:
        person_index = np.flatnonzero(keep_person)
        item_index = np.flatnonzero(keep_item)
        person_xy = _pad_map_axes(person_pos)
        item_xy = _pad_map_axes(item_pos)
        local_person = {int(person): local for local, person in enumerate(person_index)}
        local_item = {int(item): local for local, item in enumerate(item_index)}
        for person, item in observed:
            if person not in local_person or item not in local_item:
                continue
            person_coord = person_pos[local_person[person]]
            item_coord = item_pos[local_item[item]]
            distance = float(np.linalg.norm(person_coord - item_coord))
            if not np.isfinite(distance):
                continue
            reconstruction = float(
                np.dot(person_xy[local_person[person]], item_xy[local_item[item]])
            )
            unexplained = _unexplained_leftover(float(residual[person, item]), reconstruction)
            candidates.append(
                _candidate_row(
                    post_ids,
                    item_codes,
                    residual,
                    person,
                    item,
                    distance,
                    unexplained,
                )
            )
    if not candidates:
        for person, item in observed:
            distance = abs(float(residual[person, item]) - center)
            candidates.append(
                _candidate_row(
                    post_ids,
                    item_codes,
                    residual,
                    person,
                    item,
                    distance,
                    None,
                )
            )
    closest = min(candidates, key=lambda row: (row[0], row[1], row[2]))
    farthest = max(candidates, key=lambda row: (row[0], row[1], row[2]))
    return (
        _pair_from_candidate(PAIR_KIND_CLOSEST, closest),
        _pair_from_candidate(PAIR_KIND_FARTHEST, farthest),
    )


def _unexplained_leftover(residual: float, reconstruction: float) -> float | None:
    """Return ``U = R − R̂`` when both terms are finite; otherwise omit."""
    if not np.isfinite(reconstruction):
        return None
    unexplained = residual - reconstruction
    if not np.isfinite(unexplained):
        return None
    return float(unexplained)


def _candidate_row(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    residual: np.ndarray,
    person: int,
    item: int,
    distance: float,
    leftover_map_unexplained: float | None,
) -> tuple[float, str, str, float, float | None]:
    """One observed leftover cell: distance, ids, residual, unexplained U."""
    return (
        max(distance, 0.0),
        post_ids[person],
        item_codes[item],
        float(residual[person, item]),
        leftover_map_unexplained,
    )


def _pair_from_candidate(
    pair_kind: str, row: tuple[float, str, str, float, float | None]
) -> LeftoverPair:
    """Build a leftover pair from a candidate row."""
    return LeftoverPair(
        pair_kind=pair_kind,
        post_id=row[1],
        criterion_code=row[2],
        leftover_distance=row[0],
        leftover_residual=row[3],
        leftover_map_unexplained=row[4],
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
    """Pad or truncate Gabriel coordinates to two leftover-map axes.

    Unused axes pad with zero rather than inventing a second component.
    Hidden SVD axes after the second are dropped so reconstruction is
    ``ξ_{1:2} · ζ_{1:2}``, not the full-rank inner product. That
    reconstruction stays internal; only unexplained leftover is named.
    """
    padded = np.zeros((positions.shape[0], _LEFTOVER_MAP_AXES), dtype=np.float64)
    width = min(_LEFTOVER_MAP_AXES, positions.shape[1])
    padded[:, :width] = positions[:, :width]
    return padded
