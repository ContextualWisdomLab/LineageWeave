"""Calibrated period reports from persisted post-evaluation IRT rows.

ADR 0003 slice 3/4: assemble the judge-to-IRT matrix already stored in
``post_evaluation_response``, fit GRM and GPCM with
``fast_mlsirm.fit_polytomous`` (Rust EM; Dempster et al., 1977), score
EAP thetas (Bock & Mislevy, 1982), and pick the model with
``fixed_item_calibration_diagnostics`` -- never a placeholder number.

The first period for a grouping free-calibrates and persists its item
bank. Later periods EAP-score on those fixed parameters (Kim, 2006
FIPC) so weekly thetas stay on one metric. Independent refits would
re-center each week at 0 and hide real movement.

After scoring, items on that shared bank are ranked by Fisher
information at the group's mean θ (Lord, 1980 max-info CAT rule) via
``fast_mlsirm.information_polytomous`` -- Samejima (1969) GRM /
Muraki (1993) GPCM, computed in Rust. A missing bank is not invented.

Leftover post–criterion pairs (ADR 0017 / 0048) and leftover-map
coordinates (ADR 0121) come from the residual interaction after those
IRT main effects: ``R = Y − E[Y|θ, item]``.
A Gabriel biplot of ``R`` supplies person and item leftover-map
positions. Closest / farthest pairs are the min / max Euclidean
distances on that map (Jeon et al., 2021, eq. 3). fast-mlsirm's
``residual_interaction_map`` owns residual, complete-case admission, Gabriel
coordinates, distance, axis inertia, reconstruction, unexplained residual,
and cross share. This module maps those results to product identifiers and
selects the persisted closest/farthest cells (ADR 0207); it does not fork the
calculation or invent a second IRT fit.

This module is pure compute. Persistence lives in
``backend/app/report_ingestion.py``. TEPP is not used here; temporal
event measurement stays on ``tepp_client``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from fast_mlsirm import (
    PolytomousFit,
    fit_polytomous,
    fixed_item_calibration_diagnostics,
    information_polytomous,
    polytomous_category_probabilities,
    score_polytomous,
    validate_irt_response_matrix,
)

from . import leftover_pairs as _leftover_pairs
from .leftover_pairs import (
    LeftoverInteractionMap,
    LeftoverMapAxis,
    LeftoverMapCoverage,
    LeftoverMapItem,
    LeftoverMapPerson,
    LeftoverPair,
    leftover_map_coverage_from_residual,
    leftover_map_from_residual,
)
from .post_evaluation import CRITERION_CODES, IRT_CATEGORY_COUNT

PAIR_KIND_CLOSEST = _leftover_pairs.PAIR_KIND_CLOSEST
PAIR_KIND_FARTHEST = _leftover_pairs.PAIR_KIND_FARTHEST
leftover_pairs_from_residual = _leftover_pairs.leftover_pairs_from_residual

LINK_METHOD_FREE = "free"
LINK_METHOD_FIPC = "fipc"


@dataclass(frozen=True)
class MemberScore:
    """One post's EAP ability on the period's fitted metric."""

    post_id: str
    theta_eap: float
    theta_sd: float


@dataclass(frozen=True)
class SelectedItem:
    """One shared-bank item ranked by Fisher information at a group's θ."""

    item_code: str
    information: float
    rank: int


@dataclass(frozen=True)
class ItemBank:
    """Polytomous item parameters on one metric (the FIPC anchor)."""

    model: str
    item_codes: tuple[str, ...]
    slope: tuple[float, ...]
    cat_params: tuple[tuple[float, ...], ...]
    source_period_code: str

    def as_fit(self, loglik: float = 0.0, n_iter: int = 0, converged: bool = True) -> PolytomousFit:
        """Rebuild the ``fast_mlsirm`` fit object used by ``score_polytomous``."""
        return PolytomousFit(
            model=self.model,
            slope=np.asarray(self.slope, dtype=np.float64),
            cat_params=np.asarray(self.cat_params, dtype=np.float64),
            loglik=loglik,
            n_iter=n_iter,
            converged=converged,
        )


@dataclass(frozen=True)
class PeriodReport:
    """One grouping's calibrated report for one calendar period."""

    selected_model: str
    mean_theta: float
    mean_theta_sd: float
    post_count: int
    item_count: int
    fit_loglik: float
    fit_converged: bool
    calibration_score: float
    member_scores: tuple[MemberScore, ...]
    item_bank: ItemBank
    link_method: str = LINK_METHOD_FREE
    anchor_period_code: str | None = None
    delta_mean_theta: float | None = None
    selected_items: tuple[SelectedItem, ...] = ()
    leftover_pairs: tuple[LeftoverPair, ...] = ()
    leftover_map_persons: tuple[LeftoverMapPerson, ...] = ()
    leftover_map_items: tuple[LeftoverMapItem, ...] = ()
    leftover_map_axes: tuple[LeftoverMapAxis, ...] = ()
    leftover_map_coverage: LeftoverMapCoverage | None = None


