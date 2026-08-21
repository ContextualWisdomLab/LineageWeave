from __future__ import annotations

from typing import Any

import pytest

from backend.app import main
from lineageweave.claim_verification import (
    CLAIM_NOT_ENOUGH_INFORMATION,
    CLAIM_SUPPORTED,
    VERIFICATION_COMPLETED,
    VERIFICATION_NO_PUBLIC_CLAIMS,
    VERIFICATION_SKIPPED,
    VERIFICATION_UNAVAILABLE,
    ClaimVerificationResult,
    GlobalAskSourceDocument,
)


def _source(*facts: str) -> GlobalAskSourceDocument:
    return GlobalAskSourceDocument(
        post_id="11111111-1111-1111-1111-111111111111",
        post_title="Public Apollo evidence",
        post_body="Apollo is described in the authorized public source.",
        external_claim_facts=tuple(facts),
    )


def test_global_ask_external_verification_is_backward_compatible_opt_in() -> None:
    request = main.GlobalAskRequest(question="Apollo")
    assert request.verify_external is False
    assert main.GlobalAskRequest(question="Apollo", verify_external=True).verify_external is True


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (VERIFICATION_SKIPPED, "Enable public verification to check eligible public claims."),
        (
            VERIFICATION_UNAVAILABLE,
            "Configure public search and contextual-orchestrator, then retry.",
        ),
        (
            VERIFICATION_NO_PUBLIC_CLAIMS,
            "Inspect the internal cited posts; no public claim was eligible.",
        ),
        (
            VERIFICATION_COMPLETED,
            "Inspect public evidence separately before any governed graph review.",
        ),
        (
            CLAIM_NOT_ENOUGH_INFORMATION,
            "Collect stronger authoritative evidence before accepting the claim.",
        ),
        ("unknown", "Inspect the authorized cited posts and their evidence."),
    ],
)
def test_verification_next_actions_are_stable_translation_keys(
    status_code: str,
    expected: str,
) -> None:
    """Every verification state returns one frontend translation key."""
    assert main._verification_next_action(status_code) == expected


def test_no_source_next_action_takes_priority_over_verification_state() -> None:
    """An empty authorized source set keeps its specific buyer guidance."""
    assert main._verification_next_action(
        VERIFICATION_SKIPPED,
        has_authorized_sources=False,
    ) == "No authorized source posts are available for this question."


@pytest.mark.anyio
async def test_verify_public_claims_skips_without_explicit_opt_in() -> None:
    status_code, claims = await main._verify_public_claims(
        "Apollo",
        [_source("project: Apollo | evidence: public launch")],
        ["11111111-1111-1111-1111-111111111111"],
        verify_external=False,
    )
    assert status_code == VERIFICATION_SKIPPED
    assert claims == ()


@pytest.mark.anyio
async def test_verify_public_claims_uses_only_cited_egress_capable_sources() -> None:
    source = _source("project: Apollo | evidence: public launch")
    status_code, claims = await main._verify_public_claims(
        "Apollo",
        [source],
        [],
        verify_external=True,
    )
    assert status_code == VERIFICATION_NO_PUBLIC_CLAIMS
    assert claims == ()


@pytest.mark.anyio
async def test_verify_public_claims_returns_completed_separate_web_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source("project: Apollo | evidence: public launch")
    verified: list[str] = []

    class _FakeClient:
        available = True

        def verify(self, claim: Any) -> ClaimVerificationResult:
            verified.append(claim.claim_text)
            return ClaimVerificationResult(
                claim_text=claim.claim_text,
                claim_kind=claim.claim_kind,
                status_code=CLAIM_SUPPORTED,
                rationale="The bounded public evidence supports this claim.",
                source_post_ids=claim.source_post_ids,
            )

    monkeypatch.setattr(main, "_claim_verification_client", lambda: _FakeClient(), raising=False)

    status_code, claims = await main._verify_public_claims(
        "Apollo",
        [source],
        [source.post_id],
        verify_external=True,
    )

    assert status_code == VERIFICATION_COMPLETED
    assert len(claims) == 1
    assert claims[0].status_code == CLAIM_SUPPORTED
    assert verified == ["project: Apollo"]


def test_ask_next_action_names_event_lineage_for_verified_organization_labels() -> None:
    evidence = [
        {
            "post_id": "11111111-1111-1111-1111-111111111111",
            "facts": [
                {
                    "kind": "verified_organization_label",
                    "text": "verified organization label: DC → Demo Corp",
                }
            ],
        }
    ]
    assert main._ask_next_action(VERIFICATION_SKIPPED, evidence) == (
        "Corroborated organization labels are current. Open a cited post to read Event Lineage."
    )
    assert main._ask_next_action(VERIFICATION_SKIPPED, []) == (
        "Enable public verification to check eligible public claims."
    )
