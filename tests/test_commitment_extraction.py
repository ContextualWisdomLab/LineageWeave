"""Tests for lineageweave.commitment_extraction.

parse_commitment_response's tests need no live provider. The real-provider
test reuses fixtures.ambiguous_commitment_post -- it states its deadline
relative to the post ("by next Friday"), so it can only be resolved
correctly if the client actually uses the reference date it's given, and
it contains a second, date-adjacent sentence that is NOT a commitment (a
past event), so a keyword match on "date-like text" would get it wrong.
"""

from __future__ import annotations

import os

import pytest

from lineageweave.commitment_extraction import (
    ContextualOrchestratorCommitmentExtractionClient,
    NullCommitmentExtractionClient,
    parse_commitment_response,
)
from lineageweave.fixtures import ambiguous_commitment_post


def test_null_commitment_client_is_unavailable_not_a_negative_result() -> None:
    client = NullCommitmentExtractionClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.extract("any title", "any body", "2026-01-01")


def test_parses_a_well_formed_commitment() -> None:
    content = (
        '{"has_commitment": true, '
        '"commitment_summary": "Send Riverbend the revised delivery schedule.", '
        '"due_date": "2026-01-09"}'
    )
    commitment = parse_commitment_response(content)
    assert commitment is not None
    assert commitment.has_commitment is True
    assert commitment.commitment_summary == "Send Riverbend the revised delivery schedule."
    assert commitment.due_date == "2026-01-09"


def test_no_commitment_is_a_real_result_not_none() -> None:
    content = '{"has_commitment": false, "commitment_summary": null, "due_date": null}'
    commitment = parse_commitment_response(content)
    assert commitment is not None
    assert commitment.has_commitment is False
    assert commitment.commitment_summary is None
    assert commitment.due_date is None


def test_missing_has_commitment_field_returns_none() -> None:
    content = '{"commitment_summary": "x", "due_date": null}'
    assert parse_commitment_response(content) is None


def test_true_without_summary_returns_none() -> None:
    content = '{"has_commitment": true, "commitment_summary": null, "due_date": null}'
    assert parse_commitment_response(content) is None


def test_malformed_due_date_is_dropped_not_fatal() -> None:
    """A commitment with no resolvable date is still a real commitment --
    the due_date just stays None rather than failing the whole parse."""
    content = (
        '{"has_commitment": true, "commitment_summary": "Follow up eventually.", '
        '"due_date": "next Friday"}'
    )
    commitment = parse_commitment_response(content)
    assert commitment is not None
    assert commitment.has_commitment is True
    assert commitment.due_date is None


def test_invalid_json_returns_none() -> None:
    assert parse_commitment_response("not json") is None


def test_code_fence_is_stripped() -> None:
    content = '```json\n{"has_commitment": false, "commitment_summary": null, "due_date": null}\n```'
    commitment = parse_commitment_response(content)
    assert commitment is not None
    assert commitment.has_commitment is False


_ORCHESTRATOR_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL")
_ORCHESTRATOR_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY")


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_real_llm_resolves_a_relative_deadline_against_the_reference_date() -> None:
    """A real LLM call must actually use the reference date it's given,
    not just echo back "next Friday" or hallucinate an arbitrary one."""
    client = ContextualOrchestratorCommitmentExtractionClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY
    )
    title, body = ambiguous_commitment_post()
    # A Monday, so "next Friday" is unambiguous.
    commitment = client.extract(title, body, "2026-01-05")
    assert commitment.has_commitment is True
    assert commitment.due_date is not None
    assert commitment.due_date.startswith("2026-01")
    assert commitment.commitment_summary
