"""Tests for lineageweave.corporate_hierarchy_inference (ADR 0010).

Pure parse-function tests, same style as test_organization_name_resolution.py
-- the HTTP mechanics are already covered by test_http_client.py.
"""

from __future__ import annotations

from lineageweave.corporate_hierarchy_inference import (
    LEVEL_COMPANY,
    LEVEL_GROUP,
    LEVEL_PLANT,
    HierarchyProposal,
    parse_inference_response,
)


def test_parses_a_plant_with_a_parent() -> None:
    content = '{"level": "plant", "parent_name": "삼성전자"}'
    assert parse_inference_response(content) == HierarchyProposal(
        level_code=LEVEL_PLANT, parent_name="삼성전자"
    )


def test_parses_a_group_with_no_parent() -> None:
    content = '{"level": "group", "parent_name": null}'
    assert parse_inference_response(content) == HierarchyProposal(level_code=LEVEL_GROUP, parent_name=None)


def test_company_level_recognized() -> None:
    content = '{"level": "company", "parent_name": "Some Group"}'
    result = parse_inference_response(content)
    assert result is not None
    assert result.level_code == LEVEL_COMPANY


def test_unknown_response_returns_none() -> None:
    assert parse_inference_response("UNKNOWN") is None
    assert parse_inference_response("unknown\n") is None


def test_empty_response_returns_none() -> None:
    assert parse_inference_response("") is None


def test_malformed_json_returns_none() -> None:
    assert parse_inference_response("not json at all") is None


def test_invalid_level_code_returns_none() -> None:
    """A level outside the three valid codes must not be silently
    accepted as if it were a real classification."""
    content = '{"level": "division", "parent_name": null}'
    assert parse_inference_response(content) is None


def test_blank_parent_name_becomes_none() -> None:
    content = '{"level": "company", "parent_name": "   "}'
    result = parse_inference_response(content)
    assert result is not None
    assert result.parent_name is None


def test_markdown_fenced_json_is_rejected_not_stripped() -> None:
    """Unlike post_summary's parser, this one does not strip code
    fences -- the prompt asks for raw JSON only; a fenced response
    means the model did not follow instructions and should not be
    silently repaired into a trusted hierarchy claim.
    """
    content = '```json\n{"level": "company", "parent_name": null}\n```'
    assert parse_inference_response(content) is None
