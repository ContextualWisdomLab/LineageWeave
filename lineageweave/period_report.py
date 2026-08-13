"""Calibrated period reports from persisted post-evaluation IRT rows.

ADR 0003 slice 3: assemble the judge-to-IRT matrix already stored in
``post_evaluation_response``, fit GRM and GPCM with
``fast_mlsirm.fit_polytomous`` (Rust EM; Dempster et al., 1977), score
EAP thetas (Bock & Mislevy, 1982), and pick the model with
``fixed_item_calibration_diagnostics`` -- never a placeholder number.

This module is pure compute. Persistence lives in
``backend/app/report_ingestion.py``. TEPP is not used here; temporal
event measurement stays on ``tepp_client``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from fast_mlsirm import (
    fit_polytomous,
    fixed_item_calibration_diagnostics,
    score_polytomous,
    validate_irt_response_matrix,
)

from .post_evaluation import CRITERION_CODES, IRT_CATEGORY_COUNT


@dataclass(frozen=True)
class MemberScore:
    """One post's EAP ability on the period's fitted metric."""

    post_id: str
    theta_eap: float
    theta_sd: float


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


def _sigmoid(value: np.ndarray) -> np.ndarray:
    """Numerically stable logistic."""
    return 1.0 / (1.0 + np.exp(-np.clip(value, -40.0, 40.0)))


def grm_category_probabilities(theta: np.ndarray, slope: np.ndarray, cat_params: np.ndarray) -> np.ndarray:
    """Samejima GRM P(Y=k | theta) from a ``PolytomousFit``.

    ``cat_params[i, k]`` is the cumulative threshold ``beta_{i,k+1}``.
    ``P(Y >= k) = sigmoid(a_i * theta - beta_{i,k})``.
    """
    n_persons = theta.shape[0]
    n_items, n_steps = cat_params.shape
    n_cat = n_steps + 1
    probs = np.empty((n_persons, n_items, n_cat), dtype=np.float64)
    for item in range(n_items):
        cumul = np.empty((n_persons, n_cat + 1), dtype=np.float64)
        cumul[:, 0] = 1.0
        for step in range(n_steps):
            cumul[:, step + 1] = _sigmoid(slope[item] * theta - cat_params[item, step])
        cumul[:, n_cat] = 0.0
        # Thresholds must yield a decreasing survival curve; enforce that
        # so category probabilities stay non-negative and sum to 1.
        for step in range(1, n_cat):
            cumul[:, step] = np.minimum(cumul[:, step], cumul[:, step - 1])
        probs[:, item, :] = np.maximum(cumul[:, :-1] - cumul[:, 1:], 0.0)
        row_sum = probs[:, item, :].sum(axis=1, keepdims=True)
        probs[:, item, :] /= np.maximum(row_sum, 1e-12)
    return probs


def gpcm_category_probabilities(theta: np.ndarray, slope: np.ndarray, cat_params: np.ndarray) -> np.ndarray:
    """Muraki GPCM P(Y=k | theta) from additive category intercepts."""
    n_persons = theta.shape[0]
    n_items, n_steps = cat_params.shape
    n_cat = n_steps + 1
    probs = np.empty((n_persons, n_items, n_cat), dtype=np.float64)
    for item in range(n_items):
        logits = np.zeros((n_persons, n_cat), dtype=np.float64)
        running = np.zeros(n_persons, dtype=np.float64)
        for step in range(n_steps):
            running = running + slope[item] * theta + cat_params[item, step]
            logits[:, step + 1] = running
        logits -= logits.max(axis=1, keepdims=True)
        exp = np.exp(logits)
        probs[:, item, :] = exp / exp.sum(axis=1, keepdims=True)
    return np.clip(probs, 1e-12, 1.0)


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


def calibrate_period_report(
    post_ids: list[str],
    rows: list[tuple[str, str, int]],
    item_codes: tuple[str, ...] = CRITERION_CODES,
    n_categories: int = IRT_CATEGORY_COUNT,
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
        if model == "grm":
            probs = grm_category_probabilities(theta, fit.slope, fit.cat_params)
        else:
            probs = gpcm_category_probabilities(theta, fit.slope, fit.cat_params)
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
    theta_sd = np.asarray(scores["theta_sd"], dtype=np.float64)
    members = tuple(
        MemberScore(post_id=post_id, theta_eap=float(theta[idx]), theta_sd=float(theta_sd[idx]))
        for idx, post_id in enumerate(post_ids)
    )
    return PeriodReport(
        selected_model=selected,
        mean_theta=float(theta.mean()),
        mean_theta_sd=float(theta.std(ddof=0)),
        post_count=len(post_ids),
        item_count=len(item_codes),
        fit_loglik=float(fit.loglik),
        fit_converged=bool(fit.converged),
        calibration_score=float(diagnostics.best["calibration_score"]),
        member_scores=members,
    )
