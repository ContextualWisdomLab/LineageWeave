"""Unit contracts for source-redacting, leakage-safe analysis evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

import pytest

from lineageweave.analysis_run import (
    AnalysisRunConfiguration,
    AnalysisRunContractError,
    AnalysisRunRegistration,
    AnalysisRunSummary,
    SourceProfileReference,
    SourceSnapshotEvidence,
    canonical_json_sha256,
    exact_text_sha256,
)

UTC = timezone.utc
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def _profile() -> SourceProfileReference:
    return SourceProfileReference("configured-primary", 1, DIGEST_A)


def _snapshot() -> SourceSnapshotEvidence:
    return SourceSnapshotEvidence(
        source_digest_sha256=DIGEST_B,
        knowledge_cutoff=datetime(2026, 8, 15, 0, 0, tzinfo=UTC),
        maximum_available_time=datetime(2026, 8, 14, 23, 59, tzinfo=UTC),
        row_count=12,
        document_count=10,
        thread_count=8,
    )


def _configuration() -> AnalysisRunConfiguration:
    return AnalysisRunConfiguration(
        row_limit=0,
        write_reports=True,
        inspect_inline_images=True,
        validate_runtime_schema=True,
        model_contract_version="tepp-v1",
        output_profile="aggregate-and-product",
    )


def test_exact_text_digest_does_not_normalize_source_text() -> None:
    assert exact_text_sha256("select 1") != exact_text_sha256("select  1")
    with pytest.raises(TypeError, match="must be text"):
        exact_text_sha256(1)  # type: ignore[arg-type]


def test_canonical_json_digest_is_order_independent_and_rejects_nan() -> None:
    assert canonical_json_sha256({"b": 2, "a": 1}) == canonical_json_sha256(
        {"a": 1, "b": 2}
    )
    with pytest.raises(ValueError):
        canonical_json_sha256({"metric": math.nan})


@pytest.mark.parametrize(
    ("key", "revision", "digest", "message"),
    [
        ("Configured Primary", 1, DIGEST_A, "profile_key"),
        ("configured-primary", True, DIGEST_A, "profile_revision"),
        ("configured-primary", 0, DIGEST_A, "at least 1"),
        ("configured-primary", 1, "A" * 64, "lowercase SHA-256"),
        ("configured-primary", 1, DIGEST_A, None),
    ],
)
def test_source_profile_validation(
    key: str, revision: int, digest: str, message: str | None
) -> None:
    if message is None:
        assert SourceProfileReference(key, revision, digest).public_json()["profile_key"] == key
    else:
        with pytest.raises(AnalysisRunContractError, match=message):
            SourceProfileReference(key, revision, digest)


def test_source_kind_must_be_bounded_nonempty_text() -> None:
    with pytest.raises(AnalysisRunContractError, match="source_kind_code"):
        SourceProfileReference("configured-primary", 1, DIGEST_A, " ")
    with pytest.raises(AnalysisRunContractError, match="exceeds 64"):
        SourceProfileReference("configured-primary", 1, DIGEST_A, "x" * 65)


def test_snapshot_enforces_temporal_leakage_and_count_order() -> None:
    snapshot = _snapshot()
    assert snapshot.public_json()["row_count"] == 12
    with pytest.raises(AnalysisRunContractError, match="timezone-aware"):
        SourceSnapshotEvidence(
            DIGEST_B,
            datetime(2026, 8, 15),
            snapshot.maximum_available_time,
            12,
            10,
            8,
        )
    with pytest.raises(AnalysisRunContractError, match="must not exceed"):
        SourceSnapshotEvidence(
            DIGEST_B,
            snapshot.knowledge_cutoff,
            snapshot.knowledge_cutoff + timedelta(seconds=1),
            12,
            10,
            8,
        )
    with pytest.raises(AnalysisRunContractError, match="must be an integer"):
        SourceSnapshotEvidence(
            DIGEST_B,
            snapshot.knowledge_cutoff,
            snapshot.maximum_available_time,
            True,
            1,
            1,
        )
    with pytest.raises(AnalysisRunContractError, match="non-negative"):
        SourceSnapshotEvidence(
            DIGEST_B,
            snapshot.knowledge_cutoff,
            snapshot.maximum_available_time,
            -1,
            0,
            0,
        )
    with pytest.raises(AnalysisRunContractError, match="document_count"):
        SourceSnapshotEvidence(
            DIGEST_B,
            snapshot.knowledge_cutoff,
            snapshot.maximum_available_time,
            1,
            2,
            1,
        )
    with pytest.raises(AnalysisRunContractError, match="thread_count"):
        SourceSnapshotEvidence(
            DIGEST_B,
            snapshot.knowledge_cutoff,
            snapshot.maximum_available_time,
            2,
            1,
            2,
        )


def test_snapshot_rejects_invalid_digest_and_naive_available_time() -> None:
    snapshot = _snapshot()
    with pytest.raises(AnalysisRunContractError, match="source_digest_sha256"):
        SourceSnapshotEvidence(
            "bad",
            snapshot.knowledge_cutoff,
            snapshot.maximum_available_time,
            1,
            1,
            1,
        )
    with pytest.raises(AnalysisRunContractError, match="maximum_available_time"):
        SourceSnapshotEvidence(
            DIGEST_B,
            snapshot.knowledge_cutoff,
            datetime(2026, 8, 14),
            1,
            1,
            1,
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"row_limit": True}, "row_limit"),
        ({"row_limit": -1}, "non-negative"),
        ({"write_reports": 1}, "write_reports"),
        ({"inspect_inline_images": 1}, "inspect_inline_images"),
        ({"validate_runtime_schema": 1}, "validate_runtime_schema"),
        ({"model_contract_version": " "}, "model_contract_version"),
        ({"output_profile": "x" * 129}, "output_profile"),
    ],
)
def test_configuration_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "row_limit": 0,
        "write_reports": True,
        "inspect_inline_images": True,
        "validate_runtime_schema": True,
        "model_contract_version": "tepp-v1",
        "output_profile": "aggregate-and-product",
    }
    values.update(changes)
    with pytest.raises(AnalysisRunContractError, match=message):
        AnalysisRunConfiguration(**values)  # type: ignore[arg-type]


def test_registration_requires_safe_identifiers_and_aware_start_time() -> None:
    started = datetime(2026, 8, 15, 1, 0, tzinfo=UTC)
    registration = AnalysisRunRegistration("account-id", "run-key", started)
    assert registration.started_at == started
    for values, message in (
        ((" ", "run-key", started), "requested_by_account_id"),
        (("account-id", " ", started), "idempotency_key"),
        (("account-id", "x" * 256, started), "exceeds 255"),
        (("account-id", "run-key", datetime(2026, 8, 15)), "started_at"),
    ):
        with pytest.raises(AnalysisRunContractError, match=message):
            AnalysisRunRegistration(*values)


def test_request_digest_binds_profile_snapshot_and_configuration() -> None:
    configuration = _configuration()
    digest = configuration.request_digest(_profile(), _snapshot())
    assert len(digest) == 64
    changed = AnalysisRunConfiguration(
        **{**configuration.__dict__, "row_limit": 10}
    )
    assert changed.request_digest(_profile(), _snapshot()) != digest


def test_public_summary_contains_only_aggregate_safe_fields() -> None:
    started = datetime(2026, 8, 15, 1, 0, tzinfo=UTC)
    summary = AnalysisRunSummary(
        analysis_run_id="019-analysis-run",
        profile_key="configured-primary",
        profile_revision=1,
        run_status_code="analysis_run_succeeded",
        request_digest_sha256=DIGEST_A,
        source_digest_sha256=DIGEST_B,
        knowledge_cutoff=_snapshot().knowledge_cutoff,
        maximum_available_time=_snapshot().maximum_available_time,
        row_count=12,
        document_count=10,
        thread_count=8,
        started_at=started,
        completed_at=started + timedelta(minutes=2),
        configuration=_configuration(),
    )
    payload = summary.public_json()
    serialized = str(payload).lower()
    for forbidden in ("dsn", "sql", "query_text", "source_table", "raw_content"):
        assert forbidden not in serialized
    assert payload["source_snapshot"]["document_count"] == 10

    running = AnalysisRunSummary(
        analysis_run_id="019-running-run",
        profile_key="configured-primary",
        profile_revision=1,
        run_status_code="analysis_run_running",
        request_digest_sha256=DIGEST_A,
        source_digest_sha256=DIGEST_B,
        knowledge_cutoff=_snapshot().knowledge_cutoff,
        maximum_available_time=_snapshot().maximum_available_time,
        row_count=12,
        document_count=10,
        thread_count=8,
        started_at=started,
        completed_at=None,
        configuration=_configuration(),
    )
    assert running.public_json()["completed_at"] is None


def test_summary_rejects_invalid_lifecycle_and_identifiers() -> None:
    snapshot = _snapshot()
    config = _configuration()
    started = datetime(2026, 8, 15, 1, 0, tzinfo=UTC)
    base = dict(
        analysis_run_id="run-1",
        profile_key="configured-primary",
        profile_revision=1,
        run_status_code="analysis_run_running",
        request_digest_sha256=DIGEST_A,
        source_digest_sha256=DIGEST_B,
        knowledge_cutoff=snapshot.knowledge_cutoff,
        maximum_available_time=snapshot.maximum_available_time,
        row_count=12,
        document_count=10,
        thread_count=8,
        started_at=started,
        completed_at=None,
        configuration=config,
    )
    for field_name, value, message in (
        ("analysis_run_id", " ", "analysis_run_id"),
        ("profile_revision", True, "profile_revision"),
        ("profile_revision", 0, "at least 1"),
        ("run_status_code", " ", "run_status_code"),
        ("request_digest_sha256", "bad", "request_digest_sha256"),
        ("started_at", datetime(2026, 8, 15), "started_at"),
    ):
        values = {**base, field_name: value}
        with pytest.raises(AnalysisRunContractError, match=message):
            AnalysisRunSummary(**values)
    with pytest.raises(AnalysisRunContractError, match="completed_at"):
        AnalysisRunSummary(
            **{
                **base,
                "completed_at": datetime(2026, 8, 15),
            }
        )
    with pytest.raises(AnalysisRunContractError, match="must not precede"):
        AnalysisRunSummary(
            **{
                **base,
                "completed_at": started - timedelta(seconds=1),
            }
        )
