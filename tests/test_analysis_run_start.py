"""Start-reconstruction contracts: digest, freeze, 422/409, designed tree."""

import asyncio
from datetime import datetime, timezone
from functools import lru_cache

import pytest

from backend.app import analysis_run_start
from backend.app.analysis_run_ingestion import reconstructed_edge_is_visible
from backend.app.analysis_run_start import (
    AnalysisRunStartError,
    _persist_tepp_receipt,
    _persist_tepp_terminal_result,
    _persist_tepp_result,
    configured_tepp_client,
    reconstruction_member_ids,
    reconstruction_result_digest,
    start_kind_rejection,
    start_write_conflict_error,
    tepp_run_request,
    tepp_submit_outcome,
    topic_lineage_run_request,
    topic_lineage_submit_outcome,
)
from backend.app.lineage_ingestion import records_from_source_posts
from lineageweave.channel_weight_estimation import estimate_fixture_channel_weights
from lineageweave.fixtures import sample_records
from lineageweave.http_client import HttpClientError
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable

@lru_cache(maxsize=1)
def _estimated_fixture_weights() -> dict[str, float]:
    """Return the fast-mlsirm estimate or fail the test closed."""
    estimate = estimate_fixture_channel_weights()
    assert estimate is not None
    return estimate.weights


@pytest.mark.anyio
async def test_delivery_releases_pool_during_provider_work_and_closes_run_lock(monkeypatch):
    """ADR 0204: provider latency owns neither a transaction nor a pool slot."""
    active_pool_leases = 0

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

    class Connection:
        def transaction(self):
            return Transaction()

    class Acquire:
        async def __aenter__(self):
            nonlocal active_pool_leases
            active_pool_leases += 1
            return Connection()

        async def __aexit__(self, *_args):
            nonlocal active_pool_leases
            active_pool_leases -= 1
            return False

    class Pool:
        def acquire(self):
            return Acquire()

    class LockConnection:
        closed = False

        async def fetchval(self, query, run_id):
            assert "pg_try_advisory_lock" in query
            assert "lineageweave:analysis-run:" in query
            assert run_id == "00000000-0000-0000-0000-000000000001"
            return True

        async def close(self):
            self.closed = True

    lock_connection = LockConnection()
    plan = analysis_run_start._DeliveryPlan(
        "analysis_run_tepp",
        datetime(2026, 8, 25, tzinfo=timezone.utc),
        {},
    )

    async def fake_claim(*_args, **_kwargs):
        assert active_pool_leases == 1
        return plan

    def fake_execute(*_args):
        assert active_pool_leases == 0
        return analysis_run_start._DeliveryOutcome(
            "analysis_run_tepp", plan.started_at, status_code="analysis_status_failed"
        )

    async def fake_persist(*_args, **_kwargs):
        assert active_pool_leases == 1
        return {"status_code": "analysis_status_failed"}

    async def fake_connect(_database_url):
        return lock_connection

    monkeypatch.setattr(analysis_run_start.asyncpg, "connect", fake_connect)
    monkeypatch.setattr(analysis_run_start, "_claim_delivery_plan", fake_claim)
    monkeypatch.setattr(analysis_run_start, "_execute_delivery_plan", fake_execute)
    monkeypatch.setattr(analysis_run_start, "_persist_delivery_outcome", fake_persist)

    result = await analysis_run_start.deliver_queued_analysis_run(
        Pool(),
        database_url="postgresql://synthetic",
        analysis_run_id="00000000-0000-0000-0000-000000000001",
        account_id="synthetic-account",
        affiliated_entity_ids=[],
    )

    assert result == {"status_code": "analysis_status_failed"}
    assert active_pool_leases == 0
    assert lock_connection.closed


def test_reconstruction_digest_is_stable_and_ignores_edge_order() -> None:
    """The same parent choices hash the same way regardless of insert order."""
    edges = lineage_edge_specs(sample_records(), weights=_estimated_fixture_weights())
    reversed_edges = list(reversed(edges))
    assert reconstruction_result_digest(edges) == reconstruction_result_digest(reversed_edges)
    assert reconstruction_result_digest([]) == reconstruction_result_digest([])
    assert reconstruction_result_digest(edges) != reconstruction_result_digest([])


