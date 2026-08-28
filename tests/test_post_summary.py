"""Tests for lineageweave.post_summary.

parse_summary_response's tests need no live provider. The real-provider
test reuses fixtures.ambiguous_keyman_post -- it already has multiple
people, an implied timeline (a bid workshop, a follow-up, "last quarter"),
and an ambiguous responsibility (Priya's dual role is what made the
warranty language messy), which is exactly the "non-trivial" shape Phase
4's stop condition calls for.
"""

from __future__ import annotations

import os

import pytest

from backend.app.post_summary_ingestion import (
    require_summary_source_body,
    seeded_fixture_summary,
)
from lineageweave.fixtures import (
    ambiguous_commitment_post,
    ambiguous_keyman_post,
    fixture_thread_cast,
    sample_records,
)
from lineageweave.post_summary import (
    _SUMMARY_REQUEST_PROMPT_TEMPLATE,
    ContextualOrchestratorPostSummaryClient,
    NullPostSummaryClient,
    RoleResponsibility,
    _parse_optional_project_key,
    _parse_plain_summary_details,
    _parse_plain_summary_response,
    parse_summary_response,
)


def test_null_summary_client_is_unavailable_not_empty_summary() -> None:
    client = NullPostSummaryClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.summarize("any title", "any body")


def test_summary_prompt_requires_trigger_development_conclusion_structure() -> None:
    """Feature request (2026-08-19): a flat 5W1H restatement in body
    order was ruled a bug -- the prompt must ask for a legible
    발단(trigger)/전개(development)/결론(conclusion) narrative arc so a
    reader can tell what triggered the post, what was actually
    considered, and what was decided or left open.
    """
    for marker in ("발단", "전개", "결론", "다음 조치는"):
        assert marker in _SUMMARY_REQUEST_PROMPT_TEMPLATE


def test_summary_prompt_requires_naming_actual_people_not_generic_titles() -> None:
    """Live bug (2026-08-19): a real post's summary said "PM들이
    참석했다" (a generic "PMs attended") even though the post body
    literally named each attendee -- the same names a separate R&R
    extraction call correctly pulled out. The summary call has no
    knowledge of that separate call's output, so the summary prompt
    itself must demand real names, not rely on R&R to carry them.
    """
    assert "PM들이 참석했다" in _SUMMARY_REQUEST_PROMPT_TEMPLATE
    assert "홍길동" in _SUMMARY_REQUEST_PROMPT_TEMPLATE


def test_summary_requires_imported_source_body() -> None:
    assert require_summary_source_body("  body  ") == "  body  "
    with pytest.raises(ValueError, match="source post body is empty"):
        require_summary_source_body("")


def test_parses_a_well_formed_json_object() -> None:
    content = (
        '{"korean_summary": "회의 후속 조치에 대한 요약입니다.", '
        '"key_events": ["입찰 워크숍 진행", "검사 일정 확인 요청"], '
        '"roles_and_responsibilities": [{"actor_name": "Jordan Hale", "responsibility": "입찰 일정 안내", '
        '"actor_type": "person", "affiliated_organization_name": "Westfield Power"}]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    assert summary.korean_summary == "회의 후속 조치에 대한 요약입니다."
    assert summary.key_events == ("입찰 워크숍 진행", "검사 일정 확인 요청")
    role = summary.roles_and_responsibilities[0]
    assert role.actor_name == "Jordan Hale"
    assert role.actor_type_code == "prov_person"
    assert role.affiliated_organization_name == "Westfield Power"


def test_parses_explicit_five_w1h_evidence_with_source_phrase() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"요약", "key_events":[], '
        '"five_w1h_evidence":[{"slot_code":"when", "value_text":"3월 4일", '
        '"evidence_text":"3월 4일 현장 회의"}]}'
    )
    assert summary is not None
    assert summary.five_w1h_evidence[0].slot_code == "when"
    assert summary.five_w1h_evidence[0].evidence_text == "3월 4일 현장 회의"


