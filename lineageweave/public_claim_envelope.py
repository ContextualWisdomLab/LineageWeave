"""Persisted admission envelopes for public Global Ask verification.

The envelope decides which already-cited public assertion may leave the
workspace boundary.  Retrieval and adjudication remain owned by the existing
claim-verification clients; this module never derives a claim from question
tokens or source text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .claim_verification import PublicClaimCandidate

ADMITTED_PUBLIC_CLAIM_KINDS = frozenset(
    {
        "claim_organization_presence",
        "claim_public_event",
        "claim_public_relationship",
    }
)


@dataclass(frozen=True)
class PersistedPublicClaimEnvelope:
    """One governed claim and its exact authorized source-post provenance."""

    public_claim_envelope_id: str
    source_post_id: str
    claim_kind_code: str
    claim_text: str

    def verification_candidate(self) -> PublicClaimCandidate:
        """Project the persisted envelope into the existing verifier contract."""

        return PublicClaimCandidate(
            claim_text=self.claim_text,
            claim_kind=self.claim_kind_code,
            source_post_ids=(self.source_post_id,),
        )


def envelope_from_authorized_row(row: Any) -> PersistedPublicClaimEnvelope | None:
    """Validate a database row already filtered by ABAC and PROV-O binding."""

    kind = str(row["claim_kind_code"] or "").strip()
    envelope_id = str(row["public_claim_envelope_id"] or "").strip()
    source_post_id = str(row["source_post_id"] or "").strip()
    claim_text = str(row["claim_text"] or "").strip()
    if (
        kind not in ADMITTED_PUBLIC_CLAIM_KINDS
        or not envelope_id
        or not source_post_id
        or not claim_text
        or len(claim_text) > 800
    ):
        return None
    return PersistedPublicClaimEnvelope(
        public_claim_envelope_id=envelope_id,
        source_post_id=source_post_id,
        claim_kind_code=kind,
        claim_text=claim_text,
    )