def test_start_uses_the_same_parent_choices_as_library_reconstruct() -> None:
    """The product start path must recover the designed A-100 fork.

    fixtures.sample_records() is the synthetic gold tree: rec-002 is the
    branch point for the revised quote and the delivery question. A start
    that dropped an edge or invented a parent would fail this check.
    """
    weights = _estimated_fixture_weights()
    edges = lineage_edge_specs(sample_records(), weights=weights)
    children = {edge.child_id for edge in edges if edge.parent_id == "rec-002"}
    assert children >= {"rec-003", "rec-004"}
    assert all(0.0 <= edge.fused_score <= 1.0 for edge in edges)
    assert "theta" not in reconstruction_result_digest(edges)


def test_start_wiring_recovers_a100_from_source_post_rows() -> None:
    """CI must exercise records_from_source_posts, not only library reconstruct."""
    rows = [
        {
            "post_id": record.record_id,
            "post_title": record.label,
            "created_at": record.occurred_at,
            "thread_group_key": record.group_key,
            "secondary_grouping_key": record.secondary_key,
            "process_unit_id": None,
            "corporate_entity_id": "corp-demo",
        }
        for record in sample_records()
    ]
    weights = _estimated_fixture_weights()
    edges = lineage_edge_specs(records_from_source_posts(rows), weights=weights)
    children = {edge.child_id for edge in edges if edge.parent_id == "rec-002"}
    assert children >= {"rec-003", "rec-004"}
    assert reconstruction_result_digest(edges) == reconstruction_result_digest(
        lineage_edge_specs(sample_records(), weights=weights)
    )


def test_snapshot_members_exclude_a_later_backfill() -> None:
    """Start reconstructs the create-time bag, not a later cutoff re-query."""
    captured = ["rec-001", "rec-002", "rec-003", "rec-004"]
    cutoff_with_backfill = [*captured, "rec-backfill"]
    assert reconstruction_member_ids(captured, cutoff_with_backfill) == captured
    assert reconstruction_member_ids([], cutoff_with_backfill) == cutoff_with_backfill


def test_reconstructed_edge_hides_unaffiliated_private_titles() -> None:
    """Edge titles use the same public-or-affiliated rule as cutoff posts."""
    affiliated = ["corp-demo"]
    assert reconstructed_edge_is_visible(
        parent_visibility_code="public",
        parent_corporate_entity_id="corp-other",
        child_visibility_code="public",
        child_corporate_entity_id="corp-other",
        affiliated_entity_ids=affiliated,
    )
    assert not reconstructed_edge_is_visible(
        parent_visibility_code="private",
        parent_corporate_entity_id="corp-other",
        child_visibility_code="public",
        child_corporate_entity_id="corp-demo",
        affiliated_entity_ids=affiliated,
    )


def test_period_report_start_is_unprocessable_and_tepp_is_allowed() -> None:
    """Period-report stays 422. TEPP/topic-lineage start is allowed so tepp_client can run."""
    report = start_kind_rejection("analysis_run_report")
    assert report is not None
    assert report.status_code == 422
    assert "invent a measurement" in report.detail
    assert "period report" in report.detail
    assert start_kind_rejection("analysis_run_lineage") is None
    assert start_kind_rejection("analysis_run_tepp") is None
    assert start_kind_rejection("analysis_run_topic_lineage") is None


def _tepp_request() -> AnalysisRunRequest:
    return tepp_run_request(
        idempotency_key="buyer-tepp-2026-w07",
        snapshot_sha256="ab" * 32,
        knowledge_cutoff=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
        corporate_entity_id="11111111-1111-1111-1111-111111111111",
    )


def test_tepp_delivery_separates_acceptance_from_terminal_measurement() -> None:
    locked = {
        "idempotency_key": "buyer-tepp-2026-w07",
        "snapshot_sha256": "ab" * 32,
        "knowledge_cutoff": datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
        "corporate_entity_id": "11111111-1111-1111-1111-111111111111",
        "remote_run_id": None,
    }
    plan = analysis_run_start._DeliveryPlan(
        "analysis_run_tepp", datetime(2026, 1, 12, tzinfo=timezone.utc), locked
    )
    accepted = analysis_run_start._execute_delivery_plan(
        plan,
        TeppClient(
            transport=lambda _payload: {
                "contract_version": 1,
                "run_id": "remote-run-1",
                "run_state": "accepted",
                "idempotency_key": "buyer-tepp-2026-w07",
            }
        ),
        None,
    )

    assert accepted.status_code == "analysis_status_running"
    assert accepted.persist_receipt
    assert accepted.request == _tepp_request()


