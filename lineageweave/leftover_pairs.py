"""Jeon leftover post–criterion pairs after a main-effect IRT.

Implements ADR 0048 as amended by ADR 0119, ADR 0163, ADR 0164, ADR 0182,
and ADR 0184.

Does not import ``fast_mlsirm`` or ``period_report``. A Gabriel biplot
of the residual ``R = Y − E[Y|θ, item]`` supplies person and item
positions. Missing response cells are excluded from the factorization;
they are never treated as zero residuals. Each pair names observed
``Y`` and expected ``E`` so residual always reconciles to ``Y − E``.
Pair distances are Euclidean
on the two leftover-map axes (Jeon et al., 2021); unused axes pad with
zero rather than inventing a second component, and hidden SVD axes
after the second are dropped. Each pair also names the full leftover-map
rank so a rank-0 collapse is not read as leftover structure. Axis share
is the Gabriel inertia of the first two leftover-map axes (ADR 0148).
Complete-case coverage (ADR 0168) names how many scored posts entered
that rectangle. Each pair also names unexplained leftover ``U = R − R̂`` after two-axis
Gabriel reconstruction ``R̂ = ξ_{1:2} · ζ_{1:2}`` so the leftover cell
the map does not reconstruct is not confused with leftover residual
``R`` or leftover-map distance ``d``. Each pair also names explained
leftover share ``e = R̂_c² / R̃²`` of the *centered* leftover ``R̃ = R −
center`` that two-axis reconstruction ``R̂_c`` recovers, so that share
is not confused with unexplained leftover ``U`` (which uses raw
residual, not centered) or leftover-map distance ``d``. Reconstruction
``R̂`` / ``R̂_c`` and centered leftover ``U_c`` are computed internally
and are not persisted.
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
    leftover_map_unexplained: float | None = None
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
    """Closest and farthest leftover-map pairs from residual SVD biplot.

    Jeon et al. (2021) leftover interaction is ``−γ‖ξ_p − ζ_i‖``. This
    estimator places persons and items from the residual after IRT main
    effects (Gabriel, 1971). Only observed cells become pairs. Distances
    use the two leftover-map axes; a rank-0 residual still emits a
    stable closest/farthest pair so seed is not empty and does not
    invent a leftover score. Stored residual equals observed ``Y`` minus
    expected ``E[Y|θ, item]``. Stored leftover-map rank is the number
    of Gabriel singular values above the floor. When Gabriel coordinates
    exist, unexplained leftover ``U = R − R̂`` names the leftover cell
    the two-axis map does not reconstruct, and explained leftover share
    ``e = R̂_c² / R̃²`` names the fraction of *centered* leftover ``R̃ =
    R − center`` that reconstruction ``R̂_c`` recovers; ``R̂`` and
    ``R̂_c`` stay internal and are never persisted. Fallback pairs (no
    complete-case map) omit both rather than fabricating them.
    """
    pairs, _axes = leftover_map_from_residual(post_ids, item_codes, matrix, expected)
    return pairs


def leftover_map_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> tuple[tuple[LeftoverPair, ...], tuple[LeftoverMapAxis, ...]]:
    """Leftover pairs plus the first two Gabriel leftover-map axis shares.

    Axis share is ``σ_k² / Σ_j σ_j²`` for leftover-map axes 1 and 2.
    Rank-0 residuals emit two zero-share axes so seed can name leftover-map
    structure without inventing a leftover score.
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
        return (), ()

    keep_person, keep_item = _complete_case_masks(observed_mask)
    person_index = np.flatnonzero(keep_person)
    item_index = np.flatnonzero(keep_item)
    if person_index.size > 0 and item_index.size > 0:
        center = float(np.mean(residual[np.ix_(person_index, item_index)]))
    else:
        center = float(np.mean([residual[person, item] for person, item in observed]))
    person_pos, item_pos, singular = _complete_case_positions(
        residual, center, keep_person, keep_item
    )
    axes = leftover_map_axes_from_singular(singular)
    leftover_map_rank = int(singular.size)
    candidates: list[
        tuple[float, str, str, float, float, float, float | None, float | None]
    ] = []
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
            unexplained = _unexplained_leftover(float(residual[person, item]), reconstruction)
            share = _explained_leftover_share(filled, reconstruction)
            candidates.append(
                _candidate_row(
                    post_ids,
                    item_codes,
                    matrix,
                    expected,
                    residual,
                    person,
                    item,
                    distance,
                    unexplained,
                    share,
                )
            )
    if not candidates:
        # ADR 0168: without a complete-case Gabriel map there is no
        # leftover pair to name. The report carries coverage counts
        # instead of a center-distance stand-in pair.
        return (), ()
    closest = min(candidates, key=lambda row: (row[0], row[1], row[2]))
    farthest = max(candidates, key=lambda row: (row[0], row[1], row[2]))
    pairs = (
        _pair_from_candidate(PAIR_KIND_CLOSEST, closest, leftover_map_rank),
        _pair_from_candidate(PAIR_KIND_FARTHEST, farthest, leftover_map_rank),
    )
    return pairs, axes


