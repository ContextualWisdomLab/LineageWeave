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

def test_project_candidate_node_id_requires_normalized_key() -> None:
    """A raw project label must be normalized before node construction."""
    from lineageweave.post_summary import (
        normalize_project_key,
        project_candidate_node_id,
    )

    assert project_candidate_node_id(
        "11111111-1111-1111-1111-111111111111", "hvdc-pilot"
    ) == "11111111-1111-1111-1111-111111111111/hvdc-pilot"
    assert normalize_project_key(" HVDC Pilot ") == "hvdc-pilot"
    with pytest.raises(ValueError, match="already be normalized"):
        project_candidate_node_id("11111111-1111-1111-1111-111111111111", "HVDC Pilot")


def test_parse_project_candidate_node_id_rejects_bad_separators() -> None:
    """A node id must contain exactly one post/key separator and be canonical."""
    from lineageweave.post_summary import parse_project_candidate_node_id

    with pytest.raises(ValueError, match="one post/key separator"):
        parse_project_candidate_node_id("no-separator-here")
    with pytest.raises(ValueError, match="one post/key separator"):
        parse_project_candidate_node_id("post/key/extra")
    with pytest.raises(ValueError, match="already be normalized|not canonical"):
        parse_project_candidate_node_id(
            "11111111-1111-1111-1111-111111111111/UNCANONICAL"
        )
    assert parse_project_candidate_node_id(
        "11111111-1111-1111-1111-111111111111/hvdc-pilot"
    ) == ("11111111-1111-1111-1111-111111111111", "hvdc-pilot")


def test_major_event_action_rejects_missing_text() -> None:
    """Action and evidence text are both required."""
    from lineageweave.post_summary import MajorEventAction

    base = dict(requester_actor_name=None, processor_actor_name=None)
    with pytest.raises(ValueError, match="action and evidence"):
        MajorEventAction(**base, action_text="  ", evidence_text="evidence")
    with pytest.raises(ValueError, match="action and evidence"):
        MajorEventAction(**base, action_text="action", evidence_text="  ")
    assert MajorEventAction(
        **base, action_text="action", evidence_text="evidence"
    ).evidence_text == "evidence"


def test_five_w1h_evidence_rejects_unknown_slot_or_missing_text() -> None:
    """5W1H evidence requires a governed slot plus value and support text."""
    from lineageweave.post_summary import FiveW1HEvidence

    with pytest.raises(ValueError, match="unsupported 5W1H evidence slot"):
        FiveW1HEvidence(slot_code="when-not-a-slot", value_text="v", evidence_text="e")
    with pytest.raises(ValueError, match="requires a value and supporting text"):
        FiveW1HEvidence(slot_code="when", value_text=" ", evidence_text="e")
    with pytest.raises(ValueError, match="requires a value and supporting text"):
        FiveW1HEvidence(slot_code="where", value_text="v", evidence_text="")

    assert (
        FiveW1HEvidence(slot_code="when", value_text="3월 4일", evidence_text="회의").slot_code
        == "when"
    )


def test_project_mention_rejects_blank_names_or_out_of_range_confidence() -> None:
    """Every project mention requires names and evidence plus bounded confidence."""
    from lineageweave.post_summary import ProjectMention

    with pytest.raises(ValueError, match="require names and evidence"):
        ProjectMention(project_name="  ", canonical_name="c", evidence="e", confidence=0.5)
    with pytest.raises(ValueError, match="require names and evidence"):
        ProjectMention(project_name="p", canonical_name="c", evidence="  ", confidence=0.5)
    with pytest.raises(ValueError, match="between 0 and 1"):
        ProjectMention(project_name="p", canonical_name="c", evidence="e", confidence=2.0)


def test_key_event_rejects_blank_text_or_explicitly_empty_project_key() -> None:
    """Key events require text and reject an empty project key."""
    from lineageweave.post_summary import KeyEvent

    with pytest.raises(ValueError, match="require event text"):
        KeyEvent(event_text="  ")
    with pytest.raises(ValueError, match="must be non-empty"):
        KeyEvent(event_text="event", project_key="   ")


def test_hallucinated_account_name_detects_a_matching_context_hint() -> None:
    """A context hint naming the account selects it as a hallucination guard."""
    from lineageweave.post_summary import _hallucinated_account_name

    assert (
        _hallucinated_account_name(
            "author_account_name=Demo Analyst [source_field=user_account.display_name]"
        )
        == "Demo Analyst"
    )
    assert _hallucinated_account_name("") is None
    assert _hallucinated_account_name("no account hint here") is None