def test_tepp_delivery_reads_a_stored_remote_run_without_resubmitting() -> None:
    request = _tepp_request()
    status = {
        "contract_version": 1,
        "run_id": "remote-run-1",
        "run_state": "running",
        "idempotency_key": request.idempotency_key,
        "terminal_result": None,
    }
    locked = {
        "idempotency_key": request.idempotency_key,
        "snapshot_sha256": request.snapshot_id,
        "knowledge_cutoff": datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
        "corporate_entity_id": request.tenant_workspace_id,
        "remote_run_id": "remote-run-1",
    }
    outcome = analysis_run_start._execute_delivery_plan(
        analysis_run_start._DeliveryPlan(
            "analysis_run_tepp", datetime(2026, 1, 12, tzinfo=timezone.utc), locked
        ),
        TeppClient(
            transport=lambda _payload: pytest.fail("accepted work was resubmitted"),
            status_transport=lambda _run_id: status,
        ),
        None,
    )

    assert outcome.status_code == "analysis_status_running"
    assert not outcome.persist_receipt


def test_tepp_delivery_keeps_the_full_terminal_status_for_persistence() -> None:
    request = _tepp_request()
    terminal = {
        "contract_version": 1,
        "run_id": "remote-run-1",
        "run_state": "succeeded",
        "idempotency_key": request.idempotency_key,
        "tenant_workspace_id": request.tenant_workspace_id,
        "snapshot_id": request.snapshot_id,
        "knowledge_cutoff": request.knowledge_cutoff,
        "model_contract_version": request.model_contract_version,
        "output_profile": request.output_profile,
        "result_artifact_id": "artifact-1",
        "result_sha256": "ab" * 32,
        "result_schema_version": "tepp-result-v1",
        "completed_at": "2026-01-13T00:00:00Z",
        "summary": {
            "analysis_family": "temporal_topic_measurement",
            "evidence_count": 1,
            "statistic_count": 1,
            "validation_status": "validated",
        },
        "failure_code": None,
    }
    status = {
        "contract_version": 1,
        "run_id": "remote-run-1",
        "run_state": "succeeded",
        "idempotency_key": request.idempotency_key,
        "terminal_result": terminal,
    }
    outcome = analysis_run_start._execute_delivery_plan(
        analysis_run_start._DeliveryPlan(
            "analysis_run_tepp",
            datetime(2026, 1, 12, tzinfo=timezone.utc),
            {
                "idempotency_key": request.idempotency_key,
                "snapshot_sha256": request.snapshot_id,
                "knowledge_cutoff": datetime(2026, 1, 12, 12, tzinfo=timezone.utc),
                "corporate_entity_id": request.tenant_workspace_id,
                "remote_run_id": "remote-run-1",
            },
        ),
        TeppClient(status_transport=lambda _run_id: status),
        None,
    )

    assert outcome.status_code == "analysis_status_succeeded"
    assert outcome.persist_terminal_result
    assert outcome.envelope == status


def test_tepp_terminal_result_replay_must_match() -> None:
    class _Connection:
        def __init__(self) -> None:
            self.existing = None
            self.inserted: tuple[object, ...] | None = None

        async def fetchrow(self, _query: str, *_args: object):
            return self.existing

        async def execute(self, _query: str, *args: object):
            self.inserted = args

    envelope = {
        "contract_version": 1,
        "run_id": "remote-run-1",
        "run_state": "succeeded",
        "terminal_result": {"result_artifact_id": "artifact-1"},
    }
    conn = _Connection()
    assert asyncio.run(
        _persist_tepp_terminal_result(
            conn,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            envelope=envelope,
        )
    )
    assert conn.inserted is not None
    conn.existing = {
        "remote_run_id": conn.inserted[1],
        "result_sha256": conn.inserted[3],
    }
    assert asyncio.run(
        _persist_tepp_terminal_result(
            conn,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            envelope=envelope,
        )
    )
    conn.existing["result_sha256"] = "0" * 64
    assert not asyncio.run(
        _persist_tepp_terminal_result(
            conn,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            envelope=envelope,
        )
    )


