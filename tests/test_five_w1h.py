"""5W1H slots fail-closed and answer only from authorized facts."""

from lineageweave.five_w1h import (
    answer_lineage_question,
    assemble_five_w1h_slots,
    classify_lineage_question,
    empty_slot_next_action,
    slot_ontology_iris,
    slots_payload,
)


def test_who_what_when_where_come_from_authorized_facts_only() -> None:
    slots = assemble_five_w1h_slots(
        roles=[
            {
                "actor_name": "Ada West",
                "actor_type_code": "prov_person",
                "affiliated_organization_name": "Demo Corp",
            },
            {
                "actor_name": "당사",
                "actor_type_code": "prov_organization",
                "affiliated_organization_name": None,
            },
        ],
        key_events=["현장 방문", "범위 논의"],
        created_at="2026-01-01T00:00:00Z",
        counterparty_names=["Northridge Grid"],
    )
    assert slots["who"] == ("Ada West", "당사")
    assert slots["what"] == ("현장 방문", "범위 논의")
    assert slots["when"] == ("2026-01-01",)
    assert slots["where"] == ("Demo Corp", "Northridge Grid")
    assert slots["why"] == ()
    assert slots["how"] == ()


def test_missing_why_and_how_stay_empty() -> None:
    slots = assemble_five_w1h_slots(roles=[], key_events=[], created_at=None)
    payload = slots_payload(slots)
    by_code = {row["slot_code"]: row for row in payload}
    assert by_code["why"]["values"] == []
    assert by_code["why"]["empty_next_action"] == "이 사건의 왜가 아직 없습니다"
    assert by_code["how"]["empty_next_action"] == "이 사건의 어떻게가 아직 없습니다"
    assert empty_slot_next_action("who", "when") == "이 사건의 누가/언제가 아직 없습니다"


def test_what_falls_back_to_authorized_lineage_titles_not_invented_prose() -> None:
    slots = assemble_five_w1h_slots(
        roles=[],
        key_events=[],
        created_at=None,
        lineage_node_labels=["Public post", "Linked post"],
    )
    assert slots["what"] == ("Public post", "Linked post")


def test_who_slot_binds_ontology_iris_from_the_semantic_layer() -> None:
    iris = slot_ontology_iris("who")
    assert any(iri.endswith("RoleActorPerson") or "Person" in iri for iri in iris)
    assert slot_ontology_iris("why") == ()


def test_five_w1h_questions_answer_from_slots_never_guessed_prose() -> None:
    slots = assemble_five_w1h_slots(
        roles=[{"actor_name": "Ada West", "affiliated_organization_name": "Demo Corp"}],
        key_events=["현장 방문"],
        created_at="2026-01-01T12:00:00Z",
    )
    who = answer_lineage_question("누가 관련되었나요?", slots)
    assert who["grounded"] is True
    assert who["values"] == ["Ada West"]
    why = answer_lineage_question("왜 이 일이 일어났나요?", slots)
    assert why["grounded"] is False
    assert why["empty_next_action"] == "이 사건의 왜가 아직 없습니다"
    unknown = answer_lineage_question("Invent a theta for Demo Corp", slots)
    assert unknown["grounded"] is False
    assert "근거할 수 있는 질문" in str(unknown["empty_next_action"])


def test_what_happened_classifies_as_lineage_what() -> None:
    assert classify_lineage_question("What happened between these events?") == "what_happened"
    assert classify_lineage_question("누가 관련됐나요?") == "who"
