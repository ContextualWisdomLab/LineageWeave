from lineageweave.five_w1h import assemble_five_w1h_slots, slots_payload


def test_five_w1h_keeps_persisted_evidence_and_leaves_unsupported_slots_empty() -> None:
    slots = assemble_five_w1h_slots(
        roles=[
            {
                "actor_name": "Ada West",
                "actor_type_code": "prov_person",
                "affiliated_organization_name": "Demo Corp",
            }
        ],
        key_events=["검사 일정 확정"],
        counterparties=["Northwind Labs"],
    )

    assert [item["text"] for item in slots["who"]] == ["Ada West"]
    assert [item["text"] for item in slots["what"]] == ["검사 일정 확정"]
    # "when" has no persisted evidence of the narrated event's own time --
    # source_post.created_at is the record's filing time, a different
    # PROV-O category (prov:generatedAtTime), and must not be shown here
    # as if it answered "when did this happen" (see five_w1h.py).
    assert slots["when"] == []
    assert {item["text"] for item in slots["where"]} == {"Demo Corp", "Northwind Labs"}
    assert slots["why"] == []
    assert slots["how"] == []


def test_five_w1h_uses_visible_lineage_title_only_as_what_fallback() -> None:
    slots = assemble_five_w1h_slots(
        roles=[],
        key_events=[],
        lineage_node_labels=["검사 후속 조치"],
    )

    payload = slots_payload(slots)
    what = next(row for row in payload if row["slot_code"] == "what")
    why = next(row for row in payload if row["slot_code"] == "why")
    assert what["values"][0]["source"] == "post_lineage_edge"
    assert why["values"] == []
    assert why["empty_next_action_code"] == "inspect_source_body_or_related_posts"


def test_five_w1h_uses_only_explicit_claims_for_missing_dimensions() -> None:
    slots = assemble_five_w1h_slots(
        roles=[],
        key_events=[],
        evidence_claims=[
            {
                "slot_code": "when",
                "value_text": "2026년 3월 4일",
                "evidence_text": "3월 4일 현장 회의",
            },
            {
                "slot_code": "how",
                "value_text": "화상 회의로",
                "evidence_text": "화상으로 협의했다",
            },
        ],
    )
    assert slots["when"][0]["source"] == "post_summary_five_w1h"
    assert slots["when"][0]["evidence_text"] == "3월 4일 현장 회의"
    assert slots["how"][0]["text"] == "화상 회의로"
    assert slots["where"] == []


def test_five_w1h_when_slot_carries_a_resolved_absolute_date() -> None:
    """A relative "when" phrase (올해 말) keeps its original text and gains a
    resolved_date_text field; the "how" slot has no such field since
    resolution only applies to "when" (see post_summary.py FiveW1HEvidence).
    """
    slots = assemble_five_w1h_slots(
        roles=[],
        key_events=[],
        evidence_claims=[
            {
                "slot_code": "when",
                "value_text": "올해 말까지",
                "evidence_text": "올해 말까지 정비 작업을 완료할 계획",
                "resolved_date_text": "2026-12",
            },
            {
                "slot_code": "how",
                "value_text": "지정 협력업체를 통해",
                "evidence_text": "지정 협력업체를 통해 정비 작업을 진행",
                "resolved_date_text": None,
            },
        ],
    )
    assert slots["when"][0]["text"] == "올해 말까지"
    assert slots["when"][0]["resolved_date_text"] == "2026-12"
    assert "resolved_date_text" not in slots["how"][0]