def test_tepp_acceptance_receipt_replay_must_match() -> None:
    """A provider replay cannot replace the remote identity or evidence digest."""

    class _Connection:
        def __init__(self) -> None:
            self.existing = None
            self.inserted: tuple[object, ...] | None = None

        async def fetchrow(self, _query: str, *_args: object):
            return self.existing

        async def execute(self, _query: str, *args: object):
            self.inserted = args

    request = _tepp_request()
    receipt = {
        "contract_version": 1,
        "run_id": "remote-run-1",
        "run_state": "accepted",
        "idempotency_key": request.idempotency_key,
    }
    conn = _Connection()
    assert asyncio.run(
        _persist_tepp_receipt(
            conn,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            request=request,
            envelope=receipt,
        )
    )
    assert conn.inserted is not None
    conn.existing = {
        "remote_run_id": conn.inserted[1],
        "request_sha256": conn.inserted[2],
        "receipt_sha256": conn.inserted[3],
    }
    assert asyncio.run(
        _persist_tepp_receipt(
            conn,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            request=request,
            envelope=receipt,
        )
    )
    conn.existing["remote_run_id"] = "changed-run"
    assert not asyncio.run(
        _persist_tepp_receipt(
            conn,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            request=request,
            envelope=receipt,
        )
    )


def test_tepp_run_request_is_the_published_wire_shape() -> None:
    """Start builds TEPP's seven-field request from the frozen run."""
    request = _tepp_request()
    payload = request.to_json()
    assert payload["contract_version"] == 1
    assert payload["idempotency_key"] == "buyer-tepp-2026-w07"
    assert payload["snapshot_id"] == "ab" * 32
    assert payload["knowledge_cutoff"] == "2026-01-12T12:00:00Z"
    assert payload["model_contract_version"] == "tepp-lineage-criterion-v1"
    assert payload["output_profile"] == "lineage_pair_criterion_anchor"
    assert "theta" not in str(payload).casefold()


def test_tepp_run_request_preserves_exact_cutoff_precision() -> None:
    """The echoed TEPP anchor must match a microsecond database cutoff exactly."""
    request = tepp_run_request(
        idempotency_key="exact-cutoff",
        snapshot_sha256="ab" * 32,
        knowledge_cutoff=datetime(2026, 1, 12, 12, 0, 0, 123456, tzinfo=timezone.utc),
        corporate_entity_id="11111111-1111-1111-1111-111111111111",
    )
    assert request.knowledge_cutoff == "2026-01-12T12:00:00.123456Z"


def test_tepp_submit_outcome_drops_a_missing_transport() -> None:
    """A missing TEPP transport is Failed, never a fabricated score."""
    status, failure = tepp_submit_outcome(TeppClient(), _tepp_request())
    assert status == "analysis_status_failed"
    assert failure == "tepp_not_available"


def test_tepp_submit_outcome_does_not_persist_an_empty_envelope() -> None:
    """An accepted envelope is not a persistable measurement."""

    class _Accepting(TeppClient):
        def __init__(self) -> None:
            super().__init__(transport=lambda _payload: {"status": "accepted"})

    status, failure = tepp_submit_outcome(_Accepting(), _tepp_request())
    assert status == "analysis_status_failed"
    assert failure == "tepp_result_not_persisted"


