"""Seeded TEPP analysis runs go through tepp_client, never a local model."""

from datetime import datetime, timezone

from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable
from scripts.seed_demo_data import (
    DEMO_TEPP_ACCEPTED_IDEMPOTENCY_KEY,
    DEMO_TEPP_ACCEPTED_REMOTE_RUN_ID,
    _ensure_demo_source_counts,
    _seed_demo_tepp_accepted_run,
    _seed_demo_tepp_run,
    demo_source_snapshot_sha256,
    tepp_accepted_seed_client,
    tepp_accepted_seed_outcome,
    tepp_accepted_seed_request,
    tepp_seed_outcome,
    tepp_seed_request,
)
from backend.app.analysis_run_start import _tepp_submission


class _RecordingUnavailableClient(TeppClient):
    """Default-path stand-in that records the request then drops the channel."""

    def __init__(self) -> None:
        super().__init__()
        self.submitted: list[AnalysisRunRequest] = []

    def submit_analysis_run(self, request: AnalysisRunRequest) -> dict[str, object]:
        self.submitted.append(request)
        raise TeppNotAvailable("TEPP has no live HTTP endpoint yet.")


class _AcceptingClient(TeppClient):
    """Transport that returns an envelope without a persistable measurement."""

    def __init__(self) -> None:
        super().__init__(transport=lambda _payload: {"status": "accepted"})


class _CountCursor:
    """Minimal cursor for proving re-seed skips a frozen count insert."""

    def __init__(self, existing_counts: bool) -> None:
        self.existing_counts = existing_counts
        self.statements: list[str] = []

    def execute(self, sql: str, _params=None) -> None:
        self.statements.append(" ".join(sql.split()))

    def fetchone(self):
        if self.existing_counts and "from analysis_source_count" in self.statements[-1]:
            return (1,)
        return None


def test_tepp_seed_request_targets_the_shared_demo_snapshot() -> None:
    request = tepp_seed_request()
    assert request.snapshot_id == demo_source_snapshot_sha256()
    assert request.idempotency_key == "demo-tepp-seed-2026-w02"
    assert request.model_contract_version == "tepp-analysis-run-v1"
    assert request.output_profile == "calibrated_event_measurement"


def test_tepp_seed_outcome_calls_client_and_does_not_invent_a_score() -> None:
    client = _RecordingUnavailableClient()
    status, failure = tepp_seed_outcome(client)
    assert status == "analysis_status_failed"
    assert failure == "tepp_not_available"
    assert client.submitted == [tepp_seed_request()]


def test_tepp_seed_outcome_default_client_is_unavailable_not_a_fake_score() -> None:
    status, failure = tepp_seed_outcome()
    assert status == "analysis_status_failed"
    assert failure == "tepp_not_available"


def test_tepp_seed_outcome_does_not_treat_an_empty_envelope_as_success() -> None:
    status, failure = tepp_seed_outcome(_AcceptingClient())
    assert status == "analysis_status_failed"
    assert failure == "tepp_result_not_persisted"


def test_tepp_seed_outcome_keeps_strict_acceptance_running() -> None:
    status, failure = tepp_seed_outcome(
        TeppClient(
            transport=lambda payload: {
                "contract_version": 1,
                "run_id": "tepp-seed-accepted-1",
                "run_state": "accepted",
                "idempotency_key": payload["idempotency_key"],
            }
        )
    )
    assert status == "analysis_status_running"
    assert failure is None


def test_tepp_submission_rejects_boolean_contract_version() -> None:
    request = tepp_seed_request()
    status, failure, envelope = _tepp_submission(
        TeppClient(
            transport=lambda payload: {
                "contract_version": True,
                "run_id": "tepp-seed-accepted-1",
                "run_state": "accepted",
                "idempotency_key": payload["idempotency_key"],
            }
        ),
        request,
    )
    assert status == "analysis_status_failed"
    assert failure == "tepp_result_not_persisted"
    assert envelope is None