def test_parses_plain_summary_evidence_section() -> None:
    details = _parse_plain_summary_details(
        "ROLES:\nNONE\nPROJECTS:\nNONE\nEVIDENCE:\n"
        "where | 제3공장 | 제3공장에서 협의했다"
    )
    assert details is not None
    assert details[3][0].value_text == "제3공장"


def test_parses_major_event_requester_and_processor() -> None:
    details = _parse_plain_summary_details(
        "ROLES:\n"
        "홍길동 | 변경 요청 | person | 당사\n"
        "김철수 | 도면 수정 | person | 고객사\n"
        "PROJECTS:\nNONE\n"
        "ACTIONS:\n"
        "도면 변경 승인 | 홍길동 | 김철수 | 홍길동이 변경을 요청했고 김철수가 수정하기로 함"
    )
    assert details is not None
    action = details[2][0]
    assert action.requester_actor_name == "홍길동"
    assert action.processor_actor_name == "김철수"


def test_parses_project_bound_major_event_action() -> None:
    details = _parse_plain_summary_details(
        "ROLES:\n"
        "홍길동 | 변경 요청 | person | 당사\n"
        "김철수 | 도면 수정 | person | 고객사\n"
        "PROJECTS:\n"
        "HVDC Pilot | hvdc-pilot | 파일럿 도면 | 0.9\n"
        "ACTIONS:\n"
        "도면 변경 승인 | hvdc-pilot | 홍길동 | 김철수 | 프로젝트 도면 근거"
    )
    assert details is not None
    assert details[2][0].project_key == "hvdc-pilot"


def test_legacy_action_preserves_pipe_in_evidence_text() -> None:
    details = _parse_plain_summary_details(
        "ROLES:\n"
        "Synthetic requester | 요청 | person | Synthetic organization\n"
        "Synthetic processor | 처리 | person | Synthetic organization\n"
        "PROJECTS:\nNONE\n"
        "ACTIONS:\n"
        "합성 조치 | Synthetic requester | Synthetic processor | 첫 근거 | 추가 근거"
    )
    assert details is not None
    assert details[2][0].project_key is None
    assert details[2][0].evidence_text == "첫 근거 | 추가 근거"


def test_json_project_name_is_normalized_for_legacy_action_contract() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"요약", "major_event_actions":['
        '{"action_text":"검토", "project_name":"HVDC Pilot", '
        '"evidence_text":"본문 근거"}]}'
    )
    assert summary is not None
    assert summary.major_event_actions[0].project_key == "hvdc-pilot"