def assemble_response_matrix(
    post_ids: list[str],
    rows: list[tuple[str, str, int]],
    item_codes: tuple[str, ...] = CRITERION_CODES,
) -> np.ndarray:
    """Persons x items matrix; missing cells are NaN.

    ``rows`` are ``(post_id, criterion_code, response_category)``.
    """
    person_index = {post_id: idx for idx, post_id in enumerate(post_ids)}
    item_index = {code: idx for idx, code in enumerate(item_codes)}
    matrix = np.full((len(post_ids), len(item_codes)), np.nan, dtype=np.float64)
    for post_id, criterion_code, category in rows:
        if post_id not in person_index or criterion_code not in item_index:
            continue
        matrix[person_index[post_id], item_index[criterion_code]] = float(category)
    return matrix


def rank_items_by_information(item_bank: ItemBank, theta: float) -> tuple[SelectedItem, ...]:
    """Rank shared-bank items by Fisher information at ``theta``.

    Reuses ``fast_mlsirm.information_polytomous`` (Rust; Samejima 1969,
    Muraki 1993). The rank-1 item is the Lord (1980) max-info CAT pick
    at this group's location on the shared metric.
    """
    if item_bank.model not in {"grm", "gpcm"}:
        raise ValueError(f"unsupported item-bank model {item_bank.model!r}")
    if not np.isfinite(theta):
        raise ValueError("theta must be finite")
    curves = information_polytomous(item_bank.as_fit(), np.asarray([theta], dtype=np.float64))
    item_info = np.asarray(curves["item_info"], dtype=np.float64)
    n_items = len(item_bank.item_codes)
    if item_info.shape != (1, n_items):
        raise ValueError(f"information_polytomous returned shape {item_info.shape}, expected (1, {n_items})")
    infos = item_info[0]
    order = np.argsort(-infos, kind="stable")
    return tuple(
        SelectedItem(
            item_code=item_bank.item_codes[int(index)],
            information=float(infos[int(index)]),
            rank=rank,
        )
        for rank, index in enumerate(order, start=1)
    )


def item_bank_from_fit(fit: PolytomousFit, item_codes: tuple[str, ...], source_period_code: str) -> ItemBank:
    """Copy fitted slopes and category parameters into a persistable bank."""
    cat = np.asarray(fit.cat_params, dtype=np.float64)
    return ItemBank(
        model=str(fit.model),
        item_codes=tuple(item_codes),
        slope=tuple(float(value) for value in np.asarray(fit.slope, dtype=np.float64)),
        cat_params=tuple(tuple(float(value) for value in row) for row in cat),
        source_period_code=source_period_code,
    )


def observed_response_loglik(matrix: np.ndarray, probs: np.ndarray) -> float:
    """Sum log P(y_ij) over observed cells; missing cells are skipped."""
    loglik = 0.0
    n_persons, n_items = matrix.shape
    for person in range(n_persons):
        for item in range(n_items):
            category = matrix[person, item]
            if np.isnan(category):
                continue
            index = int(category)
            loglik += float(np.log(max(probs[person, item, index], 1e-12)))
    return loglik


def expected_category_matrix(matrix: np.ndarray, probs: np.ndarray) -> np.ndarray:
    """E[Y_pi] = sum_k k P(Y=k | θ_p, item_i); missing cells stay NaN."""
    n_categories = probs.shape[2]
    categories = np.arange(n_categories, dtype=np.float64)
    expected = np.tensordot(probs, categories, axes=([2], [0]))
    return np.where(np.isnan(matrix), np.nan, expected)


def leftover_pairs_for_fit(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    model: str,
    theta: np.ndarray,
    fit: PolytomousFit,
) -> tuple[LeftoverPair, ...]:
    """Leftover pairs from the already-fitted GRM/GPCM main effects."""
    return leftover_map_for_fit(post_ids, item_codes, matrix, model, theta, fit).pairs


def leftover_map_for_fit(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    model: str,
    theta: np.ndarray,
    fit: PolytomousFit,
) -> LeftoverInteractionMap:
    """Leftover-map coordinates and pairs from already-fitted GRM/GPCM main effects."""
    probs = _category_probabilities(model, theta, fit)
    expected = expected_category_matrix(matrix, probs)
    return leftover_map_from_residual(post_ids, item_codes, matrix, expected)


