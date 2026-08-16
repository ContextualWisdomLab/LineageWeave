"""Seeded TEPP analysis runs go through tepp_client, never a local model."""

from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable
from scripts.seed_demo_data import (
    _ensure_demo_source_counts,
    demo_source_snapshot_sha256,
    tepp_seed_outcome,
    tepp_seed_request,
)


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


def test_ensure_demo_source_counts_skips_insert_when_counts_exist() -> None:
    cursor = _CountCursor(existing_counts=True)
    _ensure_demo_source_counts(cursor, "snapshot-1")
    assert any("from analysis_source_count" in sql for sql in cursor.statements)
    assert not any(sql.lstrip().startswith("insert into analysis_source_count") for sql in cursor.statements)


def test_ensure_demo_source_counts_inserts_when_the_snapshot_is_empty() -> None:
    cursor = _CountCursor(existing_counts=False)
    _ensure_demo_source_counts(cursor, "snapshot-1")
    assert any(sql.lstrip().startswith("insert into analysis_source_count") for sql in cursor.statements)
