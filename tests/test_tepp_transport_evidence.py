"""Authorized TEPP transport-evidence projection stays fail-closed."""

from __future__ import annotations

from pathlib import Path

from backend.app.analysis_run_ingestion import project_tepp_transport_evidence
from lineageweave.tepp_result import (
    accepted_tepp_seed_envelope,
    parse_tepp_accepted_evidence,
    tepp_accepted_evidence_sha256,
)


def test_project_tepp_transport_evidence_recomputes_the_exact_digest() -> None:
    """The API digest must match an independent SHA-256 recomputation."""
    parsed = parse_tepp_accepted_evidence(
        accepted_tepp_seed_envelope(idempotency_key="buyer-key"),
        expected_idempotency_key="buyer-key",
    )
    assert parsed is not None
    expected = tepp_accepted_evidence_sha256(
        contract_version=1,
        accepted_run_id="demo-tepp-accepted-opaque",
        run_state="accepted",
        idempotency_key="buyer-key",
    )
    row = {
        "contract_version": parsed.contract_version,
        "accepted_run_id": parsed.accepted_run_id,
        "run_state": parsed.run_state,
        "idempotency_key": parsed.idempotency_key,
        "evidence_sha256": expected,
        "received_at": "2026-01-12T12:45:00Z",
        "recorded_at": "2026-01-12T12:45:00Z",
    }
    projected = project_tepp_transport_evidence(row)
    assert projected is not None
    assert projected["tepp_evidence_sha256"] == expected
    assert projected["tepp_evidence_kind"] == "aggregate transport evidence"
    assert projected["tepp_completed_artifact_available"] is False
    assert "affiliation_count" not in projected
    assert "theta" not in str(projected).casefold()


def test_project_tepp_transport_evidence_fails_closed_on_digest_mismatch() -> None:
    """A substituted digest is omitted rather than shown as evidence."""
    row = {
        "contract_version": 1,
        "accepted_run_id": "demo-tepp-accepted-opaque",
        "run_state": "accepted",
        "idempotency_key": "buyer-key",
        "evidence_sha256": "0" * 64,
        "received_at": "2026-01-12T12:45:00Z",
        "recorded_at": "2026-01-12T12:45:00Z",
    }
    assert project_tepp_transport_evidence(row) is None


def test_tepp_accepted_query_binds_authorized_run_ids_only() -> None:
    """Hidden runs never enter the evidence query parameter list."""
    source = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "app"
        / "analysis_run_ingestion.py"
    ).read_text(encoding="utf-8")
    assert "from analysis_run_tepp_accepted" in source
    assert "where analysis_run_id = any($1::uuid[])" in source
    assert "_tepp_accepted_by_run(conn, run_ids)" in source
