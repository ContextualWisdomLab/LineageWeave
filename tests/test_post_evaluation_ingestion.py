from __future__ import annotations

import asyncio

import pytest
from fast_mlsirm import LLMJudgeResult

from backend.app.post_evaluation_ingestion import ingest_post_evaluation
from lineageweave.post_evaluation import CRITERION_CODES, IRT_CATEGORY_COUNT, RUBRIC_VERSION


class _EvaluationDatabaseConnection:
    def __init__(self, persisted_evaluation_rows: list[dict[str, object]]) -> None:
        self.persisted_evaluation_rows = persisted_evaluation_rows
        self.executed_queries: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *args: object) -> str:
        self.executed_queries.append((query, args))
        return "OK"

    async def fetch(self, _query: str, *_args: object) -> list[dict[str, object]]:
        return self.persisted_evaluation_rows


class _PostEvaluationClient:
    available = True

    def __init__(self, judge_result: LLMJudgeResult) -> None:
        self.judge_result = judge_result

    def evaluate(self, _title: str, _body: str) -> LLMJudgeResult:
        return self.judge_result


def _judge_result() -> LLMJudgeResult:
    return LLMJudgeResult(
        score=0.8,
        accepted=True,
        rationale="synthetic ingestion result",
        criterion_scores={code: 0.8 for code in CRITERION_CODES},
        raw_output="{}",
        orchestration_mode="route",
        trace_step_count=0,
        usage={},
        criterion_categories={code: 2 for code in CRITERION_CODES},
        category_count=IRT_CATEGORY_COUNT,
    )


def test_ingest_evaluation_upserts_each_criterion_and_fetches_rows() -> None:
    persisted_evaluation_rows = [
        {
            "criterion_code": code,
            "criterion_label": f"label-{code}",
            "response_category": 2,
            "rubric_version": RUBRIC_VERSION,
        }
        for code in CRITERION_CODES
    ]
    database_connection = _EvaluationDatabaseConnection(persisted_evaluation_rows)
    persisted_criterion_responses = asyncio.run(
        ingest_post_evaluation(
            database_connection,
            _PostEvaluationClient(_judge_result()),
            "post-1",
            "title",
            "body",
        )
    )

    assert [
        criterion_response.criterion_code
        for criterion_response in persisted_criterion_responses
    ] == list(CRITERION_CODES)
    assert len(database_connection.executed_queries) == len(CRITERION_CODES)
    assert all(
        "on conflict" in query.lower()
        for query, _args in database_connection.executed_queries
    )


def test_ingest_evaluation_propagates_judge_failure_without_writes() -> None:
    class FailingClient:
        def evaluate(self, _title: str, _body: str) -> LLMJudgeResult:
            raise RuntimeError("synthetic judge failure")

    database_connection = _EvaluationDatabaseConnection([])
    with pytest.raises(RuntimeError, match="synthetic judge failure"):
        asyncio.run(
            ingest_post_evaluation(
                database_connection,
                FailingClient(),
                "post-1",
                "title",
                "body",
            )
        )
    assert database_connection.executed_queries == []
