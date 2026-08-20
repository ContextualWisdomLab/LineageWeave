from __future__ import annotations

import asyncio

import pytest
from fast_mlsirm import LLMJudgeResult

from backend.app.post_evaluation_ingestion import ingest_post_evaluation
from lineageweave.post_evaluation import CRITERION_CODES, IRT_CATEGORY_COUNT, RUBRIC_VERSION


class _Connection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"

    async def fetch(self, _query: str, *_args: object) -> list[dict[str, object]]:
        return self.rows


class _Client:
    available = True

    def __init__(self, result: LLMJudgeResult) -> None:
        self.result = result

    def evaluate(self, _title: str, _body: str) -> LLMJudgeResult:
        return self.result


def _result() -> LLMJudgeResult:
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
    rows = [
        {
            "criterion_code": code,
            "criterion_label": f"label-{code}",
            "response_category": 2,
            "rubric_version": RUBRIC_VERSION,
        }
        for code in CRITERION_CODES
    ]
    conn = _Connection(rows)
    persisted = asyncio.run(ingest_post_evaluation(conn, _Client(_result()), "post-1", "title", "body"))

    assert [item.criterion_code for item in persisted] == list(CRITERION_CODES)
    assert len(conn.executed) == len(CRITERION_CODES)
    assert all("on conflict" in query.lower() for query, _args in conn.executed)


def test_ingest_evaluation_propagates_judge_failure_without_writes() -> None:
    class FailingClient:
        def evaluate(self, _title: str, _body: str) -> LLMJudgeResult:
            raise RuntimeError("synthetic judge failure")

    conn = _Connection([])
    with pytest.raises(RuntimeError, match="synthetic judge failure"):
        asyncio.run(ingest_post_evaluation(conn, FailingClient(), "post-1", "title", "body"))
    assert conn.executed == []