def test_tepp_submission_rejects_conflicting_state_aliases() -> None:
    request = tepp_seed_request()
    status, failure, envelope = _tepp_submission(
        TeppClient(
            transport=lambda payload: {
                "contract_version": 1,
                "run_id": "tepp-seed-accepted-1",
                "status": "accepted",
                "run_state": "completed",
                "idempotency_key": payload["idempotency_key"],
            }
        ),
        request,
    )
    assert status == "analysis_status_failed"
    assert failure == "tepp_result_not_persisted"
    assert envelope is None


def test_tepp_accepted_seed_request_shares_the_demo_snapshot() -> None:
    request = tepp_accepted_seed_request("corp-1")
    assert request.snapshot_id == demo_source_snapshot_sha256()
    assert request.idempotency_key == DEMO_TEPP_ACCEPTED_IDEMPOTENCY_KEY
    assert request.model_contract_version == "tepp-lineage-criterion-v1"
    assert request.output_profile == "lineage_pair_criterion_anchor"
    assert request.tenant_workspace_id == "corp-1"
    assert "theta" not in str(request.to_json()).casefold()


def test_tepp_accepted_seed_outcome_is_running_transport_evidence() -> None:
    status, failure, envelope = tepp_accepted_seed_outcome(tepp_accepted_seed_client())
    assert status == "analysis_status_running"
    assert failure is None
    assert envelope == {
        "contract_version": 1,
        "run_id": DEMO_TEPP_ACCEPTED_REMOTE_RUN_ID,
        "run_state": "accepted",
        "idempotency_key": DEMO_TEPP_ACCEPTED_IDEMPOTENCY_KEY,
    }


def test_ensure_demo_source_counts_skips_insert_when_counts_exist() -> None:
    cursor = _CountCursor(existing_counts=True)
    _ensure_demo_source_counts(cursor, "snapshot-1")
    assert any("from analysis_source_count" in sql for sql in cursor.statements)
    assert not any(sql.lstrip().startswith("insert into analysis_source_count") for sql in cursor.statements)


def test_ensure_demo_source_counts_inserts_when_the_snapshot_is_empty() -> None:
    cursor = _CountCursor(existing_counts=False)
    _ensure_demo_source_counts(cursor, "snapshot-1")
    assert any(sql.lstrip().startswith("insert into analysis_source_count") for sql in cursor.statements)


class _TeppSeedCursor:
    """Drive `_seed_demo_tepp_run` without a live database."""

    def __init__(self) -> None:
        self.statements: list[str] = []
        self.params: list[object] = []

    def execute(self, sql: str, params=None) -> None:
        self.statements.append(" ".join(sql.split()))
        self.params.append(params)

    def fetchone(self):
        last = self.statements[-1]
        if last.lstrip().startswith("select") and "from analysis_source_snapshot" in last:
            return None
        if "insert into analysis_source_snapshot" in last:
            return ("snapshot-demo",)
        if last.lstrip().startswith("select") and "from analysis_source_count" in last:
            return None
        if last.lstrip().startswith("select") and "from analysis_run where" in last:
            return None
        if "insert into analysis_run" in last:
            return ("run-demo-tepp",)
        if "insert into analysis_run_tepp_receipt" in last:
            return ("run-demo-tepp",)
        if last.lstrip().startswith("select") and "from analysis_run_outbox" in last:
            return None
        if last.lstrip().startswith("select") and "run.run_kind_code" in last:
            return (
                "analysis_run_tepp",
                datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
                "ab" * 32,
            )
        return None


class _ExistingRunningTeppSeedCursor(_TeppSeedCursor):
    """Model a reseed whose accepted receipt conflicts after Running."""

    def fetchone(self):
        last = self.statements[-1]
        row = (
            2,
            False,
            "different-run",
            "different-request",
            "different-receipt",
            1,
            "run-demo-tepp",
        )
        if "max(status_ordinal)" in last:
            return row[:2]
        if "from analysis_run_tepp_receipt" in last:
            return row[2:5]
        if "max(delivery_ordinal)" in last:
            return row[5:6] + row[1:2]
        if last.lstrip().startswith("select") and "from analysis_run_outbox" in last:
            return row[5:6]
        if last.lstrip().startswith("select") and "from analysis_run where" in last:
            return row[6:7]
        return super().fetchone()


