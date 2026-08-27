"""Direct branch coverage for the compact summary-details parser.

``_parse_summary_details`` decodes provider JSON (optionally code-fenced)
into role/responsibility and project-mention tuples. Its dict vs. pipe
string encodings, actor-type mapping, affiliation normalization, and
malformed-entry rejection are pure logic the end-to-end summary path only
hits on happy-path fixtures.
"""

from __future__ import annotations

import json

import pytest

from lineageweave.post_summary import (
    ACTOR_TYPE_ORGANIZATION,
    ACTOR_TYPE_PERSON,
    ACTOR_TYPE_TEAM,
    ProjectMention,
    RoleResponsibility,
    _parse_summary_details,
)


def _json_content(payload: object) -> str:
    """Return the provider payload as raw JSON text."""
    return json.dumps(payload)


def test_parse_returns_empty_tuples_for_invalid_json() -> None:
    assert _parse_summary_details("{not-json") == ((), ())
    assert _parse_summary_details("") == ((), ())


def test_parse_returns_empty_tuples_for_non_object_json() -> None:
    assert _parse_summary_details("[1, 2, 3]") == ((), ())
    assert _parse_summary_details('"plain string"') == ((), ())


def test_parse_handles_code_fenced_json() -> None:
    payload = {"roles": [], "projects": [], "summary": "x"}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    assert _parse_summary_details(fenced) == ((), ())


def test_parse_roles_from_dict_entries_with_actor_types() -> None:
    content = _json_content(
        {
            "roles_and_responsibilities": [
                {"actor_name": "김다은", "responsibility": "검토"},
                {"actor_name": "설계부", "responsibility": "승인", "actor_type": "organization"},
                {"actor_name": "설계팀", "responsibility": "배포", "actor_type": "Team"},
            ]
        }
    )
    roles, projects = _parse_summary_details(content)
    assert [role.actor_name for role in roles] == ["김다은", "설계부", "설계팀"]
    assert [role.actor_type_code for role in roles] == [
        ACTOR_TYPE_PERSON,
        ACTOR_TYPE_ORGANIZATION,
        ACTOR_TYPE_TEAM,
    ]


def test_parse_roles_from_pipe_string_entries() -> None:
    content = _json_content(
        {
            "roles": [
                "담당자|작성|person|영업팀",
                "협력사|검증|organization|",
            ]
        }
    )
    roles, projects = _parse_summary_details(content)
    assert roles == (
        RoleResponsibility(
            actor_name="담당자",
            responsibility="작성",
            actor_type_code=ACTOR_TYPE_PERSON,
            affiliated_organization_name="영업팀",
        ),
        RoleResponsibility(
            actor_name="협력사",
            responsibility="검증",
            actor_type_code=ACTOR_TYPE_ORGANIZATION,
            affiliated_organization_name=None,
        ),
    )


def test_parse_drops_roles_with_wrong_pipe_arity_or_missing_fields() -> None:
    content = _json_content(
        {
            "roles": [
                "only|three|parts",
                ["not", "a", "string"],
            ],
            "roles_and_responsibilities": None,
        }
    )
    assert _parse_summary_details(content)[0] == ()


def test_parse_skips_roles_with_empty_names_or_responsibilities() -> None:
    content = _json_content(
        {
            "roles": [
                {"actor_name": "", "responsibility": "작성"},
                {"actor_name": "담당자", "responsibility": "  "},
            ]
        }
    )
    assert _parse_summary_details(content)[0] == ()


def test_parse_normalizes_affiliation_empty_strings() -> None:
    content = _json_content(
        {
            "roles": [
                {"actor_name": "A", "responsibility": "r", "affiliated_organization_name": "none"},
                {"actor_name": "B", "responsibility": "r", "affiliated_organization_name": "Null"},
                {"actor_name": "C", "responsibility": "r", "affiliated_organization_name": "없음"},
                {"actor_name": "D", "responsibility": "r", "affiliated_organization_name": "  "},
            ]
        }
    )
    roles, _ = _parse_summary_details(content)
    assert [role.affiliated_organization_name for role in roles] == [None, None, None, None]


def test_parse_projects_from_dict_entries() -> None:
    content = _json_content(
        {
            "project_mentions": [
                {
                    "project_name": "구매",
                    "canonical_name": "procurement",
                    "evidence": "본문 언급",
                    "confidence": 0.8,
                }
            ]
        }
    )
    roles, projects = _parse_summary_details(content)
    assert projects == (
        ProjectMention(
            project_name="구매",
            canonical_name="procurement",
            evidence="본문 언급",
            confidence=0.8,
        ),
    )


def test_parse_projects_from_pipe_string_entries() -> None:
    content = _json_content(
        {
            "projects": ["설계|design|문서 참조|0.95"],
        }
    )
    _, projects = _parse_summary_details(content)
    assert projects == (
        ProjectMention(
            project_name="설계",
            canonical_name="design",
            evidence="문서 참조",
            confidence=0.95,
        ),
    )


def test_parse_drops_projects_with_non_string_fields() -> None:
    content = _json_content(
        {
            "projects": [
                ["설계", "design", "evidence", "0.9"],
                {"project_name": "설계", "canonical_name": "design"},
            ]
        }
    )
    assert _parse_summary_details(content)[1] == ()


def test_parse_drops_projects_with_unparsable_or_out_of_range_confidence() -> None:
    content = _json_content(
        {
            "projects": [
                {"project_name": "A", "canonical_name": "a", "evidence": "e", "confidence": "NaN"},
                {"project_name": "B", "canonical_name": "b", "evidence": "e", "confidence": 1.5},
                {"project_name": "C", "canonical_name": "c", "evidence": "e", "confidence": -0.2},
            ]
        }
    )
    assert _parse_summary_details(content)[1] == ()


def test_parse_ignores_non_list_roles_and_projects() -> None:
    content = _json_content(
        {
            "roles": "not-a-list",
            "roles_and_responsibilities": "also-not-a-list",
            "projects": {"single": "object"},
            "project_mentions": None,
        }
    )
    assert _parse_summary_details(content) == ((), ())


def test_parse_pipe_string_with_maxsplit_merges_extra_fields() -> None:
    """split(..., maxsplit=3) merges a fifth field into the affiliation slot."""
    content = _json_content({"roles": ["A|B|C|D|E"]})
    roles, _ = _parse_summary_details(content)
    assert roles == (
        RoleResponsibility(
            actor_name="A",
            responsibility="B",
            actor_type_code=ACTOR_TYPE_PERSON,
            affiliated_organization_name="D|E",
        ),
    )


def test_parse_single_part_pipe_string_is_dropped() -> None:
    content = _json_content({"roles": ["A"], "projects": ["A"]})
    roles, projects = _parse_summary_details(content)
    assert roles == ()
    assert projects == ()