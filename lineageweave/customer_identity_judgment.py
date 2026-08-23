"""Cross-post customer identity judging through fast-mlsirm (ADR 0137)."""

from __future__ import annotations

from typing import Protocol

from fast_mlsirm import ContextualOrchestratorJudge, JudgeCriterion, LLMJudgeResult

from .post_evaluation import IRT_CATEGORY_COUNT, OrchestratorCompleteAdapter

RUBRIC_VERSION = "2026-08-23"
MIN_PROMOTION_CATEGORY = 3

CUSTOMER_IDENTITY_CRITERIA: tuple[JudgeCriterion, ...] = (
    JudgeCriterion(
        criterion_id="customer_cross_post_recurrence",
        description=(
            "The evidence contains at least two distinct source posts carrying the exact "
            "same source-system/customer-code key; repeated lines inside one post do not count."
        ),
    ),
    JudgeCriterion(
        criterion_id="customer_same_organization",
        description=(
            "Across those posts, customer-side context supports one continuing legal organization; "
            "mere co-occurrence, attendance, supplier context, or similarly named organizations do not."
        ),
    ),
    JudgeCriterion(
        criterion_id="customer_candidate_name_support",
        description=(
            "The proposed canonical organization name is supported by the source customer names or "
            "post text in more than one record, rather than inferred from the opaque code itself."
        ),
    ),
)

CUSTOMER_RENAME_CRITERIA: tuple[JudgeCriterion, ...] = (
    JudgeCriterion(
        criterion_id="customer_rename_same_identity",
        description="The previous and proposed names denote the same continuing legal organization.",
    ),
    JudgeCriterion(
        criterion_id="customer_rename_explicit_change",
        description=(
            "The evidence explicitly supports a formal organization-name change; spelling, translation, "
            "abbreviation, brand, division, or subsidiary variation is insufficient."
        ),
    ),
    JudgeCriterion(
        criterion_id="customer_rename_temporal_successor",
        description=(
            "The proposed name is supported by later observations than the previous name and is the "
            "successor label, without making a causal claim from time order alone."
        ),
    ),
)

IDENTITY_CRITERION_CODES = frozenset(item.criterion_id for item in CUSTOMER_IDENTITY_CRITERIA)
RENAME_CRITERION_CODES = frozenset(item.criterion_id for item in CUSTOMER_RENAME_CRITERIA)


class CustomerIdentityJudgeClient(Protocol):
    """Judge a candidate identity and, separately, a possible formal rename."""

    available: bool

    def judge_identity(self, candidate_name: str, evidence_text: str) -> LLMJudgeResult:
        """Return the cross-post identity judgment."""
        raise NotImplementedError  # pragma: no cover - protocol declaration

    def judge_rename(
        self, previous_name: str, candidate_name: str, evidence_text: str
    ) -> LLMJudgeResult:
        """Return a strict formal-rename judgment."""
        raise NotImplementedError  # pragma: no cover - protocol declaration


class NullCustomerIdentityJudgeClient:
    """No orchestrator configured; no master-data judgment is available."""

    available = False

    def judge_identity(self, candidate_name: str, evidence_text: str) -> LLMJudgeResult:
        """Reject use of an unavailable judgment channel."""
        raise RuntimeError("NullCustomerIdentityJudgeClient cannot judge; check .available first")

    def judge_rename(
        self, previous_name: str, candidate_name: str, evidence_text: str
    ) -> LLMJudgeResult:
        """Reject use of an unavailable judgment channel."""
        raise RuntimeError("NullCustomerIdentityJudgeClient cannot judge; check .available first")


class ContextualOrchestratorCustomerIdentityJudgeClient:
    """Use fast-mlsirm's strict judge over contextual-orchestrator."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        adapter = OrchestratorCompleteAdapter(base_url, api_key, timeout=timeout)
        self._identity_judge = ContextualOrchestratorJudge(
            adapter, mode="auto", accept_threshold=0.8
        )
        self._rename_judge = ContextualOrchestratorJudge(
            adapter, mode="auto", accept_threshold=0.95
        )

    def judge_identity(self, candidate_name: str, evidence_text: str) -> LLMJudgeResult:
        """Judge whether repeated post evidence supports one named customer."""
        return self._identity_judge.judge(
            task=(
                "Determine whether repeated source records support promoting the proposed customer "
                "identity into a governed Customer Master."
            ),
            answer=f"Proposed customer: {candidate_name}\n\nEvidence records:\n{evidence_text}",
            criteria=CUSTOMER_IDENTITY_CRITERIA,
            category_count=IRT_CATEGORY_COUNT,
            category_method="cumulative_threshold",
        )

    def judge_rename(
        self, previous_name: str, candidate_name: str, evidence_text: str
    ) -> LLMJudgeResult:
        """Judge only explicit formal name succession, never loose aliasing."""
        return self._rename_judge.judge(
            task="Determine whether the evidence proves a formal organization-name succession.",
            answer=(
                f"Previous preferred name: {previous_name}\n"
                f"Proposed preferred name: {candidate_name}\n\n"
                f"Time-ordered evidence records:\n{evidence_text}"
            ),
            criteria=CUSTOMER_RENAME_CRITERIA,
            category_count=IRT_CATEGORY_COUNT,
            category_method="cumulative_threshold",
        )


def identity_is_promotable(result: LLMJudgeResult, distinct_post_count: int) -> bool:
    """True only for a complete, strong multi-post identity judgment."""
    categories = result.criterion_categories
    return bool(
        distinct_post_count >= 2
        and result.accepted
        and categories is not None
        and set(categories) == IDENTITY_CRITERION_CODES
        and min(categories.values()) >= MIN_PROMOTION_CATEGORY
    )


def rename_is_supported(result: LLMJudgeResult) -> bool:
    """True only when every strict rename criterion reaches the top category."""
    categories = result.criterion_categories
    return bool(
        result.accepted
        and categories is not None
        and set(categories) == RENAME_CRITERION_CODES
        and all(value == IRT_CATEGORY_COUNT - 1 for value in categories.values())
    )


__all__ = [
    "CUSTOMER_IDENTITY_CRITERIA",
    "CUSTOMER_RENAME_CRITERIA",
    "IDENTITY_CRITERION_CODES",
    "MIN_PROMOTION_CATEGORY",
    "RENAME_CRITERION_CODES",
    "RUBRIC_VERSION",
    "ContextualOrchestratorCustomerIdentityJudgeClient",
    "CustomerIdentityJudgeClient",
    "NullCustomerIdentityJudgeClient",
    "identity_is_promotable",
    "rename_is_supported",
]
