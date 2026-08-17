"""Published TEPP accepted evidence is not a completed measurement."""

from __future__ import annotations

from lineageweave.tepp_result import (
    accepted_tepp_seed_envelope,
    parse_persistable_tepp_result,
    parse_tepp_accepted_evidence,
    persistable_tepp_seed_envelope,
    tepp_accepted_evidence_sha256,
)


def test_published_accepted_envelope_is_transport_evidence() -> None:
    """TEPP's AnalysisRunAccepted fields are storeable transport evidence."""
    envelope = accepted_tepp_seed_envelope(idempotency_key="demo-tepp-seed-2026-w02")
    parsed = parse_tepp_accepted_evidence(
        envelope,
        expected_idempotency_key="demo-tepp-seed-2026-w02",
    )
    assert parsed is not None
    assert parsed.contract_version == 1
    assert parsed.run_state == "accepted"
    assert parsed.accepted_run_id == "demo-tepp-accepted-opaque"
    assert parsed.evidence_kind() == "aggregate transport evidence"
    expected = tepp_accepted_evidence_sha256(
        contract_version=1,
        accepted_run_id="demo-tepp-accepted-opaque",
        run_state="accepted",
        idempotency_key="demo-tepp-seed-2026-w02",
    )
    assert parsed.evidence_sha256() == expected
    assert len(expected) == 64
    assert "theta" not in expected


def test_accepted_ack_without_published_fields_is_not_evidence() -> None:
    """A bare status=accepted object is not TEPP's published envelope."""
    assert parse_tepp_accepted_evidence({"status": "accepted"}) is None
    assert parse_tepp_accepted_evidence(
        {"contract_version": 1, "status": "accepted"}
    ) is None


def test_local_completed_envelope_is_not_accepted_evidence() -> None:
    """The v2.12.0 LineageWeave-local shape is not a TEPP completed result."""
    local = persistable_tepp_seed_envelope()
    assert parse_tepp_accepted_evidence(local) is None
    assert parse_persistable_tepp_result(local) is None


def test_theta_and_unknown_fields_are_not_accepted_evidence() -> None:
    """Unknown fields and psychometric keys fail closed."""
    base = accepted_tepp_seed_envelope(idempotency_key="k")
    assert parse_tepp_accepted_evidence({**base, "theta": 0.42}) is None
    assert parse_tepp_accepted_evidence({**base, "affiliation_count": 2}) is None
    assert parse_tepp_accepted_evidence({**base, "extra": True}) is None
    assert parse_tepp_accepted_evidence({**base, "run_state": "completed"}) is None
    assert parse_tepp_accepted_evidence({**base, "contract_version": 2}) is None
    assert parse_tepp_accepted_evidence(
        base,
        expected_idempotency_key="other-key",
    ) is None
    assert parse_tepp_accepted_evidence("accepted") is None


def test_persistable_parser_never_succeeds() -> None:
    """No unpublished completed envelope becomes a persistable measurement."""
    assert parse_persistable_tepp_result(persistable_tepp_seed_envelope()) is None
    assert parse_persistable_tepp_result(
        accepted_tepp_seed_envelope(idempotency_key="k")
    ) is None
    assert parse_persistable_tepp_result({"theta": 1}) is None