def test_tepp_anchor_projection_accepts_only_the_published_result_contract() -> None:
    """The consumer persists TEPP's exact v1 artifact, not an ad hoc nested flag."""

    class _Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

    class _Connection:
        def __init__(self) -> None:
            self.queries: list[tuple[str, tuple[object, ...]]] = []

        def transaction(self):
            return _Transaction()

        async def execute(self, query: str, *args: object):
            self.queries.append((query, args))

        async def fetchrow(self, _query: str, *_args: object):
            return None

    cutoff = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)
    conn = _Connection()
    envelope = {
        "status": "succeeded",
        "run_id": "tepp-run-1",
        "result_schema_version": "tepp.lineage_criterion_anchor.v1",
        "result": {
            "contract_version": 1,
            "anchor_kind_code": "lineage_pair_criterion",
            "estimation_run_id": "018f47e7-7b5b-7cc0-98c6-15fdf9e3d9b1",
            "source_snapshot_sha256": "ab" * 32,
            "knowledge_cutoff": cutoff.isoformat(),
            "criterion_validity_status": "accepted",
            "validated_pair_count": 600,
        },
    }
    assert asyncio.run(
        _persist_tepp_result(
            conn,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            envelope=envelope,
            expected_snapshot_sha256="ab" * 32,
            expected_knowledge_cutoff=cutoff,
        )
    )
    assert sum("lineage_weight_tepp_anchor" in query for query, _ in conn.queries) == 1
    promotion = next(
        (args for query, args in conn.queries if "update lineage_channel_weight" in query),
        None,
    )
    assert promotion == (
        "018f47e7-7b5b-7cc0-98c6-15fdf9e3d9b1",
        "ab" * 32,
        cutoff,
        600,
    )

    conn = _Connection()
    envelope["result_schema_version"] = "consumer.private.v1"
    assert asyncio.run(
        _persist_tepp_result(
            conn,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            envelope=envelope,
            expected_snapshot_sha256="ab" * 32,
            expected_knowledge_cutoff=cutoff,
        )
    )
    assert not any("lineage_weight_tepp_anchor" in query for query, _ in conn.queries)
    assert not any("update lineage_channel_weight" in query for query, _ in conn.queries)

    conn = _Connection()
    envelope["result_schema_version"] = "tepp.lineage_criterion_anchor.v1"
    envelope["result"]["estimation_run_id"] = "018f47e77b5b7cc098c615fdf9e3d9b1"
    assert asyncio.run(
        _persist_tepp_result(
            conn,
            analysis_run_id="11111111-1111-1111-1111-111111111111",
            envelope=envelope,
            expected_snapshot_sha256="ab" * 32,
            expected_knowledge_cutoff=cutoff,
        )
    )
    assert not any("lineage_weight_tepp_anchor" in query for query, _ in conn.queries)


def _topic_lineage_request() -> AnalysisRunRequest:
    return topic_lineage_run_request(
        idempotency_key="run-topic-lineage-2026-w07",
        snapshot_sha256="ab" * 32,
        knowledge_cutoff=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
        corporate_entity_id="11111111-1111-1111-1111-111111111111",
    )


def test_topic_lineage_run_request_is_the_published_wire_shape() -> None:
    """Start builds TEPP's seven-field request for topic lineage (ADR 0132)."""
    request = _topic_lineage_request()
    payload = request.to_json()
    assert payload["contract_version"] == 1
    assert payload["idempotency_key"] == "run-topic-lineage-2026-w07"
    assert payload["snapshot_id"] == "ab" * 32
    assert payload["knowledge_cutoff"] == "2026-01-12T12:00:00Z"
    assert payload["model_contract_version"] == "tepp-topic-lineage-v1"
    assert payload["output_profile"] == "topic_identity_lineage"
    assert "theta" not in str(payload).casefold()
    assert "chronos" not in str(payload).casefold()


def test_topic_lineage_submit_outcome_drops_a_missing_transport() -> None:
    """A missing TEPP transport is Failed, never a fabricated topic model."""
    status, failure, envelope = topic_lineage_submit_outcome(
        TeppClient(), _topic_lineage_request()
    )
    assert status == "analysis_status_failed"
    assert failure == "tepp_not_available"
    assert envelope is None


def test_topic_lineage_submit_outcome_does_not_persist_an_empty_envelope() -> None:
    """An accepted envelope is not yet a persistable topic-lineage result."""

    class _Accepting(TeppClient):
        def __init__(self) -> None:
            super().__init__(transport=lambda _payload: {"status": "accepted"})

    status, failure, envelope = topic_lineage_submit_outcome(
        _Accepting(), _topic_lineage_request()
    )
    assert status == "analysis_status_failed"
    assert envelope is None
    assert failure == "tepp_result_not_persisted"