def _unexplained_leftover(residual: float, reconstruction: float) -> float | None:
    """Return ``U = R − R̂`` when both terms are finite; otherwise omit."""
    if not np.isfinite(reconstruction):
        return None
    unexplained = residual - reconstruction
    if not np.isfinite(unexplained):
        return None
    return float(unexplained)


def _explained_leftover_share(filled: float, reconstruction: float) -> float | None:
    """Return ``e = R̂_c² / R̃²`` when both terms are finite; otherwise omit.

    ``filled`` is centered leftover ``R̃ = R − center``. Gabriel
    reconstruction recovers that centered matrix, not raw residual
    ``R``. Using raw ``R`` in the denominator leaves the grand mean
    inside the named leftover and makes a fully reconstructed rank-1
    cell look only partly explained whenever ``center ≠ 0``. Per-cell
    ``e`` is not ``1 − U_c² / R̃²``: truncated two-axis reconstruction
    of a higher-rank cell keeps a cross term ``2 R̂_c U_c``.
    """
    if not np.isfinite(filled) or not np.isfinite(reconstruction):
        return None
    # Compare the absolute magnitudes against the singular floor before
    # squaring: squaring first makes the effective threshold sqrt(1e-12)
    # and can overflow large finite inputs to inf.
    if abs(filled) > _LEFTOVER_SINGULAR_FLOOR:
        share = float((reconstruction / filled) ** 2)
        return share if np.isfinite(share) and share >= 0.0 else None
    if abs(reconstruction) <= _LEFTOVER_SINGULAR_FLOOR:
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
    leftover_map_unexplained: float | None,
    leftover_map_explained_share: float | None,
) -> tuple[float, str, str, float, float, float, float | None, float | None]:
    """One observed leftover cell: distance, ids, residual, Y, E, unexplained U, explained share."""
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
        leftover_map_unexplained,
        leftover_map_explained_share,
    )


def _pair_from_candidate(
    pair_kind: str,
    row: tuple[float, str, str, float, float, float, float | None, float | None],
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
        leftover_map_unexplained=row[6],
        leftover_map_explained_share=row[7],
    )


def leftover_map_axes_from_singular(singular: np.ndarray) -> tuple[LeftoverMapAxis, ...]:
    """Gabriel axis inertia for leftover-map axes 1 and 2.

    Share is ``σ_k² / Σ_j σ_j²``. Values at or below the leftover
    singular floor do not enter the denominator. Rank-0 residuals emit
    two zero-share axes.
    """
    values = np.asarray(singular, dtype=np.float64).reshape(-1)
    kept = values[np.isfinite(values) & (values > _LEFTOVER_SINGULAR_FLOOR)]
    total = float(np.sum(kept * kept)) if kept.size else 0.0
    axes: list[LeftoverMapAxis] = []
    for index in (1, 2):
        value = float(kept[index - 1]) if kept.size >= index else 0.0
        if not np.isfinite(value) or value < 0.0:
            value = 0.0
        share = (value * value / total) if total > 0.0 else 0.0
        axes.append(
            LeftoverMapAxis(
                axis_index=index,
                leftover_singular_value=value,
                leftover_share=max(share, 0.0),
            )
        )
    return tuple(axes)