def leftover_map_coverage_for_fit(
    post_ids: list[str],
    item_codes: tuple[str, ...],
    matrix: np.ndarray,
    model: str,
    theta: np.ndarray,
    fit: PolytomousFit,
) -> LeftoverMapCoverage:
    """Complete-case leftover-map coverage from the fitted main effects."""
    probs = _category_probabilities(model, theta, fit)
    expected = expected_category_matrix(matrix, probs)
    return leftover_map_coverage_from_residual(post_ids, item_codes, matrix, expected)


def _member_scores(post_ids: list[str], scores: dict[str, np.ndarray]) -> tuple[MemberScore, ...]:
    """Implement the _member_scores operation for this channel."""
    theta = np.asarray(scores["theta_eap"], dtype=np.float64)
    theta_sd = np.asarray(scores["theta_sd"], dtype=np.float64)
    return tuple(
        MemberScore(post_id=post_id, theta_eap=float(theta[idx]), theta_sd=float(theta_sd[idx]))
        for idx, post_id in enumerate(post_ids)
    )


def _category_probabilities(model: str, theta: np.ndarray, fit: PolytomousFit) -> np.ndarray:
    """Delegate fitted-model predictions to fast-mlsirm's Rust authority."""
    if model != fit.model:
        raise ValueError("model must match the fitted item bank")
    probabilities = np.asarray(
        polytomous_category_probabilities(fit, theta), dtype=np.float64
    )
    expected_shape = (len(theta), len(fit.slope), fit.cat_params.shape[1] + 1)
    if probabilities.shape != expected_shape:
        raise ValueError(
            "fast-mlsirm category probabilities must have shape "
            f"{expected_shape}, got {probabilities.shape}"
        )
    return probabilities


def calibrate_period_report(
    post_ids: list[str],
    rows: list[tuple[str, str, int]],
    item_codes: tuple[str, ...] = CRITERION_CODES,
    n_categories: int = IRT_CATEGORY_COUNT,
    source_period_code: str = "",
) -> PeriodReport:
    """Fit GRM and GPCM, FIPC-select, EAP-score. Raises if the matrix is unusable."""
    if len(post_ids) < 2:
        raise ValueError("need at least two posts with evaluations to calibrate a period")
    matrix = assemble_response_matrix(post_ids, rows, item_codes)
    validate_irt_response_matrix(matrix, item_type="polytomous", n_categories=n_categories)

    fits = {}
    for model in ("grm", "gpcm"):
        fit = fit_polytomous(matrix, n_cat=n_categories, model=model, max_iter=80)
        scores = score_polytomous(matrix, fit)
        theta = np.asarray(scores["theta_eap"], dtype=np.float64)
        probs = _category_probabilities(model, theta, fit)
        fits[model] = (fit, scores, probs)

    diagnostics = fixed_item_calibration_diagnostics(
        matrix,
        {model: payload[2] for model, payload in fits.items()},
        item_type="polytomous",
        response_process="cumulative",
    )
    selected = str(diagnostics.best["candidate_label"])
    fit, scores, _ = fits[selected]
    theta = np.asarray(scores["theta_eap"], dtype=np.float64)
    mean_theta = float(theta.mean())
    item_bank = item_bank_from_fit(fit, item_codes, source_period_code)
    leftover_map = leftover_map_for_fit(post_ids, item_codes, matrix, selected, theta, fit)
    leftover_map_coverage = leftover_map_coverage_for_fit(
        post_ids, item_codes, matrix, selected, theta, fit
    )
    return PeriodReport(
        selected_model=selected,
        mean_theta=mean_theta,
        mean_theta_sd=float(theta.std(ddof=0)),
        post_count=len(post_ids),
        item_count=len(item_codes),
        fit_loglik=float(fit.loglik),
        fit_converged=bool(fit.converged),
        calibration_score=float(diagnostics.best["calibration_score"]),
        member_scores=_member_scores(post_ids, scores),
        item_bank=item_bank,
        link_method=LINK_METHOD_FREE,
        selected_items=rank_items_by_information(item_bank, mean_theta),
        leftover_pairs=leftover_map.pairs,
        leftover_map_persons=leftover_map.persons,
        leftover_map_items=leftover_map.items,
        leftover_map_axes=leftover_map.axes,
        leftover_map_coverage=leftover_map_coverage,
    )