def test_parses_project_bound_key_event_without_leaking_internal_key_to_text() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"요약", "key_events":[{"event_text":"도면 검토",'
        '"project_key":"HVDC Pilot"}]}'
    )
    assert summary is not None
    assert summary.key_events == ("도면 검토",)
    assert summary.key_event_details[0].project_key == "hvdc-pilot"


def test_parses_project_bound_plain_key_event() -> None:
    parsed = _parse_plain_summary_response(
        "회의 요약\nKEY EVENTS: hvdc-pilot :: 도면 검토; NONE :: 공통 일정 확인"
    )
    assert parsed is not None
    _summary, events, details = parsed
    assert events == ("도면 검토", "공통 일정 확인")
    assert details[0].project_key == "hvdc-pilot"
    assert details[1].project_key is None


def test_optional_project_key_normalizes_unicode_and_rejects_sentinels() -> None:
    assert _parse_optional_project_key("  Project  Ω ") == "project-ω"
    for sentinel in (None, "", "  ", "None", "N/A", "unknown", 42):
        assert _parse_optional_project_key(sentinel) is None


def test_organization_actor_is_not_forced_into_a_person_slot() -> None:
    """A named actor that is genuinely an organization (e.g. our own
    company acting in its own name, not a named individual) must parse
    as ``prov_organization``, not silently default to person -- the
    default only applies when the model omits ``actor_type`` entirely.
    """
    content = (
        '{"korean_summary": "당사가 요청 사항을 확인했습니다.", "key_events": [], '
        '"roles_and_responsibilities": [{"actor_name": "당사", "responsibility": "요청 확인", '
        '"actor_type": "organization", "affiliated_organization_name": null}]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    role = summary.roles_and_responsibilities[0]
    assert role.actor_name == "당사"
    assert role.actor_type_code == "prov_organization"
    assert role.affiliated_organization_name is None


def test_team_actor_is_meso_level_not_organization() -> None:
    """A named sub-unit of a company (e.g. 설계팀, "design team") must
    parse as ``prov_team``, distinct from both ``prov_person`` and
    ``prov_organization`` -- it is part of a company, not the company
    itself (ADR 0007), and its parent company's name must still land in
    ``affiliated_organization_name``.
    """
    content = (
        '{"korean_summary": "설계팀이 도면을 검토했습니다.", "key_events": [], '
        '"roles_and_responsibilities": [{"actor_name": "설계팀", "responsibility": "도면 검토", '
        '"actor_type": "team", "affiliated_organization_name": "Demo Corp"}]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    role = summary.roles_and_responsibilities[0]
    assert role.actor_name == "설계팀"
    assert role.actor_type_code == "prov_team"
    assert role.affiliated_organization_name == "Demo Corp"


def test_unknown_actor_type_code_is_rejected() -> None:
    with pytest.raises(ValueError, match="actor_type_code"):
        RoleResponsibility(actor_name="Ada West", responsibility="후속", actor_type_code="person")


def test_missing_actor_type_defaults_to_person() -> None:
    content = (
        '{"korean_summary": "요약", "key_events": [], '
        '"roles_and_responsibilities": [{"actor_name": "Ada West", "responsibility": "후속"}]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    assert summary.roles_and_responsibilities[0].actor_type_code == "prov_person"
    assert summary.roles_and_responsibilities[0].affiliated_organization_name is None


def test_missing_korean_summary_returns_none() -> None:
    content = '{"key_events": [], "roles_and_responsibilities": []}'
    assert parse_summary_response(content) is None


def test_empty_korean_summary_returns_none() -> None:
    content = '{"korean_summary": "   ", "key_events": [], "roles_and_responsibilities": []}'
    assert parse_summary_response(content) is None


def test_invalid_json_returns_none() -> None:
    assert parse_summary_response("not json") is None


def test_every_sample_record_has_a_seeded_korean_summary() -> None:
    """Event Lineage click-through must have a stored Korean summary for
    every reconstruct fixture -- not a shared placeholder, not English.
    """
    seen: set[str] = set()
    for rec in sample_records():
        summary = seeded_fixture_summary(rec.label)
        assert summary is not None, rec.label
        assert any("가" <= ch <= "힣" for ch in summary.korean_summary)
        assert summary.key_events
        assert summary.korean_summary not in seen
        seen.add(summary.korean_summary)
        cast = fixture_thread_cast(rec.label)
        names = {role.actor_name for role in summary.roles_and_responsibilities}
        if cast is not None and cast.person_names:
            assert set(cast.person_names) <= names
        else:
            assert names == set()
    calendar_title, _ = ambiguous_commitment_post()
    calendar = seeded_fixture_summary(calendar_title)
    assert calendar is not None
    assert "리버벤드" in calendar.korean_summary
    assert calendar.roles_and_responsibilities == ()
    assert seeded_fixture_summary("not a fixture title") is None


def test_malformed_roles_entries_are_skipped_not_crashed_on() -> None:
    content = (
        '{"korean_summary": "요약", "key_events": [], '
        '"roles_and_responsibilities": [{"actor_name": "Only Name"}, "not an object"]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    assert summary.roles_and_responsibilities == ()


def test_summary_request_uses_plain_route_evidence_contract(monkeypatch) -> None:
    observed: list[dict[str, object]] = []

    def fake_post_json(url, payload, *, headers, timeout):
        observed.append(payload)
        prompt = payload["messages"][0]["content"]
        if "ROLES:" in prompt:
            content = (
                "ROLES:\n"
                "Jordan Hale | 입찰 일정 안내 | Westfield Power\n"
                "PROJECTS:\n"
                "HVDC pilot | pilot bid workshop | 0.9\n"
                "Unsupported project | NONE | 1"
            )
        else:
            content = "본문 근거 요약\n\nKEY EVENTS: 후속 확인"
        return {
            "choices": [
                {
                    "message": {
                        "content": content
                    }
                }
            ]
        }

    monkeypatch.setattr("lineageweave.post_summary.post_json", fake_post_json)
    summary = ContextualOrchestratorPostSummaryClient("https://orchestrator.test", "token").summarize(
        "Synthetic title", "Synthetic body"
    )

    assert summary.korean_summary == "본문 근거 요약"
    assert summary.key_events == ("후속 확인",)
    assert len(observed) == 2
    assert all(payload["mode"] == "auto" for payload in observed)
    assert "KEY EVENTS" in observed[0]["messages"][0]["content"]
    details_prompt = observed[1]["messages"][0]["content"]
    assert "source_process_unit_name are PU/business-unit hints only" in details_prompt
    assert "must never be" in details_prompt
    assert "sales-pool/order-pool value" in details_prompt
    assert "source_sales_pool_name are sales-pool/order-pool hints only" in details_prompt
    assert "PU/business-unit value" in details_prompt
    assert summary.roles_and_responsibilities[0].actor_name == "Jordan Hale"
    assert summary.project_mentions[0].canonical_name == "hvdc-pilot"


def test_summary_details_parse_failure_does_not_expose_provider_response(monkeypatch) -> None:
    """Malformed provider output gets a stable parser error, never raw text."""
    responses = iter(
        (
            {
                "choices": [
                    {"message": {"content": "본문 근거 요약\nKEY EVENTS: 후속 확인"}}
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": "provider-secret-and-gateway-prompt"
                        }
                    }
                ]
            },
        )
    )

    monkeypatch.setattr(
        "lineageweave.post_summary.post_json",
        lambda *args, **kwargs: next(responses),
    )

    with pytest.raises(
        ValueError,
        match="summary semantic response did not match the required format",
    ) as exc_info:
        ContextualOrchestratorPostSummaryClient("https://orchestrator.test", "token").summarize(
            "Synthetic title", "Synthetic body"
        )

    assert "provider-secret-and-gateway-prompt" not in str(exc_info.value)


def test_title_match_can_supply_explicit_project_evidence_but_not_a_guess() -> None:
    details = _parse_plain_summary_details(
        "ROLES:\nNONE\nPROJECTS:\nNorthridge transformer bid | NONE | 1",
        post_title="Follow-up after the Northridge transformer bid workshop",
    )
    assert details is not None
    assert details[1][0].evidence == "Follow-up after the Northridge transformer bid workshop"

    unrelated = _parse_plain_summary_details(
        "ROLES:\nNONE\nPROJECTS:\nUnrelated project | NONE | 1",
        post_title="Follow-up after the Northridge transformer bid workshop",
    )
    assert unrelated == ((), (), (), ())


def test_role_matching_the_hinted_account_name_is_dropped_not_cataloged() -> None:
    """Live finding: the model wrote a ROLES row for the logged-in
    account's display name (from author_account_name in the hints)
    even though that name never appeared in the post text -- see
    _hallucinated_account_name's docstring.
    """
    details = _parse_plain_summary_details(
        "ROLES:\n"
        "Demo Analyst | met the customer | person | Demo Corp\n"
        "Jordi Gil | approved the quote | person | Northwind Labs\n"
        "PROJECTS:\nNONE",
        context_hints="author_account_name=Demo Analyst [source_field=user_account.display_name]; "
        "author_affiliations=Demo Corp [source_field=account_affiliation.corporate_entity_id]",
    )
    assert details is not None
    assert [role.actor_name for role in details[0]] == ["Jordi Gil"]


_ORCHESTRATOR_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL")
_ORCHESTRATOR_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY")


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_contextual_orchestrator_summarizes_a_non_trivial_post() -> None:
    client = ContextualOrchestratorPostSummaryClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY
    )
    title, body = ambiguous_keyman_post()

    summary = client.summarize(title, body)

    assert summary.korean_summary.strip() != ""
    # A genuine Korean summary should contain at least one Hangul syllable
    # block -- not just an English sentence handed back unchanged.
    assert any("가" <= ch <= "힣" for ch in summary.korean_summary)
    assert len(summary.key_events) >= 1
    people_named = {rr.actor_name for rr in summary.roles_and_responsibilities}
    assert any("Jordan" in name or "Priya" in name for name in people_named)


def test_non_object_json_summary_returns_none() -> None:
    """A JSON non-object response is a missing summary, not an empty one."""
    from lineageweave.post_summary import parse_summary_response

    assert parse_summary_response("[1, 2, 3]") is None
    assert parse_summary_response('"just a string"') is None


def test_dict_key_event_and_role_guards_are_dropped_individually() -> None:
    """Invalid dict key events and roles fail closed without killing the parse."""
    from lineageweave.post_summary import parse_summary_response

    content = (
        '{"korean_summary":"요약", '
        '"key_events":['
        '{"event_text":"도면 검토", "project_key":"HVDC Pilot"},'
        '{"event_text":"  ", "project_key":"x"},'
        '{"event": null, "project_name":null},'
        '"문자열 이벤트"'
        "], "
        '"roles_and_responsibilities":['
        '{"actor_name":"홍길동", "responsibility":"검토", "actor_type":"person", '
        '"affiliated_organization_name":"당사"},'
        '{"actor_name": 7, "responsibility":"검토"},'
        '"not-a-dict-role"'
        "], "
        '"project_mentions":[], "major_event_actions":[], "five_w1h_evidence":[]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    assert summary.key_events == ("도면 검토", "문자열 이벤트")
    assert summary.key_event_details[0].project_key == "hvdc-pilot"
    assert [role.actor_name for role in summary.roles_and_responsibilities] == [
        "홍길동"
    ]


def test_dict_project_mentions_with_defaults_and_bounds() -> None:
    """Project-mention dict rows accept defaults and drop bad confidence."""
    from lineageweave.post_summary import parse_summary_response

    content = (
        '{"korean_summary":"요약", "key_events":[], '
        '"project_mentions":['
        '{"project_name":"HVDC Pilot", "canonical_name":"hvdc-pilot", '
        '"evidence":"문서 근거", "confidence":0.9},'
        '{"project_name":"Bad", "canonical_name":"bad", '
        '"evidence":"문서 근거", "confidence":"nonsense"}'
        "], "
        '"major_event_actions":[], "five_w1h_evidence":[]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    assert len(summary.project_mentions) == 1
    assert summary.project_mentions[0].project_name == "HVDC Pilot"


def test_dict_major_event_actions_drop_non_string_rows_and_preserve_others() -> None:
    """Action dict rows with non-string text are dropped; others are kept."""
    from lineageweave.post_summary import parse_summary_response

    content = (
        '{"korean_summary":"요약", "key_events":[], '
        '"major_event_actions":['
        '{"action_text":"변경 승인", "project_name":null, '
        '"requester_name":"홍길동", "processor_name":null, "evidence_text":"근거"},'
        '{"action_text": 7, "evidence_text":"근거"},'
        '{"action_text":"실패", "evidence_text":"근거", "confidence":"bad"}'
        "], "
        '"project_mentions":[], "five_w1h_evidence":[]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    assert [action.action_text for action in summary.major_event_actions] == [
        "변경 승인",
        "실패",
    ]
