"""Persisted public-claim admission boundary regressions."""

from lineageweave.claim_verification import PublicClaimCandidate
from lineageweave.public_claim_envelope import envelope_from_authorized_row


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "public_claim_envelope_id": "00000000-0000-0000-0000-000000000101",
        "source_post_id": "00000000-0000-0000-0000-000000000201",
        "claim_kind_code": "claim_public_event",
        "claim_text": "Synthetic project reached its published milestone.",
    }
    row.update(overrides)
    return row


def test_persisted_envelope_projects_exact_claim_and_provenance() -> None:
    """Admission preserves the stored claim and its one evidence post."""

    envelope = envelope_from_authorized_row(_row())

    assert envelope is not None
    assert envelope.verification_candidate() == PublicClaimCandidate(
        claim_text="Synthetic project reached its published milestone.",
        claim_kind="claim_public_event",
        source_post_ids=("00000000-0000-0000-0000-000000000201",),
    )


def test_persisted_envelope_rejects_unregistered_or_malformed_claims() -> None:
    """Person-like and malformed rows cannot be repaired into egress claims."""

    assert envelope_from_authorized_row(_row(claim_kind_code="person")) is None
    assert envelope_from_authorized_row(_row(claim_text="")) is None
    assert envelope_from_authorized_row(_row(claim_text="x" * 801)) is None
