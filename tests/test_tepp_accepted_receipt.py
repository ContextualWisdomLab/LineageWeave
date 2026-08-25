"""TEPP accepted receipts are transport evidence, never a measurement."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import pytest

import backend.app.analysis_run_start as analysis_run_start_module
from backend.app.analysis_run_ingestion import (
    fetch_outbox_deliveries,
    fetch_reconstructed_edges,
    fetch_tepp_accepted_receipts,
)
from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable

_ROOT = Path(__file__).resolve().parents[1]


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _ReceiptConnection:
    def __init__(self, *, rows=None, row=None, result_row=None, error=None) -> None:
        self.rows = [] if rows is None else rows
        self.row = row
        self.result_row = result_row
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
        if "from analysis_run_tepp_result" in query:
            return self.result_row
        return self.row

    async def execute(self, *args):
        self.executions.append(args)
        if self.error is not None:
            raise self.error

    async def fetchval(self, query, *args):
        if "select delivery_status_code" in query:
            return "analysis_outbox_claimed"
        if "max(status_ordinal)" in query or "max(delivery_ordinal)" in query:
            return 1
        raise AssertionError(f"Unexpected fetchval query: {query}")


def _request() -> AnalysisRunRequest:
    return analysis_run_start_module.tepp_run_request(
        idempotency_key="buyer-tepp-2026-w07",
        snapshot_sha256="ab" * 32,
        knowledge_cutoff=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
        corporate_entity_id="11111111-1111-1111-1111-111111111111",
    )


class _EnvelopeClient(TeppClient):
    def __init__(self, envelope: object) -> None:
        super().__init__(transport=lambda _payload: envelope)  # type: ignore[arg-type]


def test_missing_transport_stays_failed_not_available() -> None:
    outcome = analysis_run_start_module.classify_tepp_submission(TeppClient(), _request())
    assert outcome.status_code == "analysis_status_failed"
    assert outcome.failure_code == "tepp_not_available"
    assert outcome.persist_kind == ""
    assert outcome.envelope is None


@pytest.mark.parametrize(
    "tepp_client",
    [TeppClient(), _EnvelopeClient({"status": "accepted"})],
    ids=["transport-unavailable", "empty-accepted-envelope"],
)
def test_unpersistable_recheck_keeps_an_already_accepted_run_claimed(
    monkeypatch, tepp_client,
) -> None:
    analysis_run_id = "11111111-1111-1111-1111-111111111111"
    visible = {
        "analysis_run_id": analysis_run_id,
        "status_code": "analysis_status_running",
    }

    async def fetch_visible(*_args, **_kwargs):
        return visible

    monkeypatch.setattr(
        analysis_run_start_module,
        "fetch_visible_analysis_run",
        fetch_visible,
    )
    connection = _ReceiptConnection(
        row={
            "analysis_run_id": analysis_run_id,
            "work_kind_code": "analysis_run_tepp",
            "knowledge_cutoff": datetime(2026, 1, 12, tzinfo=timezone.utc),
            "idempotency_key": "buyer-tepp-2026-w07",
            "analysis_source_snapshot_id": "snapshot-1",
            "snapshot_sha256": "ab" * 32,
            "corporate_entity_id": "22222222-2222-2222-2222-222222222222",
        },
        rows=[
            {
                "analysis_run_id": analysis_run_id,
                "remote_run_id": "remote-run-1",
                "accepted_status_code": "accepted",
                "received_at": datetime(2026, 1, 12, tzinfo=timezone.utc),
            }
        ],
    )

    result = asyncio.run(
        analysis_run_start_module.deliver_queued_analysis_run(
            connection,
            analysis_run_id=analysis_run_id,
            account_id="account-1",
            affiliated_entity_ids=[],
            tepp_client=tepp_client,
        )
    )

    assert result["status_code"] == "analysis_status_running"
    assert not any(
        "insert into analysis_run_status_event" in str(execution[0])
        for execution in connection.executions
    )
    assert not any(
        "analysis_outbox_delivered" in execution
        for execution in connection.executions
    )


def test_initial_unavailability_without_a_receipt_remains_terminal() -> None:
    connection = _ReceiptConnection(rows=[])

    terminal = asyncio.run(
        analysis_run_start_module._deliver_tepp_measurement(
            connection,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            locked={
                "knowledge_cutoff": datetime(2026, 1, 12, tzinfo=timezone.utc),
                "idempotency_key": "buyer-tepp-2026-w07",
                "snapshot_sha256": "ab" * 32,
                "corporate_entity_id": "22222222-2222-2222-2222-222222222222",
            },
            tepp_client=TeppClient(),
        )
    )

    assert terminal is True
    assert any(
        execution[3:] == ("analysis_status_failed", "tepp_not_available")
        for execution in connection.executions
    )


def test_empty_accepted_envelope_is_not_a_receipt() -> None:
    outcome = analysis_run_start_module.classify_tepp_submission(
        _EnvelopeClient({"status": "accepted"}), _request()
    )
    assert outcome.status_code == "analysis_status_failed"
    assert outcome.failure_code == "tepp_result_not_persisted"
    assert outcome.persist_kind == ""
    status, failure = analysis_run_start_module.tepp_submit_outcome(
        _EnvelopeClient({"status": "accepted"}), _request()
    )
    assert status == "analysis_status_failed"
    assert failure == "tepp_result_not_persisted"


def test_accepted_with_remote_run_id_is_running_receipt() -> None:
    envelope = {"status": "accepted", "run_id": "tepp-run-accepted-1"}
    outcome = analysis_run_start_module.classify_tepp_submission(
        _EnvelopeClient(envelope), _request()
    )
    assert outcome.status_code == "analysis_status_running"
    assert outcome.failure_code == ""
    assert outcome.persist_kind == "receipt"
    assert outcome.envelope == envelope
    assert "theta" not in str(outcome.envelope).casefold()


def test_queued_and_running_envelopes_are_receipts_not_results() -> None:
    queued = analysis_run_start_module.classify_tepp_submission(
        _EnvelopeClient({"run_state": "queued", "analysis_run_id": "tepp-queued-1"}),
        _request(),
    )
    running = analysis_run_start_module.classify_tepp_submission(
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
    outcome = analysis_run_start_module.classify_tepp_submission(
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


def _terminal_status(state: str = "succeeded") -> dict:
    request = _request()
    failed = state == "failed"
    terminal = {
        "contract_version": 1,
        "run_id": "remote-run-1",
        "run_state": state,
        "idempotency_key": request.idempotency_key,
        "tenant_workspace_id": request.tenant_workspace_id,
        "snapshot_id": request.snapshot_id,
        "knowledge_cutoff": request.knowledge_cutoff,
        "model_contract_version": request.model_contract_version,
        "output_profile": request.output_profile,
        "result_artifact_id": None if failed else "artifact-1",
        "result_sha256": None if failed else "ab" * 32,
        "result_schema_version": None if failed else "tepp-result-v1",
        "completed_at": "2026-01-12T13:00:00Z",
        "summary": None
        if failed
        else {
            "analysis_family": "temporal_event_measurement",
            "evidence_count": 4,
            "statistic_count": 2,
            "validation_status": "validated",
        },
        "failure_code": "estimation_failed" if failed else None,
    }
    return {
        "contract_version": 1,
        "run_id": "remote-run-1",
        "run_state": state,
        "idempotency_key": request.idempotency_key,
        "terminal_result": terminal,
    }


def test_status_read_promotes_only_validated_terminal_result() -> None:
    status = _terminal_status()
    client = TeppClient(status_transport=lambda _run_id: status)

    outcome = analysis_run_start_module.classify_tepp_status(
        client, _request(), "remote-run-1"
    )

    assert outcome.status_code == "analysis_status_succeeded"
    assert outcome.persist_kind == "result"
    assert outcome.envelope == status["terminal_result"]


def test_status_read_maps_provider_terminal_failure_without_result() -> None:
    status = _terminal_status("failed")
    client = TeppClient(status_transport=lambda _run_id: status)

    outcome = analysis_run_start_module.classify_tepp_status(
        client, _request(), "remote-run-1"
    )

    assert outcome.status_code == "analysis_status_failed"
    assert outcome.failure_code == "estimation_failed"
    assert outcome.persist_kind == ""


def test_status_read_keeps_provider_running_and_fails_closed_on_invalid() -> None:
    request = _request()
    running = {
        "contract_version": 1,
        "run_id": "remote-run-1",
        "run_state": "running",
        "idempotency_key": request.idempotency_key,
        "terminal_result": None,
    }
    running_outcome = analysis_run_start_module.classify_tepp_status(
        TeppClient(status_transport=lambda _run_id: running),
        request,
        "remote-run-1",
    )
    invalid_outcome = analysis_run_start_module.classify_tepp_status(
        TeppClient(status_transport=lambda _run_id: {}),
        request,
        "remote-run-1",
    )

    assert running_outcome.status_code == "analysis_status_running"
    assert running_outcome.persist_kind == ""
    assert invalid_outcome.status_code == "analysis_status_failed"
    assert invalid_outcome.failure_code == "tepp_result_not_persisted"


def test_running_delivery_reads_and_persists_terminal_status(monkeypatch) -> None:
    analysis_run_id = "11111111-1111-1111-1111-111111111111"
    visible_calls = 0

    async def fetch_visible(*_args, **_kwargs):
        nonlocal visible_calls
        visible_calls += 1
        return {
            "analysis_run_id": analysis_run_id,
            "status_code": (
                "analysis_status_running"
                if visible_calls == 1
                else "analysis_status_succeeded"
            ),
        }

    monkeypatch.setattr(analysis_run_start_module, "fetch_visible_analysis_run", fetch_visible)
    connection = _ReceiptConnection(
        row={
            "analysis_run_id": analysis_run_id,
            "work_kind_code": "analysis_run_tepp",
            "knowledge_cutoff": datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
            "idempotency_key": "buyer-tepp-2026-w07",
            "analysis_source_snapshot_id": "snapshot-1",
            "snapshot_sha256": "ab" * 32,
            "corporate_entity_id": "11111111-1111-1111-1111-111111111111",
        },
        rows=[
            {
                "analysis_run_id": analysis_run_id,
                "remote_run_id": "remote-run-1",
                "accepted_status_code": "accepted",
                "received_at": datetime(2026, 1, 12, tzinfo=timezone.utc),
            }
        ],
    )
    status = _terminal_status()
    client = TeppClient(status_transport=lambda _run_id: status)

    result = asyncio.run(
        analysis_run_start_module.deliver_queued_analysis_run(
            connection,
            analysis_run_id=analysis_run_id,
            account_id="account-1",
            affiliated_entity_ids=[],
            tepp_client=client,
        )
    )

    assert result["status_code"] == "analysis_status_succeeded"
    assert any(
        "insert into analysis_run_tepp_result" in str(execution[0])
        for execution in connection.executions
    )
    assert any(
        "analysis_outbox_delivered" in execution for execution in connection.executions
    )


def test_completed_remote_run_id_alias_persists_the_result() -> None:
    connection = _ReceiptConnection()
    persisted = asyncio.run(
        analysis_run_start_module._persist_tepp_result(
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


def test_completed_result_replay_rejects_changed_digest() -> None:
    connection = _ReceiptConnection(
        result_row={"remote_run_id": "remote-run", "result_sha256": "0" * 64}
    )
    persisted = asyncio.run(
        analysis_run_start_module._persist_tepp_result(
            connection,
            analysis_run_id="local-run",
            envelope={
                "contract_version": 1,
                "run_id": "remote-run",
                "run_state": "succeeded",
            },
        )
    )

    assert persisted is False
    assert connection.executions == []


def test_receipt_insert_error_is_rolled_back_by_a_savepoint() -> None:
    connection = _ReceiptConnection(error=asyncpg.UniqueViolationError("duplicate"))
    persisted = asyncio.run(
        analysis_run_start_module._persist_tepp_accepted_receipt(
            connection,
            analysis_run_id="local-run",
            envelope={"status": "accepted", "run_id": "remote-run"},
            request=_request(),
            knowledge_cutoff=datetime(2026, 1, 12, tzinfo=timezone.utc),
        )
    )
    assert persisted is False
    assert connection.transactions == 1


def test_receipt_transport_progression_keeps_the_same_run_running() -> None:
    request = _request()
    connection = _ReceiptConnection(
        row={
            "remote_run_id": "remote-run",
            "request_sha256": analysis_run_start_module.tepp_request_digest(request),
        }
    )
    persisted = asyncio.run(
        analysis_run_start_module._persist_tepp_accepted_receipt(
            connection,
            analysis_run_id="local-run",
            envelope={"status": "running", "run_id": "remote-run"},
            request=request,
            knowledge_cutoff=datetime(2026, 1, 12, tzinfo=timezone.utc),
        )
    )
    assert persisted is True
    assert connection.executions == []


def test_receipt_replay_fails_closed_when_remote_run_id_changes() -> None:
    request = _request()
    connection = _ReceiptConnection(
        row={
            "remote_run_id": "different-remote-run",
            "request_sha256": analysis_run_start_module.tepp_request_digest(request),
        }
    )
    persisted = asyncio.run(
        analysis_run_start_module._persist_tepp_accepted_receipt(
            connection,
            analysis_run_id="local-run",
            envelope={"status": "running", "run_id": "remote-run"},
            request=request,
            knowledge_cutoff=datetime.fromisoformat(request.knowledge_cutoff),
        )
    )
    assert persisted is False
    assert connection.executions == []


def test_receipt_replay_fails_closed_when_request_digest_changes() -> None:
    request = _request()
    connection = _ReceiptConnection(
        row={
            "remote_run_id": "remote-run",
            "request_sha256": "cd" * 32,
        }
    )
    persisted = asyncio.run(
        analysis_run_start_module._persist_tepp_accepted_receipt(
            connection,
            analysis_run_id="local-run",
            envelope={"status": "running", "run_id": "remote-run"},
            request=request,
            knowledge_cutoff=datetime.fromisoformat(request.knowledge_cutoff),
        )
    )
    assert persisted is False
    assert connection.executions == []


def test_missing_receipt_table_isolated_from_the_callers_transaction() -> None:
    connection = _ReceiptConnection(error=asyncpg.UndefinedTableError("missing"))
    receipts = asyncio.run(fetch_tepp_accepted_receipts(connection, ["local-run"]))
    assert receipts == {}
    assert connection.transactions == 1


def test_legacy_optional_reads_isolate_missing_tables() -> None:
    outbox = _ReceiptConnection(error=asyncpg.UndefinedTableError("missing"))
    reconstruction = _ReceiptConnection(error=asyncpg.UndefinedTableError("missing"))

    assert asyncio.run(fetch_outbox_deliveries(outbox, "local-run")) == []
    assert asyncio.run(fetch_reconstructed_edges(reconstruction, "local-run", [])) == (
        None,
        [],
    )
    assert outbox.transactions == reconstruction.transactions == 1


def test_completed_without_result_is_not_a_measurement() -> None:
    outcome = analysis_run_start_module.classify_tepp_submission(
        _EnvelopeClient({"status": "succeeded", "run_id": "tepp-empty-1"}),
        _request(),
    )
    assert outcome.status_code == "analysis_status_failed"
    assert outcome.failure_code == "tepp_result_not_persisted"
    assert outcome.persist_kind == ""


def test_receipt_digest_is_stable_and_omits_result_bodies() -> None:
    request = _request()
    first = analysis_run_start_module.tepp_receipt_digest(
        remote_run_id="tepp-run-accepted-1",
        accepted_status_code="accepted",
        model_contract_version=request.model_contract_version,
        snapshot_id=request.snapshot_id,
        knowledge_cutoff=request.knowledge_cutoff,
    )
    second = analysis_run_start_module.tepp_receipt_digest(
        remote_run_id="tepp-run-accepted-1",
        accepted_status_code="accepted",
        model_contract_version=request.model_contract_version,
        snapshot_id=request.snapshot_id,
        knowledge_cutoff=request.knowledge_cutoff,
    )
    assert first == second
    assert len(first) == 64
    assert analysis_run_start_module.tepp_request_digest(request) != first
    assert "theta" not in analysis_run_start_module.tepp_request_digest(request)


def test_unavailable_transport_still_raises_on_direct_submit() -> None:
    with pytest.raises(TeppNotAvailable):
        TeppClient().submit_analysis_run(_request())


def test_migration_0171_is_transport_evidence_not_a_result_table() -> None:
    sql = (_ROOT / "migrations" / "0171_analysis_run_tepp_accepted_receipt.sql").read_text(
        encoding="utf-8"
    )
    rollback = (
        _ROOT / "migrations" / "rollback" / "0171_analysis_run_tepp_accepted_receipt.sql"
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
    tenant_settings = (_ROOT / "migrations" / "0103_tenant_settings.sql").read_text(
        encoding="utf-8"
    )
    assert "0103_*" in script
    assert "0171_*" in script
    assert "CREATE TABLE IF NOT EXISTS tenant_settings" in tenant_settings
    assert "ON CONFLICT (id) DO NOTHING" in tenant_settings


def test_adr_0162_keeps_measurement_authority_with_tepp() -> None:
    adr = (_ROOT / "docs" / "adr" / "0162-tepp-accepted-receipt.md").read_text(encoding="utf-8")
    assert "transport evidence" in adr.casefold()
    assert "do not invent a theta" in adr.casefold()
    assert "TEPP#156" in adr
    assert "analysis_run_tepp_accepted_receipt" in adr
    assert "stay Running" in adr or "leave the local run" in adr
    assert "GET /api/analysis-runs` and `GET /api/analysis-runs/{id}`" in adr
