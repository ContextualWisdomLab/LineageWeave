import ast
from pathlib import Path

from lineageweave.five_w1h import assemble_five_w1h_slots, slots_payload


FIVE_W1H_SOURCE_PATH = Path(__file__).parents[1] / "lineageweave" / "five_w1h.py"
FIVE_W1H_INGESTION_SOURCE_PATH = (
    Path(__file__).parents[1] / "backend" / "app" / "five_w1h_ingestion.py"
)
BACKEND_MAIN_SOURCE_PATH = Path(__file__).parents[1] / "backend" / "app" / "main.py"
FORBIDDEN_FIVE_W1H_IDENTIFIERS = {
    "annotations",
    "codes",
    "event",
    "item",
    "key",
    "name",
    "result",
    "role",
    "roles",
    "seen",
    "slot",
    "slots",
    "source",
    "text",
    "value",
    "values",
}
REQUIRED_FIVE_W1H_IDENTIFIERS = {
    "actor_type_code",
    "counterparty_name",
    "evidence_claim",
    "evidence_source_code",
    "evidence_slot_value",
    "evidence_value_key",
    "five_w1h_slots",
    "key_event_text",
    "ontology_annotation_map",
    "ontology_codes",
    "post_summary_role",
    "post_summary_roles",
    "seen_value_keys",
    "slot_code",
    "slot_values",
    "unique_slot_values",
}


def test_five_w1h_uses_evidence_slot_specific_owned_identifiers() -> None:
    """Keep internal names aligned with the evidence-only 5W1H projection."""
    five_w1h_tree = ast.parse(FIVE_W1H_SOURCE_PATH.read_text(encoding="utf-8"))
    owned_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(five_w1h_tree)
        if isinstance(syntax_node, ast.Name)
    }
    owned_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(five_w1h_tree)
        if isinstance(syntax_node, ast.arg)
    )

    assert not (FORBIDDEN_FIVE_W1H_IDENTIFIERS & owned_identifiers)
    assert REQUIRED_FIVE_W1H_IDENTIFIERS <= owned_identifiers

    ingestion_tree = ast.parse(
        FIVE_W1H_INGESTION_SOURCE_PATH.read_text(encoding="utf-8")
    )
    assembly_call = next(
        syntax_node
        for syntax_node in ast.walk(ingestion_tree)
        if isinstance(syntax_node, ast.Call)
        and isinstance(syntax_node.func, ast.Name)
        and syntax_node.func.id == "assemble_five_w1h_slots"
    )
    assembly_keywords = {keyword.arg for keyword in assembly_call.keywords}
    assert "roles" not in assembly_keywords
    assert "post_summary_roles" in assembly_keywords

    ingestion_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(ingestion_tree)
        if isinstance(syntax_node, ast.Name)
    }
    ingestion_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(ingestion_tree)
        if isinstance(syntax_node, ast.arg)
    )
    assert not (
        {"conn", "linked", "row", "rows", "slots", "summary"} & ingestion_identifiers
    )
    assert {
        "database_connection",
        "five_w1h_slots",
        "linked_post_row",
        "linked_post_rows",
        "linked_post_ids",
        "persisted_summary",
    } <= ingestion_identifiers

    backend_main_tree = ast.parse(BACKEND_MAIN_SOURCE_PATH.read_text(encoding="utf-8"))
    endpoint_function = next(
        syntax_node
        for syntax_node in backend_main_tree.body
        if isinstance(syntax_node, ast.AsyncFunctionDef)
        and syntax_node.name == "read_post_five_w1h"
    )
    endpoint_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(endpoint_function)
        if isinstance(syntax_node, ast.Name)
    }
    endpoint_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(endpoint_function)
        if isinstance(syntax_node, ast.arg)
    )
    assert not ({"conn", "row"} & endpoint_identifiers)
    assert {"database_connection", "visible_post_row"} <= endpoint_identifiers


def test_five_w1h_keeps_persisted_evidence_and_leaves_unsupported_slots_empty() -> None:
    five_w1h_slots = assemble_five_w1h_slots(
        post_summary_roles=[
            {
                "actor_name": "Ada West",
                "actor_type_code": "prov_person",
                "affiliated_organization_name": "Demo Corp",
            }
        ],
        key_events=["검사 일정 확정"],
        counterparties=["Northwind Labs"],
    )

    assert [slot_value["text"] for slot_value in five_w1h_slots["who"]] == ["Ada West"]
    assert [slot_value["text"] for slot_value in five_w1h_slots["what"]] == [
        "검사 일정 확정"
    ]
    # "when" has no persisted evidence of the narrated event's own time --
    # source_post.created_at is the record's filing time, a different
    # PROV-O category (prov:generatedAtTime), and must not be shown here
    # as if it answered "when did this happen" (see five_w1h.py).
    assert five_w1h_slots["when"] == []
    assert {slot_value["text"] for slot_value in five_w1h_slots["where"]} == {
        "Demo Corp",
        "Northwind Labs",
    }
    assert five_w1h_slots["why"] == []
    assert five_w1h_slots["how"] == []


def test_five_w1h_uses_visible_lineage_title_only_as_what_fallback() -> None:
    five_w1h_slots = assemble_five_w1h_slots(
        post_summary_roles=[],
        key_events=[],
        lineage_node_labels=["검사 후속 조치"],
    )

    five_w1h_payload = slots_payload(five_w1h_slots)
    what_slot = next(
        slot_payload
        for slot_payload in five_w1h_payload
        if slot_payload["slot_code"] == "what"
    )
    why_slot = next(
        slot_payload
        for slot_payload in five_w1h_payload
        if slot_payload["slot_code"] == "why"
    )
    assert what_slot["values"][0]["source"] == "post_lineage_edge"
    assert why_slot["values"] == []
    assert why_slot["empty_next_action_code"] == "inspect_source_body_or_related_posts"


def test_five_w1h_uses_only_explicit_claims_for_missing_dimensions() -> None:
    five_w1h_slots = assemble_five_w1h_slots(
        post_summary_roles=[],
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
    assert five_w1h_slots["when"][0]["source"] == "post_summary_five_w1h"
    assert five_w1h_slots["when"][0]["evidence_text"] == "3월 4일 현장 회의"
    assert five_w1h_slots["how"][0]["text"] == "화상 회의로"
    assert five_w1h_slots["where"] == []
