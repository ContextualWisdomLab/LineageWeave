from datetime import datetime, timezone

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
        created_at=datetime(2026, 8, 19, 9, 30, tzinfo=timezone.utc),
        counterparties=["Northwind Labs"],
    )

    assert [item["text"] for item in slots["who"]] == ["Ada West"]
    assert [item["text"] for item in slots["what"]] == ["검사 일정 확정"]
    assert slots["when"][0]["text"].startswith("2026-08-19T09:30:00")
    assert {item["text"] for item in slots["where"]} == {"Demo Corp", "Northwind Labs"}
    assert slots["why"] == []
    assert slots["how"] == []


def test_five_w1h_uses_visible_lineage_title_only_as_what_fallback() -> None:
    slots = assemble_five_w1h_slots(
        roles=[],
        key_events=[],
        created_at=None,
        lineage_node_labels=["검사 후속 조치"],
    )

    payload = slots_payload(slots)
    what = next(row for row in payload if row["slot_code"] == "what")
    why = next(row for row in payload if row["slot_code"] == "why")
    assert what["values"][0]["source"] == "post_lineage_edge"
    assert why["values"] == []
    assert why["empty_next_action_code"] == "inspect_source_body_or_related_posts"