def test_plain_details_accepts_three_column_role_rows() -> None:
    """A 3-column role row defaults the actor type to person."""
    from lineageweave.post_summary import _parse_plain_summary_details

    details = _parse_plain_summary_details(
        "ROLES:\n홍길동 | 자료 검토 | 당사\n"
        "PROJECTS:\nNONE\n"
        "EVIDENCE:\nNONE",
        context_hints="author_account_name=Demo Analyst [source_field=user_account.display_name]",
    )
    assert details is not None
    assert details[0][0].actor_type_code == "prov_person"
    assert details[0][0].affiliated_organization_name == "당사"


def test_plain_details_drops_template_echo_rows_and_hallucinated_actor() -> None:
    """Prompt-template echoes and the logged-in account are never actors."""
    from lineageweave.post_summary import _parse_plain_summary_details

    details = _parse_plain_summary_details(
        "ROLES:\n"
        "actor name | responsibility | person, organization, or team | affiliation or none\n"
        "Demo Analyst | 고객 면담 | person | Demo Corp\n"
        "Jordi Gil | 견적 승인 | person | Northwind Labs\n"
        "PROJECTS:\nNONE",
        context_hints="author_account_name=Demo Analyst [source_field=user_account.display_name]; "
        "author_affiliations=Demo Corp [source_field=account_affiliation.corporate_entity_id]",
    )
    assert details is not None
    assert [role.actor_name for role in details[0]] == ["Jordi Gil"]


def test_plain_details_skips_role_rows_with_unknown_actor_column() -> None:
    """A row whose actor column isn't person/organization/team is dropped."""
    from lineageweave.post_summary import _parse_plain_summary_details

    details = _parse_plain_summary_details(
        "ROLES:\n"
        "Q&A participant | 발표 듣기 | some-description | Acme\n"
        "PROJECTS:\nNONE"
    )
    assert details is not None
    assert details[0] == ()


def test_plain_details_project_uses_post_title_as_evidence_when_empty() -> None:
    """A project whose evidence column is empty falls back to the post title."""
    from lineageweave.post_summary import _parse_plain_summary_details

    details = _parse_plain_summary_details(
        "ROLES:\nNONE\n"
        "PROJECTS:\nHVDC Pilot | hvdc-pilot | none | 0.9",
        post_title="HVDC Pilot 견적 검토",
    )
    assert details is not None
    assert details[1][0].evidence == "HVDC Pilot 견적 검토"


def test_plain_details_drops_untitled_and_unparsable_project_rows() -> None:
    """Projects whose empty evidence cannot borrow a title are dropped."""
    from lineageweave.post_summary import _parse_plain_summary_details

    details = _parse_plain_summary_details(
        "ROLES:\nNONE\n"
        "PROJECTS:\nUnknown Project | unknown-project | NONE | not-a-number\n"
        "Mystery | mystery | NONE | 0.5",
        post_title="",
    )
    assert details is not None
    assert details[1] == ()


def test_plain_details_five_column_actions_recognize_actors_and_fallback() -> None:
    """5-column actions use actor columns; unrecognized rows fall back to legacy."""
    from lineageweave.post_summary import _parse_plain_summary_details

    details = _parse_plain_summary_details(
        "ROLES:\n"
        "홍길동 | 변경 요청 | person | 당사\n"
        "김철수 | 도면 수정 | person | 고객사\n"
        "PROJECTS:\nNONE\n"
        "ACTIONS:\n"
        "도면 변경 승인 | hvdc-pilot | 홍길동 | 김철수 | 근거 문장\n"
        "드롭 될 행 | x | NotAnActor | NothingInteresting | bad"
    )
    assert details is not None
    assert [action.action_text for action in details[2]] == [
        "도면 변경 승인",
        "드롭 될 행",
    ]
    assert details[2][0].project_key == "hvdc-pilot"
    assert details[2][0].requester_actor_name == "홍길동"
    assert details[2][0].processor_actor_name == "김철수"
    assert details[2][1].project_key is None


def test_plain_details_requires_roles_and_projects_sections() -> None:
    """Missing ROLES/PROJECTS sections fail the whole parse."""
    from lineageweave.post_summary import _parse_plain_summary_details

    assert _parse_plain_summary_details("ROLES:\nNONE") is None
    assert _parse_plain_summary_details("EVIDENCE:\nwhere | x | y") is None
    assert _parse_plain_summary_details("") is None
