"""Focused branch tests for analysis-run validation failure modes.

The product tests exercise realistic registration and PostgreSQL behavior. These
small cases additionally prove that every fail-closed validation branch emits a
content-redacting error instead of accidentally accepting malformed evidence.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from lineageweave.analysis_run import (
    AnalysisRunConfiguration,
    AnalysisRunContractError,
    AnalysisRunRegistration,
    AnalysisRunSummary,
    SourceProfileReference,
    SourceSnapshotEvidence,
    _require_aware,
    _require_nonempty,
    _require_sha256,
)

UTC = timezone.utc
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


class _UnknownOffset(tzinfo):
    """Timezone-shaped test object whose UTC offset is deliberately unknown."""

    def utcoffset(self, value):
        """Return no offset, making a datetime unsuitable for comparison."""
        return None

    def dst(self, value):
        """Return no daylight-saving offset."""
        return None


def _snapshot() -> SourceSnapshotEvidence:
    cutoff = datetime(2026, 8, 15, tzinfo=UTC)
    return SourceSnapshotEvidence(
        DIGEST_B,
        cutoff,
        cutoff - timedelta(seconds=1),
        3,
        2,
        1,
    )


def _configuration() -> AnalysisRunConfiguration:
    return AnalysisRunConfiguration(0, True, True, True, "tepp-v1", "aggregate")


def _summary_values() -> dict[str, object]:
    snapshot = _snapshot()
    started = datetime(2026, 8, 15, 1, tzinfo=UTC)
    return {
        "analysis_run_id": "run-1",
        "profile_key": "configured-primary",
        "profile_revision": 1,
        "run_status_code": "analysis_run_running",
        "request_digest_sha256": DIGEST_A,
        "source_digest_sha256": DIGEST_B,
        "knowledge_cutoff": snapshot.knowledge_cutoff,
        "maximum_available_time": snapshot.maximum_available_time,
        "row_count": 3,
        "document_count": 2,
        "thread_count": 1,
        "started_at": started,
        "completed_at": None,
        "configuration": _configuration(),
    }


def test_low_level_validators_cover_every_short_circuit_branch() -> None:
    _require_sha256("digest", DIGEST_A)
    _require_nonempty("label", "value", maximum=5)
    _require_aware("clock", datetime(2026, 8, 15, tzinfo=UTC))

    with pytest.raises(AnalysisRunContractError, match="lowercase SHA-256"):
        _require_sha256("digest", 1)  # type: ignore[arg-type]
    with pytest.raises(AnalysisRunContractError, match="non-empty text"):
        _require_nonempty("label", 1)  # type: ignore[arg-type]
    with pytest.raises(AnalysisRunContractError, match="non-empty text"):
        _require_nonempty("label", " ")
    with pytest.raises(AnalysisRunContractError, match="exceeds 1"):
        _require_nonempty("label", "xx", maximum=1)
    with pytest.raises(AnalysisRunContractError, match="timezone-aware"):
        _require_aware("clock", "not-a-time")  # type: ignore[arg-type]
    with pytest.raises(AnalysisRunContractError, match="timezone-aware"):
        _require_aware("clock", datetime(2026, 8, 15))
    with pytest.raises(AnalysisRunContractError, match="timezone-aware"):
        _require_aware("clock", datetime(2026, 8, 15, tzinfo=_UnknownOffset()))


def test_public_contracts_reject_nontext_and_unknown_values() -> None:
    with pytest.raises(AnalysisRunContractError, match="profile_key"):
        SourceProfileReference(1, 1, DIGEST_A)  # type: ignore[arg-type]
    with pytest.raises(AnalysisRunContractError, match="source_kind_code"):
        SourceProfileReference(
            "configured-primary", 1, DIGEST_A, 1  # type: ignore[arg-type]
        )
    with pytest.raises(AnalysisRunContractError, match="requested_by_account_id"):
        AnalysisRunRegistration(
            1,  # type: ignore[arg-type]
            "run-key",
            datetime(2026, 8, 15, tzinfo=UTC),
        )
    with pytest.raises(AnalysisRunContractError, match="started_at"):
        AnalysisRunRegistration(
            "account-id", "run-key", "not-a-time"  # type: ignore[arg-type]
        )


def test_summary_status_and_completion_are_a_single_lifecycle_contract() -> None:
    values = _summary_values()
    with pytest.raises(AnalysisRunContractError, match="not recognized"):
        AnalysisRunSummary(
            **{**values, "run_status_code": "analysis_run_unknown"}  # type: ignore[arg-type]
        )
    with pytest.raises(AnalysisRunContractError, match="must not have"):
        AnalysisRunSummary(
            **{
                **values,
                "completed_at": values["started_at"],
            }  # type: ignore[arg-type]
        )
    with pytest.raises(AnalysisRunContractError, match="requires completed_at"):
        AnalysisRunSummary(
            **{
                **values,
                "run_status_code": "analysis_run_failed",
            }  # type: ignore[arg-type]
        )

    completed = values["started_at"] + timedelta(seconds=1)  # type: ignore[operator]
    summary = AnalysisRunSummary(
        **{
            **values,
            "run_status_code": "analysis_run_succeeded",
            "completed_at": completed,
        }  # type: ignore[arg-type]
    )
    assert summary.public_json()["completed_at"] == completed.isoformat()
