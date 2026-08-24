"""Tests for lineageweave.keyman_extraction.

parse_keyman_response's tests need no live provider -- they exercise the
JSON-shape validation directly. The real-provider test is skipped unless
LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL/_API_KEY are set (same env vars
ContextualOrchestratorAdjudicationClient's real-provider test uses), and
runs against fixtures.ambiguous_keyman_post() -- a synthetic post
deliberately written as running prose, not a templated "Alice of Acme"
list, so a correct extraction has to actually read the text rather than
pattern-match an obvious structure.
"""

from __future__ import annotations

import os

import pytest

from lineageweave.fixtures import ambiguous_keyman_post
from lineageweave.keyman_extraction import (
    COUNTERPARTY,
    OUR_SIDE,
    ContextualOrchestratorKeymanExtractionClient,
    NullKeymanExtractionClient,
    parse_keyman_response,
)


def test_null_keyman_client_is_unavailable_not_empty_mentions() -> None:
    client = NullKeymanExtractionClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.extract("any title", "any body")


def test_parses_a_well_formed_json_array() -> None:
    content = (
        '[{"name": "Alex Kim", "side": "our_side", "affiliations": []}, '
        '{"name": "Sam Lee", "side": "counterparty", "affiliations": ["Acme Corp", "Acme Holdings"]}]'
    )
    mentions = parse_keyman_response(content)
    assert len(mentions) == 2
    assert mentions[0].person_name == "Alex Kim"
    assert mentions[0].person_side_code == OUR_SIDE
    assert mentions[0].affiliated_organization_names == ()
    assert mentions[1].person_side_code == COUNTERPARTY
    assert mentions[1].affiliated_organization_names == ("Acme Corp", "Acme Holdings")


def test_job_title_is_captured_when_present() -> None:
    content = '[{"name": "Kim Cheolsu", "side": "counterparty", "affiliations": [], "job_title": "Sales Manager"}]'
    mentions = parse_keyman_response(content)
    assert mentions[0].job_title == "Sales Manager"


def test_job_title_is_none_not_empty_string_when_absent() -> None:
    content = '[{"name": "Kim Cheolsu", "side": "counterparty", "affiliations": []}]'
    mentions = parse_keyman_response(content)
    assert mentions[0].job_title is None


def test_null_job_title_is_none_not_the_string_null() -> None:
    content = '[{"name": "Kim Cheolsu", "side": "counterparty", "affiliations": [], "job_title": null}]'
    mentions = parse_keyman_response(content)
    assert mentions[0].job_title is None


def test_strips_a_markdown_code_fence() -> None:
    content = '```json\n[{"name": "Jo Park", "side": "our_side", "affiliations": []}]\n```'
    mentions = parse_keyman_response(content)
    assert len(mentions) == 1
    assert mentions[0].person_name == "Jo Park"


def test_empty_array_is_no_mentions() -> None:
    assert parse_keyman_response("[]") == []


def test_entry_missing_name_is_skipped() -> None:
    content = '[{"side": "our_side", "affiliations": []}]'
    assert parse_keyman_response(content) == []


def test_entry_with_invalid_side_is_skipped() -> None:
    content = '[{"name": "Ambiguous Person", "side": "unknown", "affiliations": []}]'
    assert parse_keyman_response(content) == []


def test_invalid_json_fails_closed_without_deleting_existing_mentions() -> None:
    with pytest.raises(ValueError, match="valid JSON array"):
        parse_keyman_response("not json at all")


def test_non_list_top_level_fails_closed_without_deleting_existing_mentions() -> None:
    with pytest.raises(ValueError, match="JSON array"):
        parse_keyman_response('{"name": "not a list"}')


_ORCHESTRATOR_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL")
_ORCHESTRATOR_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY")


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_contextual_orchestrator_extracts_keymen_from_an_ambiguous_post() -> None:
    """A real LLM call, with real assertions grounded in the fixture's
    actual content -- not just 'the call didn't crash'. The fixture names
    four people; a correct extraction must find the two unambiguously
    described ones, classify Jordan as our-side and Priya as counterparty,
    and must not invent a person for Westfield Power (an org that sent no
    one).
    """
    client = ContextualOrchestratorKeymanExtractionClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY
    )
    title, body = ambiguous_keyman_post()

    mentions = client.extract(title, body)

    names = {mention.person_name for mention in mentions}
    assert any("Jordan" in name for name in names)
    assert any("Priya" in name for name in names)
    assert not any("Westfield" in name for name in names)

    by_name = {mention.person_name: mention for mention in mentions}
    jordan = next(m for name, m in by_name.items() if "Jordan" in name)
    priya = next(m for name, m in by_name.items() if "Priya" in name)
    assert jordan.person_side_code == OUR_SIDE
    assert priya.person_side_code == COUNTERPARTY
    assert len(priya.affiliated_organization_names) >= 2

    # Sam Okonkwo is named only by role ("our legal counsel, Sam Okonkwo") --
    # a real assertion that job_title extraction reads the text, not a
    # synthetic fixture built just to satisfy this one field.
    sam = next((m for name, m in by_name.items() if "Sam" in name or "Okonkwo" in name), None)
    assert sam is not None
    assert sam.job_title is not None
    assert "counsel" in sam.job_title.lower() or "legal" in sam.job_title.lower()
