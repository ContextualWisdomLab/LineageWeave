"""Tests for lineageweave.post_summary.

parse_summary_response's tests need no live provider. The real-provider
test reuses fixtures.ambiguous_keyman_post -- it already has multiple
people, an implied timeline (a bid workshop, a follow-up, "last quarter"),
and an ambiguous responsibility (Priya's dual role is what made the
warranty language messy), which is exactly the "non-trivial" shape Phase
4's stop condition calls for.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from backend.app.post_summary_ingestion import (
    SUMMARY_TARGET_UNAVAILABLE,
    require_summary_target,
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
    ACTOR_TYPE_ORGANIZATION,
    ContextualOrchestratorPostSummaryClient,
    NullPostSummaryClient,
    ProjectMention,
    RoleResponsibility,
    SemanticRelationship,
    _SUMMARY_REQUEST_PROMPT_TEMPLATE,
    _admit_planned_facility_relationships,
    _formalize_korean_summary,
    _parse_optional_project_key,
    _parse_plain_quantitative_observations,
    _parse_plain_source_facts,
    _parse_plain_semantic_relationships,
    _parse_plain_summary_details,
    _parse_plain_summary_response,
    _is_participation_only_responsibility,
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


def test_details_prompt_separates_events_from_projects_and_support_from_responsibility() -> None:
    from lineageweave.post_summary import (
        _DETAILS_REQUEST_PROMPT_TEMPLATE,
        _RELATIONS_REQUEST_PROMPT_TEMPLATE,
    )

    assert "meeting title into a project" in _DETAILS_REQUEST_PROMPT_TEMPLATE
    assert "lw_responsible_for" in _RELATIONS_REQUEST_PROMPT_TEMPLATE
    assert "lw_supports" in _RELATIONS_REQUEST_PROMPT_TEMPLATE


def test_details_prompt_prioritizes_loss_sensitive_semantics_before_large_lists() -> None:
    from lineageweave.post_summary import _DETAILS_REQUEST_PROMPT_TEMPLATE

    facts = _DETAILS_REQUEST_PROMPT_TEMPLATE.index("\nFACTS:\n")
    clues = _DETAILS_REQUEST_PROMPT_TEMPLATE.index("\nCLUES:\n")
    measurements = _DETAILS_REQUEST_PROMPT_TEMPLATE.index("\nMEASUREMENTS:\n")

    assert facts < clues
    assert facts < measurements


def test_summary_requires_imported_source_body() -> None:
    assert require_summary_source_body("  body  ") == "  body  "
    with pytest.raises(ValueError, match="source post body is empty"):
        require_summary_source_body("")


def test_summary_target_rejects_transport_padded_writing_state() -> None:
    class _Connection:
        async def fetchval(self, query: str, post_id: str) -> str:
            assert "source_detail_state_code" in query
            assert post_id == "post-1"
            return " w "

    with pytest.raises(ValueError, match=SUMMARY_TARGET_UNAVAILABLE):
        asyncio.run(require_summary_target(_Connection(), "post-1"))


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


def test_parses_allow_list_semantic_relationships_with_evidence() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"요약", "key_events":[], "semantic_relationships":['
        '{"subject_name":"설계팀", "subject_type":"team", '
        '"predicate_code":"org_unit_of", "object_name":"Demo Corp", '
        '"object_type":"organization", "evidence_text":"Demo Corp 설계팀", '
        '"confidence":0.93}]}'
    )
    assert summary is not None
    relation = summary.semantic_relationships[0]
    assert relation == SemanticRelationship(
        subject_name="설계팀",
        subject_type="team",
        predicate_code="org_unit_of",
        object_name="Demo Corp",
        object_type="organization",
        evidence_text="Demo Corp 설계팀",
        confidence=0.93,
    )


def test_parses_standard_profile_relation_for_industrial_why_path() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"요약", "key_events":[], "semantic_relationships":['
        '{"subject_name":"합성 공정", "subject_type":"industrial_process", '
        '"predicate_code":"prov_was_influenced_by", "object_name":"설비 상태", '
        '"object_type":"industrial_asset", "evidence_text":"합성 공정은 설비 상태의 영향을 받음", '
        '"confidence":0.8}]}'
    )
    assert summary is not None
    relation = summary.semantic_relationships[0]
    assert relation.subject_type == "industrial_process"
    assert relation.predicate_code == "prov_was_influenced_by"
    assert relation.object_type == "industrial_asset"


def test_plain_relation_parser_drops_unallowlisted_predicates() -> None:
    relations = _parse_plain_semantic_relationships(
        "RELATIONS:\n"
        "설계팀 | team | org_unit_of | Demo Corp | organization | Demo Corp 설계팀 | 0.9\n"
        "설계팀 | team | invented_relation | Demo Corp | organization | 추정 | 1"
    )
    assert len(relations) == 1
    assert relations[0].predicate_code == "org_unit_of"


def test_plain_relation_parser_keeps_explicit_responsibility_predicate() -> None:
    relations = _parse_plain_semantic_relationships(
        "RELATIONS:\n"
        "Prime Contractor | organization | lw_responsible_for | Highland HVDC | project | main contractor | 0.95\n"
        "Northwind Services | organization | lw_supports | Highland HVDC | project | installation support | 0.9"
    )
    assert [relation.predicate_code for relation in relations] == [
        "lw_responsible_for",
        "lw_supports",
    ]


def test_attendance_only_is_not_a_role_but_concrete_work_is() -> None:
    details = _parse_plain_summary_details(
        "ROLES:\n"
        "Synthetic attendee | 회의 참석 | person | Synthetic Works\n"
        "Synthetic operator | 회의 참석 및 기술 지원 | person | Synthetic Works\n"
        "PROJECTS:\nNONE\n"
    )
    assert details is not None
    assert [role.actor_name for role in details[0]] == ["Synthetic operator"]
    assert _is_participation_only_responsibility("meeting attendee")
    assert not _is_participation_only_responsibility("meeting attendance and installation support")


def test_json_attendance_only_is_not_a_role() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"요약", "key_events":[], "roles_and_responsibilities":['
        '{"actor_name":"Synthetic attendee","responsibility":"participant", "actor_type":"person"},'
        '{"actor_name":"Synthetic reviewer","responsibility":"도면 검토", "actor_type":"person"}]}'
    )
    assert summary is not None
    assert [role.actor_name for role in summary.roles_and_responsibilities] == ["Synthetic reviewer"]


def test_parses_explicit_five_w1h_evidence_with_source_phrase() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"요약", "key_events":[], '
        '"five_w1h_evidence":[{"slot_code":"when", "value_text":"3월 4일", '
        '"evidence_text":"3월 4일 현장 회의"}]}'
    )
    assert summary is not None
    assert summary.five_w1h_evidence[0].slot_code == "when"
    assert summary.five_w1h_evidence[0].evidence_text == "3월 4일 현장 회의"


def test_parses_source_grounded_quantitative_observations() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"요약", "quantitative_observations":['
        '{"measurement_type_code":"measurement_budget_amount",'
        '"label_text":"합성 최대 예산", "value_numeric":1700000000,'
        '"unit_code":"unit_krw", "raw_value_text":"약 17억원",'
        '"evidence_text":"합성 최대 예산은 부가세 포함 약 17억원",'
        '"qualifier_text":"VAT 포함·약"},'
        '{"measurement_type_code":"measurement_capacity",'
        '"label_text":"합성 탱크 용량", "value_numeric":5,'
        '"unit_code":"unit_kg", "quantity_numeric":2,'
        '"quantity_unit_code":"unit_tractor", "raw_value_text":"5kg",'
        '"evidence_text":"5kg 장비 2대"}]}'
    )
    assert summary is not None
    assert len(summary.quantitative_observations) == 2
    assert str(summary.quantitative_observations[0].value_numeric) == "1700000000"
    assert summary.quantitative_observations[1].quantity_numeric == 2


def test_plain_measurement_contract_keeps_each_atomic_capacity() -> None:
    observations = _parse_plain_quantitative_observations(
        "MEASUREMENTS:\n"
        "measurement_capacity | 합성 탱크 용량 | 5 | unit_kg | 2 | unit_tractor | 기준 | 5kg | 5kg 장비 2대\n"
        "measurement_capacity | 합성 탱크 용량 | 9 | unit_kg | 3 | unit_tractor | 기준 | 9kg | 9kg 장비 3대\n"
        "measurement_daily_capacity | 합성 일충전량 | 20 | unit_kg | NONE | NONE | 약·내외 | 약 20kg 내외 | 합성 일충전량이 약 20kg 내외"
    )
    assert [observation.value_numeric for observation in observations] == [5, 9, 20]
    assert [observation.quantity_numeric for observation in observations] == [2, 3, None]


def test_source_fact_contract_preserves_negation_and_year_basis() -> None:
    facts = _parse_plain_source_facts(
        "FACTS:\n"
        "fact_condition | 합성 사용 목적 | 판매 목적이 아님 | non_commercial | assertion_negated | NONE | NONE | NONE | 합성 장비는 판매 목적이 아님\n"
        "fact_condition | 합성 충전 수준 | 충전량이 낮음 | low_charging_volume | assertion_affirmed | NONE | NONE | NONE | 충전량이 낮다는 점을 고려\n"
        "fact_date | 합성 상담일 | 3월 14일 | NONE | assertion_affirmed | 2031-03-14 | day | 본문의 2031년 단서와 3월 14일 | 3월 14일 상담"
    )
    assert len(facts) == 3
    assert facts[0].assertion_code == "assertion_negated"
    assert facts[1].normalized_value_text == "low_charging_volume"
    assert facts[2].normalized_date.isoformat() == "2031-03-14"
    assert "2031년" in facts[2].normalization_evidence_text


def test_source_fact_contract_accepts_broad_question_dimensions() -> None:
    facts = _parse_plain_source_facts(
        "FACTS:\n"
        "fact_organization | 소속 조직 | Synthetic Works | NONE | assertion_affirmed | NONE | NONE | NONE | Synthetic Works가 담당함\n"
        "fact_industrial_asset | 설비 | 합성 장비 | NONE | assertion_affirmed | NONE | NONE | NONE | 합성 장비를 사용함\n"
        "fact_normative | 준수 조건 | 승인 필요 | NONE | assertion_affirmed | NONE | NONE | NONE | 승인 필요 조건을 명시함\n"
        "fact_result | 결과 | 점검 완료 | NONE | assertion_affirmed | NONE | NONE | NONE | 점검 완료로 기록됨\n"
        "fact_next_step | 다음 단계 | 재검토 | NONE | assertion_unknown | NONE | NONE | NONE | 재검토 예정 여부는 확인 필요함"
    )
    assert [fact.fact_type_code for fact in facts] == [
        "fact_organization",
        "fact_industrial_asset",
        "fact_normative",
        "fact_result",
        "fact_next_step",
    ]


def test_parses_plain_summary_evidence_section() -> None:
    details = _parse_plain_summary_details(
        "ROLES:\nNONE\nPROJECTS:\nNONE\nEVIDENCE:\n"
        "where | 제3공장 | 제3공장에서 협의했다"
    )
    assert details is not None
    assert details[3][0].value_text == "제3공장"


def test_parses_event_clues_without_inventing_a_relationship() -> None:
    details = _parse_plain_summary_details(
        "ROLES:\nSynthetic operator | 점검 | person | Synthetic Works\n"
        "PROJECTS:\nNONE\n"
        "CLUES:\n"
        "0 | clue_actor | Synthetic operator | Synthetic operator | NONE | assertion_affirmed | 점검 담당자로 명시됨\n"
        "0 | clue_cause | 설비 상태 확인 필요 | NONE | NONE | assertion_unknown | 상태 확인이 필요하다고 기재됨\n"
    )
    assert details is not None
    assert len(details[4]) == 2
    assert details[4][0].clue_type_code == "clue_actor"
    assert details[4][1].assertion_code == "assertion_unknown"


def test_json_key_event_evidence_and_clue_are_retained() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"합성 요약", "key_events":['
        '{"event_text":"합성 점검", "evidence_text":"합성 설비를 점검함"}],'
        '"event_clues":[{"event_index":0,"clue_type_code":"clue_result",'
        '"clue_text":"점검 결과 기록", "evidence_text":"점검 결과를 기록함"}]}'
    )
    assert summary is not None
    assert summary.key_event_details[0].evidence_text == "합성 설비를 점검함"
    assert summary.event_clues[0].event_index == 0


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


def test_software_agent_actor_is_not_forced_into_a_person_slot() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"자동화가 점검했습니다.", "key_events":[], '
        '"roles_and_responsibilities":[{"actor_name":"배치 스케줄러", '
        '"responsibility":"점검 실행", "actor_type":"software_agent", '
        '"affiliated_organization_name":null}]}'
    )
    assert summary is not None
    assert summary.roles_and_responsibilities[0].actor_type_code == "prov_software_agent"


def test_generic_business_unit_label_is_not_cataloged_as_a_team() -> None:
    content = (
        '{"korean_summary": "요약", "key_events": [], '
        '"roles_and_responsibilities": [{"actor_name": "사업부", "responsibility": "검토", '
        '"actor_type": "team", "affiliated_organization_name": null}]}'
    )
    summary = parse_summary_response(content)
    assert summary is not None
    assert summary.roles_and_responsibilities == ()


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
        elif "Write exactly one section marker" in prompt:
            content = (
                "RELATIONS:\n"
                "Synthetic base release | temporal_entity | time_before | "
                "Synthetic multi-stage release | temporal_entity | "
                "base release came first | 0.98"
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

    assert summary.korean_summary == "본문 근거 요약입니다."
    assert summary.key_events == ("후속 확인",)
    assert len(observed) == 3
    assert all(payload["mode"] == "auto" for payload in observed)
    assert "KEY EVENTS" in observed[0]["messages"][0]["content"]
    details_prompt = observed[1]["messages"][0]["content"]
    assert "source_process_unit_name are PU/business-unit hints only" in details_prompt
    assert "must never be" in details_prompt
    assert "sales-pool/order-pool value" in details_prompt
    assert "source_sales_pool_name are sales-pool/order-pool hints only" in details_prompt
    assert "PU/business-unit value" in details_prompt
    relations_prompt = observed[2]["messages"][0]["content"]
    assert "time_before" in relations_prompt
    assert "earlier temporal entity" in relations_prompt
    assert "do not label a product name as temporal_entity" in relations_prompt.casefold()
    assert "different product family in a nearby list is not a substitute" in " ".join(
        relations_prompt.split()
    )
    assert "lw_plans_to_operate" in relations_prompt
    assert "same supporting phrase must name both" in relations_prompt
    assert "matching PROJECTS row" in relations_prompt
    assert "separate extraction pass" in relations_prompt
    assert "Do not suppress an explicit source relation" in relations_prompt
    assert summary.roles_and_responsibilities[0].actor_name == "Jordan Hale"
    assert summary.project_mentions[0].canonical_name == "hvdc-pilot"
    assert summary.semantic_relationships == (
        SemanticRelationship(
            subject_name="Synthetic base release",
            subject_type="temporal_entity",
            predicate_code="time_before",
            object_name="Synthetic multi-stage release",
            object_type="temporal_entity",
            evidence_text="base release came first",
            confidence=0.98,
        ),
    )


def _planned_facility_details(
    *,
    actor_type: str = "organization",
    roles: str | None = None,
    projects: str = (
        "Aurora Charging Hub | Aurora Charging Hub | Aurora Charging Hub plan | 0.95"
    ),
    object_type: str = "industrial_asset",
    evidence: str = "Synthetic Utility plans to operate Aurora Charging Hub",
) -> str:
    roles = roles or f"Synthetic Utility | 운영 계획 담당 | {actor_type} | NONE"
    return (
        f"ROLES:\n{roles}\nPROJECTS:\n{projects}\nRELATIONS:\n"
        f"Synthetic Utility | {actor_type} | lw_plans_to_operate | "
        f"Aurora Charging Hub | {object_type} | {evidence} | 0.93"
    )


def _summarize_with_details(monkeypatch, details: str):
    responses = iter(
        (
            {"choices": [{"message": {"content": "합성 요약\nKEY EVENTS: 운영 계획"}}]},
            {"choices": [{"message": {"content": details}}]},
            {"choices": [{"message": {"content": details}}]},
        )
    )
    monkeypatch.setattr(
        "lineageweave.post_summary.post_json",
        lambda *args, **kwargs: next(responses),
    )

    return ContextualOrchestratorPostSummaryClient(
        "https://orchestrator.test", "token"
    ).summarize("Synthetic plan", "Synthetic Utility plans to operate Aurora Charging Hub")


@pytest.mark.parametrize("object_type", ("industrial_asset", "place"))
@pytest.mark.parametrize("actor_type", ("organization", "team"))
def test_summary_admits_explicit_planned_facility_relation_with_project_backing(
    monkeypatch, actor_type: str, object_type: str
) -> None:
    summary = _summarize_with_details(
        monkeypatch,
        _planned_facility_details(actor_type=actor_type, object_type=object_type),
    )

    assert len(summary.semantic_relationships) == 1
    relation = summary.semantic_relationships[0]
    assert relation.subject_name == "Synthetic Utility"
    assert relation.subject_type == actor_type
    assert relation.predicate_code == "lw_plans_to_operate"
    assert relation.object_name == "Aurora Charging Hub"
    assert relation.object_type == object_type
    assert relation.evidence_text == "Synthetic Utility plans to operate Aurora Charging Hub"
    assert relation.confidence == 0.93


@pytest.mark.parametrize(
    "details",
    (
        pytest.param(
            _planned_facility_details(projects="NONE"),
            id="missing-project-backing",
        ),
        pytest.param(
            _planned_facility_details(roles="NONE"),
            id="missing-role-actor",
        ),
        pytest.param(
            _planned_facility_details(evidence="Aurora Charging Hub plan"),
            id="evidence-missing-actor",
        ),
        pytest.param(
            _planned_facility_details(
                evidence="Synthetic Utility will manage Aurora Charging Hub"
            ),
            id="evidence-not-in-source",
        ),
        pytest.param(
            _planned_facility_details(object_type="project"),
            id="wrong-facility-type",
        ),
    ),
)
def test_summary_drops_planned_facility_relation_when_admission_evidence_is_missing(
    monkeypatch, details: str
) -> None:
    assert _summarize_with_details(monkeypatch, details).semantic_relationships == ()


def test_planned_facility_admission_normalizes_unicode_equivalent_actor_names() -> None:
    relationship = SemanticRelationship(
        subject_name="Synthetic Utility",
        subject_type="organization",
        predicate_code="lw_plans_to_operate",
        object_name="Aurora Charging Hub",
        object_type="industrial_asset",
        evidence_text="Synthetic Utility plans to operate Aurora Charging Hub",
        confidence=0.93,
    )

    assert _admit_planned_facility_relationships(
        (relationship,),
        (
            RoleResponsibility(
                "Ｓｙｎｔｈｅｔｉｃ Ｕｔｉｌｉｔｙ",
                "운영 계획 담당",
                ACTOR_TYPE_ORGANIZATION,
            ),
        ),
        (
            ProjectMention(
                "Aurora Charging Hub",
                "Aurora Charging Hub",
                "Aurora Charging Hub plan",
                0.95,
            ),
        ),
        relationship.evidence_text,
    ) == (relationship,)


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


def test_summary_relation_parse_failure_does_not_expose_provider_response(
    monkeypatch,
) -> None:
    """A malformed dedicated relation response fails closed without disclosure."""
    responses = iter(
        (
            {
                "choices": [
                    {"message": {"content": "본문 근거 요약\nKEY EVENTS: 후속 확인"}}
                ]
            },
            {
                "choices": [
                    {"message": {"content": "ROLES:\nNONE\nPROJECTS:\nNONE"}}
                ]
            },
            {
                "choices": [
                    {"message": {"content": "provider-secret-and-gateway-prompt"}}
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
        match="summary relation response did not match the required format",
    ) as exc_info:
        ContextualOrchestratorPostSummaryClient(
            "https://orchestrator.test", "token"
        ).summarize("Synthetic title", "Synthetic body")

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
    assert unrelated == ((), (), (), (), ())


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


def test_summary_uses_formal_nida_endings_and_drops_technical_acronym_actor() -> None:
    assert _formalize_korean_summary("이 글에서 별도의 의사결정이나 다음 조치는 본문에 없음.") == (
        "이 글에서 별도의 의사결정이나 다음 조치는 본문에 없습니다."
    )
    details = _parse_plain_summary_details(
        "ROLES:\n"
        "HSWG | 적용 방식 | organization | NONE\n"
        "PROJECTS:\nNONE",
        post_body="원적외선 건조방식(Heat Spreader Wave Guide, HSWG)을 적용했습니다.",
    )
    assert details is not None
    assert details[0] == ()


def test_summary_formalizes_ida_endings_without_duplicate_copula() -> None:
    assert _formalize_korean_summary("프로젝트는 진행 중이다. 일정은 다음 달 예정이다.") == (
        "프로젝트는 진행 중입니다. 일정은 다음 달 예정입니다."
    )


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
