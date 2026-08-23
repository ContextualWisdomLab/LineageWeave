"""TEPP accepted receipts are transport evidence, never a measurement."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import pytest

from backend.app.analysis_run_ingestion import fetch_tepp_accepted_receipts
from backend.app.analysis_run_start import (
    _persist_tepp_accepted_receipt,
    _persist_tepp_result,
    classify_tepp_submission,
    tepp_receipt_digest,
    tepp_request_digest,
    tepp_run_request,
    tepp_submit_outcome,
)
from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable

_ROOT = Path(__file__).resolve().parents[1]


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _ReceiptConnection:
    def __init__(self, *, rows=None, error=None) -> None:
        self.rows = [] if rows is None else rows
        self.error = error
        self.transactions = 0
        self.executions: list[tuple[object, ...]] = []

    def transaction(self):
        self.transactions += 1
        return _Transaction()

    async def fetch(self, query, analysis_run_ids):
        if self.error is not None:
            raise self.error
        return self.rows

    async def fetchrow(self, query, analysis_run_id):
        if self.error is not None:
            raise self.error

    async def execute(self, *args):
        self.executions.append(args)
        if self.error is not None:
            raise self.error


def _request() -> AnalysisRunRequest:
    return tepp_run_request(
        idempotency_key="buyer-tepp-2026-w07",
        snapshot_sha256="ab" * 32,
        knowledge_cutoff=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
        corporate_entity_id="11111111-1111-1111-1111-111111111111",
    )


class _EnvelopeClient(TeppClient):
    def __init__(self, envelope: object) -> None:
        super().__init__(transport=lambda _payload: envelope)  # type: ignore[arg-type]


def test_missing_transport_stays_failed_not_available() -> None:
    outcome = classify_tepp_submission(TeppClient(), _request())
    assert outcome.status_code == "analysis_status_failed"
    assert outcome.failure_code == "tepp_not_available"
    assert outcome.persist_kind == ""
    assert outcome.envelope is None


def test_empty_accepted_envelope_is_not_a_receipt() -> None:
    outcome = classify_tepp_submission(_EnvelopeClient({"status": "accepted"}), _request())
    assert outcome.status_code == "analysis_status_failed"
    assert outcome.failure_code == "tepp_result_not_persisted"
    assert outcome.persist_kind == ""
    status, failure = tepp_submit_outcome(_EnvelopeClient({"status": "accepted"}), _request())
    assert status == "analysis_status_failed"
    assert failure == "tepp_result_not_persisted"


def test_accepted_with_remote_run_id_is_running_receipt() -> None:
    envelope = {"status": "accepted", "run_id": "tepp-run-accepted-1"}
    outcome = classify_tepp_submission(_EnvelopeClient(envelope), _request())
    assert outcome.status_code == "analysis_status_running"
    assert outcome.failure_code == ""
    assert outcome.persist_kind == "receipt"
    assert outcome.envelope == envelope
    assert "theta" not in str(outcome.envelope).casefold()


def test_queued_and_running_envelopes_are_receipts_not_results() -> None:
    queued = classify_tepp_submission(
        _EnvelopeClient({"run_state": "queued", "analysis_run_id": "tepp-queued-1"}),
        _request(),
    )
    running = classify_tepp_submission(
        _EnvelopeClient({"status": "running", "remote_run_id": "tepp-running-1"}),
        _request(),
    )
    assert queued.persist_kind == "receipt"
    assert running.persist_kind == "receipt"
    assert queued.status_code == "analysis_status_running"
    assert running.status_code == "analysis_status_running"
    assert queued.persist_kind != "result"
    assert running.persist_kind != "result"


def test_completed_result_is_the_only_measurement_persist() -> None:
    outcome = classify_tepp_submission(
        _EnvelopeClient(
            {
                "status": "completed",
                "analysis_run_id": "tepp-completed-1",
                "result": {"schema_version": "tepp-result-v1", "event_count": 3},
            }
        ),
        _request(),
    )
    assert outcome.status_code == "analysis_status_succeeded"
    assert outcome.persist_kind == "result"
    assert outcome.failure_code == ""


def test_completed_remote_run_id_alias_persists_the_result() -> None:
    connection = _ReceiptConnection()
    persisted = asyncio.run(
        _persist_tepp_result(
            connection,
            analysis_run_id="local-run",
            envelope={
                "status": "completed",
                "remote_run_id": "remote-run",
                "result": {"schema_version": "tepp-result-v1"},
            },
        )
    )
    assert persisted is True
    assert connection.executions[0][2] == "remote-run"


def test_receipt_insert_error_is_rolled_back_by_a_savepoint() -> None:
    connection = _ReceiptConnection(error=asyncpg.UniqueViolationError("duplicate"))
    persisted = asyncio.run(
        _persist_tepp_accepted_receipt(
            connection,
            analysis_run_id="local-run",
            envelope={"status": "accepted", "run_id": "remote-run"},
            request=_request(),
            knowledge_cutoff=datetime(2026, 1, 12, tzinfo=timezone.utc),
        )
    )
    assert persisted is False
    assert connection.transactions == 1


def test_missing_receipt_table_isolated_from_the_callers_transaction() -> None:
    connection = _ReceiptConnection(error=asyncpg.UndefinedTableError("missing"))
    receipts = asyncio.run(fetch_tepp_accepted_receipts(connection, ["local-run"]))
    assert receipts == {}
    assert connection.transactions == 1


def test_completed_without_result_is_not_a_measurement() -> None:
    outcome = classify_tepp_submission(
        _EnvelopeClient({"status": "succeeded", "run_id": "tepp-empty-1"}),
        _request(),
    )
    assert outcome.status_code == "analysis_status_failed"
    assert outcome.failure_code == "tepp_result_not_persisted"
    assert outcome.persist_kind == ""


def test_receipt_digest_is_stable_and_omits_result_bodies() -> None:
    request = _request()
    first = tepp_receipt_digest(
        remote_run_id="tepp-run-accepted-1",
        accepted_status_code="accepted",
        model_contract_version=request.model_contract_version,
        snapshot_id=request.snapshot_id,
        knowledge_cutoff=request.knowledge_cutoff,
    )
    second = tepp_receipt_digest(
        remote_run_id="tepp-run-accepted-1",
        accepted_status_code="accepted",
        model_contract_version=request.model_contract_version,
        snapshot_id=request.snapshot_id,
        knowledge_cutoff=request.knowledge_cutoff,
    )
    assert first == second
    assert len(first) == 64
    assert tepp_request_digest(request) != first
    assert "theta" not in tepp_request_digest(request)


def test_unavailable_transport_still_raises_on_direct_submit() -> None:
    with pytest.raises(TeppNotAvailable):
        TeppClient().submit_analysis_run(_request())


def test_migration_0106_is_transport_evidence_not_a_result_table() -> None:
    sql = (_ROOT / "migrations" / "0106_analysis_run_tepp_accepted_receipt.sql").read_text(
        encoding="utf-8"
    )
    rollback = (
        _ROOT / "migrations" / "rollback" / "0106_analysis_run_tepp_accepted_receipt.sql"
    ).read_text(encoding="utf-8")
    assert "analysis_run_tepp_accepted_receipt" in sql
    assert "create table if not exists analysis_run_tepp_accepted_receipt" in sql
    assert "accepted_status_code in ('accepted', 'queued', 'running')" in sql
    assert "remote_run_id text not null unique" in sql
    assert "request_sha256" in sql
    assert "receipt_sha256" in sql
    create_body = sql.split("create table", 1)[1]
    assert "jsonb" not in create_body.casefold()
    assert "theta" not in create_body.casefold()
    assert "result_json" not in create_body
    assert "drop table if exists analysis_run_tepp_accepted_receipt" in rollback
    table_names = [
        name
        for name in ("analysis_run_tepp_accepted_receipt",)
        if name in sql
    ]
    assert all(len(name.split("_")) >= 2 for name in table_names)


def test_migrate_sh_replays_accepted_receipt_migration() -> None:
    script = (_ROOT / "docker" / "postgres-init" / "migrate.sh").read_text(encoding="utf-8")
    assert "0106_*" in script
    assert "0104_*" not in script
    assert "0105_*" not in script


def test_adr_0157_keeps_measurement_authority_with_tepp() -> None:
    adr = (_ROOT / "docs" / "adr" / "0157-tepp-accepted-receipt.md").read_text(encoding="utf-8")
    assert "transport evidence" in adr.casefold()
    assert "do not invent a theta" in adr.casefold()
    assert "TEPP#156" in adr
    assert "analysis_run_tepp_accepted_receipt" in adr
    assert "stay Running" in adr or "leave the local run" in adr
