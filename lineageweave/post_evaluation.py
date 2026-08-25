"""Pluggable LLM-as-a-Judge evaluation of one post (ADR 0003 slice 2).

A missing judge channel is dropped, never a placeholder score.
:class:`ContextualOrchestratorPostEvaluationClient` reuses
``fast_mlsirm.ContextualOrchestratorJudge`` and persists only through
``LLMJudgeResult.to_irt_row()`` -- this repo does not invent a second
judge-to-IRT pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from fast_mlsirm import (
    CONTEXTUAL_ORCHESTRATOR_CONTRACT_V1,
    ContextualOrchestratorJudge,
    JudgeCriterion,
    LLMJudgeResult,
)

from .http_client import chat_completion_content, post_json

RUBRIC_VERSION = "2026-08-13"
IRT_CATEGORY_COUNT = 5

POST_EVALUATION_CRITERIA: tuple[JudgeCriterion, ...] = (
    JudgeCriterion(
        criterion_id="general_sentiment_positive",
        description=(
            "How clearly the post expresses a constructive customer stance "
            "(satisfaction, praise, willingness to proceed)."
        ),
    ),
    JudgeCriterion(
        criterion_id="general_sentiment_negative",
        description=(
            "How clearly the post expresses a negative customer stance "
            "(complaint, dissatisfaction, churn risk)."
        ),
    ),
    JudgeCriterion(
        criterion_id="sales_lead_specificity",
        description=(
            "How specific the post is as a sales-lead signal: a named next "
            "step, quantity, date, or commercial ask rather than vague interest."
        ),
    ),
)

CRITERION_CODES: tuple[str, ...] = tuple(
    criterion.criterion_id for criterion in POST_EVALUATION_CRITERIA
)


@dataclass(frozen=True)
class CriterionResponse:
    """One IRT item for one post: criterion code plus its category."""

    criterion_code: str
    response_category: int


class PostEvaluationClient(Protocol):
    """Scores one post against the versioned rubric."""

    available: bool

    def evaluate(self, post_title: str, post_body: str) -> LLMJudgeResult:
        """Return a real judge result. Implementations must raise on failure."""
        raise NotImplementedError


class NullPostEvaluationClient:
    """No orchestrator configured -- the evaluation channel is skipped."""

    available = False

    def evaluate(self, post_title: str, post_body: str) -> LLMJudgeResult:  # pragma: no cover
        """Evaluate the post with the configured adjudication channel."""
        raise RuntimeError("NullPostEvaluationClient has no judge channel; check .available first")


class _OrchestratorCompleteAdapter:
    """Maps contextual-orchestrator's chat completions onto fast-mlsirm's
    ``complete(messages, mode=...)`` contract.
    """

    contextual_orchestrator_contract = CONTEXTUAL_ORCHESTRATOR_CONTRACT_V1

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def complete(self, messages: list[dict[str, Any]], mode: str = "auto") -> dict[str, Any]:
        """Complete the configured gateway request and return its response."""
        body = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "messages": messages,
                "mode": mode,
                "reasoning_effort": "auto",
                "response_format": {"type": "json_object"},
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        return {
            "answer": chat_completion_content(body),
            "mode": mode,
            "trace": [],
        }


class ContextualOrchestratorPostEvaluationClient:
    """Judge a post through fast-mlsirm against contextual-orchestrator."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._judge = ContextualOrchestratorJudge(
            _OrchestratorCompleteAdapter(base_url, api_key, timeout=timeout),
            mode="auto",
        )

    def evaluate(self, post_title: str, post_body: str) -> LLMJudgeResult:
        """Evaluate the post with the configured adjudication channel."""
        return self._judge.judge(
            task="Score this customer-facing business post against the rubric.",
            answer=f"Title: {post_title}\n\n{post_body}",
            criteria=POST_EVALUATION_CRITERIA,
            category_count=IRT_CATEGORY_COUNT,
        )


def irt_responses_from_result(result: LLMJudgeResult) -> tuple[CriterionResponse, ...]:
    """Project a judge result through ``to_irt_row`` -- the only legal path."""
    categories = result.to_irt_row(item_type="polytomous", n_categories=IRT_CATEGORY_COUNT)
    criterion_ids = tuple(sorted(result.criterion_scores))
    return tuple(
        CriterionResponse(criterion_code=criterion_id, response_category=category)
        for criterion_id, category in zip(criterion_ids, categories, strict=True)
    )