def score_period_on_bank(
    post_ids: list[str],
    rows: list[tuple[str, str, int]],
    item_bank: ItemBank,
    previous_mean_theta: float | None = None,
    n_categories: int = IRT_CATEGORY_COUNT,
) -> PeriodReport:
    """EAP-score a new period on fixed item parameters (true FIPC)."""
    if len(post_ids) < 2:
        raise ValueError("need at least two posts with evaluations to score a period")
    if item_bank.model not in {"grm", "gpcm"}:
        raise ValueError(f"unsupported item-bank model {item_bank.model!r}")
    matrix = assemble_response_matrix(post_ids, rows, item_bank.item_codes)
    validate_irt_response_matrix(matrix, item_type="polytomous", n_categories=n_categories)
    fit = item_bank.as_fit()
    scores = score_polytomous(matrix, fit)
    theta = np.asarray(scores["theta_eap"], dtype=np.float64)
    mean_theta = float(theta.mean())
    probs = _category_probabilities(item_bank.model, theta, fit)
    diagnostics = fixed_item_calibration_diagnostics(
        matrix,
        {LINK_METHOD_FIPC: probs},
        item_type="polytomous",
        response_process="cumulative",
    )
    leftover_map = leftover_map_for_fit(
        post_ids, item_bank.item_codes, matrix, item_bank.model, theta, fit
    )
    leftover_map_coverage = leftover_map_coverage_for_fit(
        post_ids, item_bank.item_codes, matrix, item_bank.model, theta, fit
    )
    return PeriodReport(
        selected_model=item_bank.model,
        mean_theta=mean_theta,
        mean_theta_sd=float(theta.std(ddof=0)),
        post_count=len(post_ids),
        item_count=len(item_bank.item_codes),
        fit_loglik=observed_response_loglik(matrix, probs),
        fit_converged=True,
        calibration_score=float(diagnostics.best["calibration_score"]),
        member_scores=_member_scores(post_ids, scores),
        item_bank=item_bank,
        link_method=LINK_METHOD_FIPC,
        anchor_period_code=item_bank.source_period_code,
        delta_mean_theta=(
            None
            if previous_mean_theta is None
            else mean_theta - float(previous_mean_theta)
        ),
        selected_items=rank_items_by_information(item_bank, mean_theta),
        leftover_pairs=leftover_map.pairs,
        leftover_map_persons=leftover_map.persons,
        leftover_map_items=leftover_map.items,
        leftover_map_axes=leftover_map.axes,
        leftover_map_coverage=leftover_map_coverage,
    )


def link_or_calibrate_period_report(
    post_ids: list[str],
    rows: list[tuple[str, str, int]],
    item_bank: ItemBank | None = None,
    previous_mean_theta: float | None = None,
    item_codes: tuple[str, ...] = CRITERION_CODES,
    n_categories: int = IRT_CATEGORY_COUNT,
    source_period_code: str = "",
) -> PeriodReport:
    """Free-calibrate the first period; FIPC-score later periods on that bank."""
    if item_bank is None:
        return calibrate_period_report(
            post_ids,
            rows,
            item_codes=item_codes,
            n_categories=n_categories,
            source_period_code=source_period_code,
        )
    return score_period_on_bank(
        post_ids,
        rows,
        item_bank,
        previous_mean_theta=previous_mean_theta,
        n_categories=n_categories,
    )


def score_groups_on_shared_metric(
    groups: dict[str, tuple[list[str], list[tuple[str, str, int]]]],
    item_bank: ItemBank | None = None,
    previous_means: dict[str, float] | None = None,
    item_codes: tuple[str, ...] = CRITERION_CODES,
    n_categories: int = IRT_CATEGORY_COUNT,
    source_period_code: str = "",
) -> tuple[PeriodReport | None, dict[str, PeriodReport]]:
    """Fit one item bank on the pooled posts, then FIPC-score each group.

    Independent per-group refits each re-center near 0, so a high process
    unit and a low process unit look the same. Scoring both on one bank
    keeps them comparable (the multilevel / multiple-membership rule).
    """
    previous_means = previous_means or {}
    pooled_ids: list[str] = []
    pooled_rows: list[tuple[str, str, int]] = []
    seen: set[str] = set()
    for post_ids, rows in groups.values():
        for post_id in post_ids:
            if post_id not in seen:
                seen.add(post_id)
                pooled_ids.append(post_id)
        pooled_rows.extend(rows)

    bank_report: PeriodReport | None = None
    if item_bank is None:
        if len(pooled_ids) < 2:
            raise ValueError("need at least two posts to fit a shared metric")
        bank_report = calibrate_period_report(
            pooled_ids,
            pooled_rows,
            item_codes=item_codes,
            n_categories=n_categories,
            source_period_code=source_period_code,
        )
        item_bank = bank_report.item_bank

    scored: dict[str, PeriodReport] = {}
    for key, (post_ids, rows) in groups.items():
        if len(post_ids) < 2:
            continue
        scored[key] = score_period_on_bank(
            post_ids,
            rows,
            item_bank,
            previous_mean_theta=previous_means.get(key),
            n_categories=n_categories,
        )
    return bank_report, scored