def test_seed_demo_tepp_run_inserts_failed_tepp_not_available() -> None:
    cursor = _TeppSeedCursor()
    _seed_demo_tepp_run(cursor, "account-1", "corp-1")
    run_inserts = [sql for sql in cursor.statements if "insert into analysis_run" in sql]
    assert run_inserts, "seed must insert the TEPP analysis_run row"
    assert any("analysis_run_tepp" in sql for sql in run_inserts)
    status_params = [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run_status_event" in sql
    ]
    assert any(
        params is not None and "analysis_status_failed" in params and "tepp_not_available" in params
        for params in status_params
    )
    assert not any(
        params is not None and "analysis_status_succeeded" in params for params in status_params
    )
    assert not any("insert into analysis_run_tepp_receipt" in sql for sql in cursor.statements)


def test_seed_demo_tepp_accepted_run_stays_running_with_receipt() -> None:
    cursor = _TeppSeedCursor()
    _seed_demo_tepp_accepted_run(cursor, "account-1", "corp-1")
    run_params = [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run" in sql and "analysis_run_tepp" in sql
    ]
    assert any(
        params is not None and DEMO_TEPP_ACCEPTED_IDEMPOTENCY_KEY in params
        for params in run_params
    )
    receipt_params = [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run_tepp_receipt" in sql
    ]
    assert receipt_params
    assert DEMO_TEPP_ACCEPTED_REMOTE_RUN_ID in receipt_params[0]
    status_params = [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run_status_event" in sql
    ]
    assert any(
        params is not None and "analysis_status_running" in params for params in status_params
    )
    assert not any(
        params is not None and "analysis_status_failed" in params for params in status_params
    )
    assert not any(
        params is not None and "analysis_status_succeeded" in params for params in status_params
    )
    delivery_params = [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run_outbox_delivery" in sql
    ]
    assert any(
        params is not None and "analysis_outbox_claimed" in params for params in delivery_params
    )
    assert not any(
        params is not None and "analysis_outbox_delivered" in params
        for params in delivery_params
    )
    assert not any("theta" in str(params).casefold() for params in cursor.params)


def test_seed_demo_tepp_accepted_run_appends_failed_after_receipt_conflict() -> None:
    cursor = _ExistingRunningTeppSeedCursor()
    _seed_demo_tepp_accepted_run(cursor, "account-1", "corp-1")
    status_params = [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run_status_event" in sql
    ]
    assert status_params == [
        (
            "run-demo-tepp",
            3,
            "analysis_status_failed",
            "2026-01-12T12:37:00Z",
            "tepp_result_not_persisted",
        )
    ]
    delivery_params = [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run_outbox_delivery" in sql
    ]
    assert delivery_params == [
        (
            "run-demo-tepp",
            2,
            datetime(2026, 1, 12, 12, 37, tzinfo=timezone.utc),
        )
    ]
    assert not any("theta" in str(params).casefold() for params in cursor.params)


class _ConflictingReceiptCursor(_TeppSeedCursor):
    """Model a remote-run uniqueness conflict at receipt insertion."""

    def fetchone(self):
        if "insert into analysis_run_tepp_receipt" in self.statements[-1]:
            return None
        return super().fetchone()


def test_seed_demo_tepp_receipt_conflict_fails_instead_of_remaining_running() -> None:
    cursor = _ConflictingReceiptCursor()
    _seed_demo_tepp_accepted_run(cursor, "account-1", "corp-1")
    status_params = [
        params
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into analysis_run_status_event" in sql
    ]
    assert any(
        params is not None
        and "analysis_status_failed" in params
        and "tepp_result_not_persisted" in params
        for params in status_params
    )
