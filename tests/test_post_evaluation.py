"""Tests for lineageweave.post_evaluation (ADR 0003 slice 2)."""

from __future__ import annotations

import pytest

from lineageweave.post_evaluation import (
    CRITERION_CODES,
    IRT_CATEGORY_COUNT,
    NullPostEvaluationClient,
    RUBRIC_VERSION,
    irt_responses_from_result,
)
from fast_mlsirm import LLMJudgeResult


def test_null_client_is_unavailable_not_a_fake_score() -> None:
    client = NullPostEvaluationClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.evaluate("title", "body")


def test_irt_row_has_one_category_per_rubric_criterion() -> None:
    scores = {code: 0.8 for code in CRITERION_CODES}
    result = LLMJudgeResult(
        score=0.8,
        accepted=True,
        rationale="synthetic fixture judge output",
        criterion_scores=scores,
        raw_output="{}",
        orchestration_mode="route",
        trace_step_count=0,
        usage={},
        criterion_categories={code: 4 for code in CRITERION_CODES},
        category_count=IRT_CATEGORY_COUNT,
    )
    responses = irt_responses_from_result(result)
    assert {row.criterion_code for row in responses} == set(CRITERION_CODES)
    assert all(0 <= row.response_category < IRT_CATEGORY_COUNT for row in responses)
    assert RUBRIC_VERSION == "2026-08-13"


def test_irt_row_requires_multiple_criteria() -> None:
    result = LLMJudgeResult(
        score=1.0,
        accepted=True,
        rationale="one item is not an IRT row",
        criterion_scores={"only_one_item": 1.0},
        raw_output="{}",
        orchestration_mode="route",
        trace_step_count=0,
        usage={},
    )
    with pytest.raises(Exception):
        irt_responses_from_result(result)
