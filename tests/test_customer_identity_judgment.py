"""Synthetic contract tests for ADR 0137's cross-post customer judge."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fast_mlsirm import LLMJudgeResult

from lineageweave.customer_identity_judgment import (
    IDENTITY_CRITERION_CODES,
    RENAME_CRITERION_CODES,
    ContextualOrchestratorCustomerIdentityJudgeClient,
    NullCustomerIdentityJudgeClient,
    identity_is_promotable,
    rename_is_supported,
)
from lineageweave.post_evaluation import IRT_CATEGORY_COUNT


def _result(codes: frozenset[str], categories: dict[str, int]) -> LLMJudgeResult:
    score = sum(categories.values()) / (len(categories) * (IRT_CATEGORY_COUNT - 1))
    return LLMJudgeResult(
        score=score,
        accepted=score >= 0.8,
        rationale="synthetic evidence judgment",
        criterion_scores={code: value / 4 for code, value in categories.items()},
        raw_output="{}",
        orchestration_mode="auto",
        trace_step_count=2,
        usage={},
        criterion_categories={code: categories[code] for code in codes},
        category_count=IRT_CATEGORY_COUNT,
        category_method="cumulative_threshold",
    )


def test_null_customer_identity_judge_is_unavailable() -> None:
    client = NullCustomerIdentityJudgeClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.judge_identity("Synthetic Grid", "record")
    with pytest.raises(RuntimeError):
        client.judge_rename("Synthetic Grid", "Synthetic Energy", "record")


def test_promotion_requires_two_posts_and_every_identity_criterion() -> None:
    strong = _result(IDENTITY_CRITERION_CODES, {code: 4 for code in IDENTITY_CRITERION_CODES})
    weak = _result(
        IDENTITY_CRITERION_CODES,
        {code: (2 if code == "customer_same_organization" else 4) for code in IDENTITY_CRITERION_CODES},
    )

    assert identity_is_promotable(strong, 2)
    assert not identity_is_promotable(strong, 1)
    assert not identity_is_promotable(weak, 3)


def test_rename_requires_top_category_for_every_criterion() -> None:
    strong = _result(RENAME_CRITERION_CODES, {code: 4 for code in RENAME_CRITERION_CODES})
    alias_only = _result(
        RENAME_CRITERION_CODES,
        {code: (3 if code == "customer_rename_explicit_change" else 4) for code in RENAME_CRITERION_CODES},
    )

    assert rename_is_supported(strong)
    assert not rename_is_supported(alias_only)


def test_live_client_uses_cumulative_fast_mlsirm_judge(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_post_json(url, body, *, headers, timeout):
        seen.update(url=url, body=body, headers=headers, timeout=timeout)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"score":1,"accepted":true,"rationale":"supported",'
                            '"criterion_thresholds":{'
                            '"customer_cross_post_recurrence":[true,true,true,true],'
                            '"customer_same_organization":[true,true,true,true],'
                            '"customer_candidate_name_support":[true,true,true,true]}}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("lineageweave.post_evaluation.post_json", fake_post_json)
    client = ContextualOrchestratorCustomerIdentityJudgeClient(
        "http://orchestrator", "secret", timeout=13.0
    )
    result = client.judge_identity(
        "Synthetic Grid", "post-a and post-b carry source key synthetic/001"
    )

    assert identity_is_promotable(result, 2)
    assert seen["url"] == "http://orchestrator/v1/chat/completions"
    assert seen["body"]["mode"] == "auto"
    assert seen["body"]["reasoning_effort"] == "auto"
    assert seen["timeout"] == 13.0


def test_live_client_uses_the_separate_strict_rename_rubric() -> None:
    result = _result(RENAME_CRITERION_CODES, {code: 4 for code in RENAME_CRITERION_CODES})
    seen: dict[str, object] = {}

    def judge(**kwargs):
        seen.update(kwargs)
        return result

    client = object.__new__(ContextualOrchestratorCustomerIdentityJudgeClient)
    client._rename_judge = SimpleNamespace(judge=judge)

    assert client.judge_rename("Synthetic Grid", "Synthetic Energy", "evidence") is result
    assert seen["criteria"]
    assert "Previous preferred name: Synthetic Grid" in seen["answer"]