def leftover_map_coverage_from_residual(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    expected: np.ndarray,
) -> LeftoverMapCoverage:
    """Name how many scored posts entered the complete-case leftover map.

    Gabriel (1971) factorizes the complete-case residual rectangle.
    Missing cells stay out of that rectangle; they are never filled
    with zero. ``map_post_count`` is the number of posts that entered
    the factorization. ``scored_post_count`` is posts with at least
    one observed cell. Incomplete rows are excluded, never zeroed.
    """
    if matrix.shape != (len(post_ids), len(item_codes)):
        raise ValueError(
            f"matrix shape {matrix.shape} does not match {len(post_ids)} posts × {len(item_codes)} items"
        )
    if expected.shape != matrix.shape:
        raise ValueError(f"expected shape {expected.shape} does not match matrix {matrix.shape}")

    residual = matrix.astype(np.float64) - expected.astype(np.float64)
    # Identical mask to leftover_map_from_residual's: a cell the pair map
    # scores must be exactly a cell coverage counts, so map_post_count and
    # the caption can never drift apart if expected ever goes non-finite.
    observed_mask = (~np.isnan(matrix)) & np.isfinite(residual) & np.isfinite(expected)
    scored_post_count = int(observed_mask.any(axis=1).sum())
    scored_item_count = int(observed_mask.any(axis=0).sum())
    keep_person, keep_item = _complete_case_masks(observed_mask)
    map_post_count = int(keep_person.sum())
    map_item_count = int(keep_item.sum())
    return LeftoverMapCoverage(
        map_post_count=map_post_count,
        scored_post_count=scored_post_count,
        map_item_count=map_item_count,
        scored_item_count=scored_item_count,
        incomplete_post_count=scored_post_count - map_post_count,
        incomplete_item_count=scored_item_count - map_item_count,
    )


def _complete_case_masks(observed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop incomplete rows, then incomplete columns among remaining rows."""
    keep_person = observed.any(axis=1)
    keep_item = observed.any(axis=0)
    if np.any(keep_item):
        keep_person = keep_person & observed[:, keep_item].all(axis=1)
    if np.any(keep_person):
        keep_item = keep_item & observed[keep_person, :].all(axis=0)
    else:
        keep_item = np.zeros_like(keep_item)
    return keep_person, keep_item


def _complete_case_positions(
    residual: np.ndarray,
    center: float,
    keep_person: np.ndarray,
    keep_item: np.ndarray,
) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray]:
    """Gabriel coordinates on the complete-case residual rectangle only."""
    person_index = np.flatnonzero(keep_person)
    item_index = np.flatnonzero(keep_item)
    empty_singular = np.zeros(0, dtype=np.float64)
    if person_index.size == 0 or item_index.size == 0:
        return None, None, empty_singular
    filled = residual[np.ix_(person_index, item_index)] - center
    return _leftover_map_positions(filled)


def _leftover_map_positions(
    filled: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Gabriel coordinates ordered by descending singular value.

    NumPy's SVD contract returns singular values largest-first, so filtering
    by the numerical floor preserves a prefix and the first two columns remain
    the two leading leftover-map axes. Rank-0 residuals collapse to the origin.
    """
    n_persons, n_items = filled.shape
    empty_singular = np.zeros(0, dtype=np.float64)
    if n_persons == 0 or n_items == 0 or not np.any(np.abs(filled) > _LEFTOVER_SINGULAR_FLOOR):
        return (
            np.zeros((n_persons, 1), dtype=np.float64),
            np.zeros((n_items, 1), dtype=np.float64),
            empty_singular,
        )
    left, singular, right = np.linalg.svd(filled, full_matrices=False)
    keep = singular > _LEFTOVER_SINGULAR_FLOOR
    if not np.any(keep):
        return (
            np.zeros((n_persons, 1), dtype=np.float64),
            np.zeros((n_items, 1), dtype=np.float64),
            empty_singular,
        )
    scale = np.sqrt(singular[keep])
    person_pos = left[:, keep] * scale
    item_pos = right[keep, :].T * scale
    return person_pos, item_pos, singular[keep]


def _pad_map_axes(positions: np.ndarray) -> np.ndarray:
    """Pad or truncate Gabriel coordinates to two leftover-map axes.

    Unused axes pad with zero rather than inventing a second component.
    Hidden SVD axes after the second are dropped so reconstruction is
    ``ξ_{1:2} · ζ_{1:2}``, not the full-rank inner product. That
    reconstruction stays internal; only unexplained leftover and
    explained leftover share are named.
    """
    padded = np.zeros((positions.shape[0], _LEFTOVER_MAP_AXES), dtype=np.float64)
    width = min(_LEFTOVER_MAP_AXES, positions.shape[1])
    padded[:, :width] = positions[:, :width]
    return padded
