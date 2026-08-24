"""Jeon leftover post–criterion pairs after a main-effect IRT.

Implements ADR 0048 as amended by ADR 0119, ADR 0163, ADR 0164, and ADR 0185.

Does not import ``fast_mlsirm`` or ``period_report``. A Gabriel biplot
of the residual ``R = Y − E[Y|θ, item]`` supplies person and item
positions. Missing response cells are excluded from the factorization;
they are never treated as zero residuals. Each pair names observed
``Y`` and expected ``E`` so residual always reconciles to ``Y − E``.
Pair distances are Euclidean on the two leftover-map axes (Jeon et al.,
2021); unused axes pad with zero rather than inventing a second
component, and hidden SVD axes after the second are dropped. Each pair
also names the full leftover-map rank so a rank-0 collapse is not read
as leftover structure. Each pair further names leftover-map cross
share ``x = 2 R̂_c U_c / R̃²`` of the *centered* leftover after
truncated two-axis Gabriel reconstruction, so the identity remainder
left by that truncation is not confused with leftover residual ``R``,
leftover-map distance ``d``, explained leftover share
``e = R̂_c² / R̃²``, or unexplained leftover share ``s = U_c² / R̃²``.
Reconstruction ``R̂_c`` and unexplained leftover ``U_c`` stay internal
and are not persisted. ``x`` may be negative when reconstruction and
unexplained leftover have opposite signs.
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
    leftover_map_cross_share: float | None = None


def leftover_pairs_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> tuple[LeftoverPair, ...]:
    """Closest and farthest leftover-map pairs from residual SVD biplot.

    Jeon et al. (2021) leftover interaction is ``−γ‖ξ_p − ζ_i‖``. This
    estimator places persons and items from the residual after IRT main
    effects (Gabriel, 1971). Only observed cells become pairs. Distances
    use the two leftover-map axes; a rank-0 residual still emits a
    stable closest/farthest pair so seed is not empty and does not
    invent a leftover score. Stored residual equals observed ``Y`` minus
    expected ``E[Y|θ, item]``. Stored leftover-map rank is the number
    of Gabriel singular values above the floor. When Gabriel coordinates
    exist, leftover-map cross share ``x = 2 R̂_c U_c / R̃²`` names the
    identity remainder of *centered* leftover ``R̃ = R − center`` after
    two-axis reconstruction ``R̂_c = ξ_{1:2} · ζ_{1:2}`` and unexplained
    leftover ``U_c = R̃ − R̂_c``. ``R̂_c`` and ``U_c`` stay internal
    and are never persisted. Fallback pairs (no complete-case map) omit
    the share rather than fabricating one.
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
        return ()

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
    candidates: list[tuple[float, str, str, float, float, float, float | None]] = []
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
            distance = float(
                np.linalg.norm(person_xy[local_person[person]] - item_xy[local_item[item]])
            )
            if not np.isfinite(distance):
                continue
            reconstruction = float(
                np.dot(person_xy[local_person[person]], item_xy[local_item[item]])
            )
            filled = float(residual[person, item]) - center
            share = _leftover_map_cross_share(filled, reconstruction)
            candidates.append(
                _candidate_row(
                    post_ids, item_codes, matrix, expected, residual, person, item, distance, share
                )
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
                    None,
                )
            )
    closest = min(candidates, key=lambda row: (row[0], row[1], row[2]))
    farthest = max(candidates, key=lambda row: (row[0], row[1], row[2]))
    return (
        _pair_from_candidate(PAIR_KIND_CLOSEST, closest, leftover_map_rank),
        _pair_from_candidate(PAIR_KIND_FARTHEST, farthest, leftover_map_rank),
    )


def _leftover_map_cross_share(filled: float, reconstruction: float) -> float | None:
    """Return ``x = 2 R̂_c U_c / R̃²`` when both terms are finite; otherwise omit.

    ``filled`` is centered leftover ``R̃ = R − center``. Unexplained
    leftover ``U_c = R̃ − R̂_c`` is computed internally. Truncated
    two-axis reconstruction of a higher-rank cell keeps a cross term
    ``2 R̂_c U_c``, so per-cell ``e + s ≠ 1``. The identity remainder
    ``x`` names that cross term as a share of centered leftover.
    ``x`` may be negative when reconstruction and unexplained leftover
    have opposite signs; a negative finite share is stored, not omitted.
    """
    if not np.isfinite(filled) or not np.isfinite(reconstruction):
        return None
    unexplained = float(filled - reconstruction)
    filled_sq = float(filled * filled)
    if filled_sq > _LEFTOVER_SINGULAR_FLOOR:
        share = float(2.0 * reconstruction * unexplained / filled_sq)
        if np.isfinite(share):
            return share
        return None
    if abs(reconstruction) <= _LEFTOVER_SINGULAR_FLOOR and abs(unexplained) <= _LEFTOVER_SINGULAR_FLOOR:
        return 0.0
    return None


def _candidate_row(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
    residual: np.ndarray,
    person: int,
    item: int,
    distance: float,
    leftover_map_cross_share: float | None,
) -> tuple[float, str, str, float, float, float, float | None]:
    """One observed leftover cell: distance, ids, residual, Y, E, cross share."""
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
        leftover_map_cross_share,
    )


def _pair_from_candidate(
    pair_kind: str,
    row: tuple[float, str, str, float, float, float, float | None],
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
        leftover_map_cross_share=row[6],
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
    if n_persons == 0 or n_items == 0 or not np.any(np.abs(filled) > _LEFTOVER_SINGULAR_FLOOR):
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
    """Pad or truncate Gabriel coordinates to two leftover-map axes.

    Unused axes pad with zero rather than inventing a second component.
    Hidden SVD axes after the second are dropped so reconstruction is
    ``ξ_{1:2} · ζ_{1:2}``, not the full-rank inner product. That
    reconstruction stays internal; only leftover-map cross share is
    named.
    """
    padded = np.zeros((positions.shape[0], _LEFTOVER_MAP_AXES), dtype=np.float64)
    width = min(_LEFTOVER_MAP_AXES, positions.shape[1])
    padded[:, :width] = positions[:, :width]
    return padded
