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
    NullOrganizationNameResolutionClient,
    OrganizationNameResolution,
    parse_resolution_response,
    resolve_and_verify_organization_name,
)
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
    assert parse_resolution_response("한국수력원자력\n") == "한국수력원자력"


def test_parse_resolution_response_rejects_unknown() -> None:
    assert parse_resolution_response("UNKNOWN") is None
    assert parse_resolution_response("unknown\n") is None


def test_parse_resolution_response_rejects_empty() -> None:
    assert parse_resolution_response("") is None
    assert parse_resolution_response("   ") is None


def test_no_resolution_when_client_unavailable() -> None:
    result = resolve_and_verify_organization_name(
        "한수원", "context", NullOrganizationNameResolutionClient(), NullRelationVerificationClient()
    )
    assert result is None


def test_no_resolution_when_model_proposes_nothing() -> None:
    result = resolve_and_verify_organization_name(
        "한수원", "context", _FakeResolutionClient(None), NullRelationVerificationClient()
    )
    assert result is None


def test_no_resolution_when_model_echoes_the_same_name() -> None:
    """A "resolution" that just returns the raw name back is not a real
    resolution -- must not be persisted as one."""
    result = resolve_and_verify_organization_name(
        "한수원", "context", _FakeResolutionClient("한수원"), NullRelationVerificationClient()
    )
    assert result is None


def test_corroborated_resolution_carries_evidence() -> None:
    verification = _FakeVerificationClient(
        RelationVerificationResult(status_code=STATUS_CORROBORATED, evidence_url="https://example.org/khnp")
    )
    resolution_client = _FakeResolutionClient("한국수력원자력")
    result = resolve_and_verify_organization_name("한수원", "설계팀이 한수원과 회의했다", resolution_client, verification)
    assert result == OrganizationNameResolution(
        raw_organization_name="한수원",
        resolved_organization_name="한국수력원자력",
        verification_status_code=STATUS_CORROBORATED,
        verification_evidence_url="https://example.org/khnp",
    )
    # The full name and the raw abbreviation are searched together --
    # the specific pairing is what needs corroborating, not just that
    # the full name exists as some organization.
    assert verification.calls == [("한국수력원자력", "한수원")]


def test_uncorroborated_resolution_still_returned_with_evidence_none() -> None:
    verification = _FakeVerificationClient(
        RelationVerificationResult(status_code=STATUS_UNCORROBORATED, evidence_url=None)
    )
    result = resolve_and_verify_organization_name(
        "한수원", "context", _FakeResolutionClient("Invented Co"), verification
    )
    assert result is not None
    assert result.verification_status_code == STATUS_UNCORROBORATED
    assert result.verification_evidence_url is None


def test_verification_unavailable_yields_pending_not_a_fabricated_result() -> None:
    result = resolve_and_verify_organization_name(
        "한수원", "context", _FakeResolutionClient("한국수력원자력"), NullRelationVerificationClient()
    )
    assert result is not None
    assert result.verification_status_code == STATUS_PENDING
    assert result.verification_evidence_url is None
