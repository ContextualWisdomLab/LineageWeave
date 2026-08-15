"""Lifecycle regressions for safe analysis-run completion and summaries."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lineageweave.analysis_run import (
    AnalysisRunCompletion,
    AnalysisRunConfiguration,
    AnalysisRunContractError,
    AnalysisRunSummary,
    SourceProfileReference,
)

UTC = timezone.utc
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
STARTED = datetime(2026, 8, 15, 1, 0, tzinfo=UTC)
COMPLETED = datetime(2026, 8, 15, 2, 0, tzinfo=UTC)


def _configuration() -> AnalysisRunConfiguration:
    return AnalysisRunConfiguration(0, True, True, True, "tepp-v1", "aggregate")


def _summary(**changes: object) -> AnalysisRunSummary:
    values: dict[str, object] = {
        "analysis_run_id": "run-id",
        "profile_key": "configured-primary",
        "profile_revision": 1,
        "run_status_code": "analysis_run_running",
        "request_digest_sha256": DIGEST_A,
        "source_digest_sha256": DIGEST_B,
        "knowledge_cutoff": STARTED,
        "maximum_available_time": STARTED,
        "row_count": 1,
        "document_count": 1,
        "thread_count": 1,
        "started_at": STARTED,
        "completed_at": None,
        "configuration": _configuration(),
    }
    values.update(changes)
    return AnalysisRunSummary(**values)  # type: ignore[arg-type]


def test_source_profile_rejects_unknown_source_kind() -> None:
    with pytest.raises(AnalysisRunContractError, match="supported source kind"):
        SourceProfileReference(
            "configured-primary",
            1,
            DIGEST_A,
            "filesystem_source_profile",
        )


def test_completion_requires_safe_identifiers_boolean_and_aware_time() -> None:
    completion = AnalysisRunCompletion("run-id", "account-id", True, COMPLETED)
    assert completion.succeeded is True
    for values, message in (
        ((" ", "account-id", True, COMPLETED), "analysis_run_id"),
        (("run-id", " ", True, COMPLETED), "actor_account_id"),
        (("run-id", "account-id", 1, COMPLETED), "succeeded"),
        (("run-id", "account-id", True, datetime(2026, 8, 15)), "completed_at"),
    ):
        with pytest.raises(AnalysisRunContractError, match=message):
            AnalysisRunCompletion(*values)  # type: ignore[arg-type]


def test_summary_lifecycle_is_bounded_and_completion_consistent() -> None:
    assert _summary().public_json()["completed_at"] is None
    assert _summary(
        run_status_code="analysis_run_succeeded",
        completed_at=COMPLETED,
    ).public_json()["run_status_code"] == "analysis_run_succeeded"
    with pytest.raises(AnalysisRunContractError, match="supported run status"):
        _summary(run_status_code="analysis_run_unknown")
    with pytest.raises(AnalysisRunContractError, match="running run cannot"):
        _summary(completed_at=COMPLETED)
    with pytest.raises(AnalysisRunContractError, match="terminal run requires"):
        _summary(run_status_code="analysis_run_failed")
