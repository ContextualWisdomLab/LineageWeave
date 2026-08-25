"""Tests for lineageweave.organization_name_resolution (ADR 0008).

Deterministic fake clients, same style as tests/test_post_summary.py
and tests/test_keyman_extraction.py's pure-parse-function tests -- the
underlying HTTP mechanics (post_json) and SearxngRelationVerificationClient's
own HTTP behavior are already covered in test_http_client.py and
test_relation_verification.py respectively; these tests are for this
module's own resolve-then-verify orchestration logic.
"""

from __future__ import annotations

from lineageweave.organization_name_resolution import (
    ContextualOrchestratorOrganizationNameResolutionClient,
    NullOrganizationNameResolutionClient,
    OrganizationNameResolution,
    parse_resolution_response,
    resolve_and_verify_organization_name,
)


def test_live_resolution_client_uses_adaptive_orchestrator_mode(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_post_json(url, body, *, headers, timeout):
        seen.update(url=url, body=body, headers=headers, timeout=timeout)
        return {"choices": [{"message": {"content": "Aurora Grid Power"}}]}

    monkeypatch.setattr("lineageweave.organization_name_resolution.post_json", fake_post_json)
    client = ContextualOrchestratorOrganizationNameResolutionClient(
        "http://orchestrator", "secret", reasoning_effort="high"
    )

    assert client.resolve("AGP", "AGP joined the synthetic meeting") == "Aurora Grid Power"
    assert seen["url"] == "http://orchestrator/v1/chat/completions"
    assert seen["body"]["mode"] == "auto"
    assert seen["body"]["reasoning_effort"] == "high"
    assert seen["timeout"] == 600.0
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    STATUS_PENDING,
    STATUS_UNCORROBORATED,
    NullRelationVerificationClient,
    RelationVerificationResult,
)


class _FakeResolutionClient:
    available = True

    def __init__(self, candidate: str | None) -> None:
        self._candidate = candidate
        self.calls: list[tuple[str, str]] = []

    def resolve(self, raw_name: str, context_text: str) -> str | None:
        self.calls.append((raw_name, context_text))
        return self._candidate


class _FakeVerificationClient:
    available = True

    def __init__(self, result: RelationVerificationResult) -> None:
        self._result = result
        self.calls: list[tuple[str, str]] = []

    def verify(self, organization_name: str, relationship_label: str) -> RelationVerificationResult:
        self.calls.append((organization_name, relationship_label))
        return self._result


def test_parse_resolution_response_extracts_the_first_line() -> None:
    assert parse_resolution_response("Aurora Grid Power\n") == "Aurora Grid Power"


def test_parse_resolution_response_rejects_unknown() -> None:
    assert parse_resolution_response("UNKNOWN") is None
    assert parse_resolution_response("unknown\n") is None


def test_parse_resolution_response_rejects_empty() -> None:
    assert parse_resolution_response("") is None
    assert parse_resolution_response("   ") is None


def test_no_resolution_when_client_unavailable() -> None:
    result = resolve_and_verify_organization_name(
        "AGP", "context", NullOrganizationNameResolutionClient(), NullRelationVerificationClient()
    )
    assert result is None


def test_no_resolution_when_model_proposes_nothing() -> None:
    result = resolve_and_verify_organization_name(
        "AGP", "context", _FakeResolutionClient(None), NullRelationVerificationClient()
    )
    assert result is None


def test_no_resolution_when_model_echoes_the_same_name() -> None:
    """A "resolution" that just returns the raw name back is not a real
    resolution -- must not be persisted as one."""
    result = resolve_and_verify_organization_name(
        "AGP", "context", _FakeResolutionClient("AGP"), NullRelationVerificationClient()
    )
    assert result is None


def test_corroborated_resolution_carries_evidence() -> None:
    verification = _FakeVerificationClient(
        RelationVerificationResult(status_code=STATUS_CORROBORATED, evidence_url="https://example.org/agp")
    )
    resolution_client = _FakeResolutionClient("Aurora Grid Power")
    result = resolve_and_verify_organization_name("AGP", "설계팀이 AGP와 회의했다", resolution_client, verification)
    assert result == OrganizationNameResolution(
        raw_organization_name="AGP",
        resolved_organization_name="Aurora Grid Power",
        verification_status_code=STATUS_CORROBORATED,
        verification_evidence_url="https://example.org/agp",
    )
    # The full name and the raw abbreviation are searched together --
    # the specific pairing is what needs corroborating, not just that
    # the full name exists as some organization.
    assert verification.calls == [("Aurora Grid Power", "AGP")]


def test_uncorroborated_resolution_still_returned_with_evidence_none() -> None:
    verification = _FakeVerificationClient(
        RelationVerificationResult(status_code=STATUS_UNCORROBORATED, evidence_url=None)
    )
    result = resolve_and_verify_organization_name(
        "AGP", "context", _FakeResolutionClient("Invented Co"), verification
    )
    assert result is not None
    assert result.verification_status_code == STATUS_UNCORROBORATED
    assert result.verification_evidence_url is None


def test_verification_unavailable_yields_pending_not_a_fabricated_result() -> None:
    result = resolve_and_verify_organization_name(
        "AGP", "context", _FakeResolutionClient("Aurora Grid Power"), NullRelationVerificationClient()
    )
    assert result is not None
    assert result.verification_status_code == STATUS_PENDING
    assert result.verification_evidence_url is None