def test_topic_lineage_submit_outcome_rejects_a_contentless_completed_envelope() -> None:
    """A 'completed' envelope missing the topic-identity/CHRONOS contract is Failed.

    A syntactically valid envelope whose ``result`` lacks TRSL-TM topic
    identity and CHRONOS/TDT status (e.g. it accidentally serves the
    calibrated-measurement shape) must not be treated as a topic-lineage
    success, per ADR 0132 Decision item 3.
    """

    class _EmptyResult(TeppClient):
        def __init__(self) -> None:
            super().__init__(
                transport=lambda _payload: {
                    "status": "completed",
                    "analysis_run_id": "r-1",
                    "result": {},
                }
            )

    status, failure, envelope = topic_lineage_submit_outcome(_EmptyResult(), _topic_lineage_request())
    assert status == "analysis_status_failed"
    assert failure == "tepp_topic_contract_unavailable"
    assert envelope is None


def test_topic_lineage_submit_outcome_accepts_the_versioned_topic_envelope() -> None:
    """A completed envelope carrying the versioned topic-identity/CHRONOS contract succeeds."""

    class _Completed(TeppClient):
        def __init__(self) -> None:
            super().__init__(
                transport=lambda _payload: {
                    "status": "completed",
                    "analysis_run_id": "r-1",
                    "result": {
                        "envelope_version": 1,
                        "topic_identity": [{"topic_id": "t-1"}],
                        "chronos_status": "evidence",
                    },
                }
            )

    status, failure, envelope = topic_lineage_submit_outcome(_Completed(), _topic_lineage_request())
    assert status == "analysis_status_succeeded"
    assert failure == ""
    assert envelope is not None


@pytest.mark.parametrize("invalid_version", [True, False, 0, 2, "1"])
def test_topic_lineage_submit_outcome_rejects_unsupported_envelope_version(
    invalid_version: object,
) -> None:
    """Only integer envelope version 1 is the published contract."""

    class _WrongVersion(TeppClient):
        def __init__(self) -> None:
            super().__init__(
                transport=lambda _payload: {
                    "status": "completed",
                    "analysis_run_id": "r-1",
                    "result": {
                        "envelope_version": invalid_version,
                        "topic_identity": [{"topic_id": "t-1"}],
                        "chronos_status": "evidence",
                    },
                }
            )

    status, failure, envelope = topic_lineage_submit_outcome(
        _WrongVersion(), _topic_lineage_request()
    )
    assert (status, failure, envelope) == (
        "analysis_status_failed",
        "tepp_topic_contract_unavailable",
        None,
    )


def test_configured_tepp_client_stays_unavailable_without_http() -> None:
    """Empty or non-http URLs keep the default dropped channel."""
    assert isinstance(configured_tepp_client(""), TeppClient)
    client = configured_tepp_client("file:///tmp/tepp.json")
    with pytest.raises(TeppNotAvailable):
        client.submit_analysis_run(_tepp_request())


def test_configured_tepp_client_does_not_expose_provider_error(monkeypatch) -> None:
    """TEPP transport failures remain a stable unavailable product error."""
    def fail(*_args, **_kwargs):
        raise HttpClientError("raw-tepp-provider-secret")

    monkeypatch.setattr("backend.app.analysis_run_start.post_json", fail)
    client = configured_tepp_client("https://tepp.example.test/run")
    with pytest.raises(TeppNotAvailable) as exc_info:
        client.submit_analysis_run(_tepp_request())
    assert str(exc_info.value) == "TEPP transport unavailable"
    assert "raw-tepp-provider-secret" not in str(exc_info.value)


def test_hidden_run_start_is_not_found() -> None:
    """Operators get a 404 next action, not an internal exception name."""
    error = AnalysisRunStartError(404, "This analysis run is not visible.")
    assert error.status_code == 404
    assert "not visible" in error.detail


def test_running_restart_conflicts_and_succeeded_replay_is_documented() -> None:
    """Running without pending outbox is 409. Succeeded replay is a no-op."""
    conflict = start_write_conflict_error()
    assert conflict.status_code == 409
    assert "Refresh to see the stored tree" in conflict.detail
    running = AnalysisRunStartError(
        409,
        "Open this run. Start is only for a Pending lineage reconstruction.",
    )
    assert running.status_code == 409
    assert "Pending" in running.detail
