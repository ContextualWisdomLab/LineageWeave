"""Exercise the end-to-end in-memory product graph built from realistic direct-query rows."""

from __future__ import annotations

import base64

import lineageweave as lw


def _row(
    guid: str,
    document_no: str,
    thread: str,
    corp: str,
    pu: str,
    person: str,
    date: str,
    sequence: int,
    *,
    title: str = "Shared commercial event lineage",
    content: str = "ordinary text",
) -> dict[str, str]:
    """Return one source-shaped row without retaining a real export value."""
    return {
        "guid_field": guid,
        "docnosub_field": document_no,
        "acthguid_field": thread,
        "aedat_field": date,
        "aezet_field": "10:00:00",
        "erdat_field": date,
        "erzet_field": "09:00:00",
        "title_field": title,
        "voctp_field": "opened",
        "dtsts_field": "active",
        "ststs_field": "open",
        "grade_field": "A",
        "bukrs_field": corp,
        "pucode_field": pu,
        "ernam_field": person,
        "aenam_field": person,
        "userid_field": person.casefold(),
        "content_prefix": content,
        "content_bytes": str(len(content)),
        "artifact_reference": "false",
        "source_row_number": str(sequence),
    }


def test_build_and_filter_product_payload_preserves_evidence_and_cross_unit_knowledge() -> None:
    """Build observed/inferred graphs and filter them to an actor's corp/PU authorization scope."""
    png = base64.b64encode(b"\x89PNG\r\n\x1a\nfixture").decode("ascii")
    rows = [
        _row("ROW-1", "DOC-1", "THREAD-1", "CORP_A", "PU_A", "Ana", "2026-01-01", 1, content=f"data:image/png;base64,{png}"),
        _row("ROW-2", "DOC-1", "THREAD-1", "CORP_A", "PU_B", "Bo", "2026-01-02", 2),
        _row("ROW-3", "DOC-2", "THREAD-1", "CORP_B", "PU_A", "Cy", "2026-01-03", 3),
        _row("ROW-4", "DOC-3", "THREAD-2", "CORP_A", "PU_A", "Dee", "2026-01-04", 4),
    ]

    keyman_requests: list[dict[str, object]] = []
    product_requests: list[dict[str, object]] = []

    def keyman_transport(request: dict[str, object]) -> dict[str, object]:
        """Return deliberate two-sided worker results for the bounded product flow."""
        keyman_requests.append(request)
        if request["extract_side"] == "our_side":
            return {"our_side": [{"person_name": "Ana", "org_name": "Org A"}], "model": "fixture"}
        return {"counterpart_side": [{"person_name": "Bo", "org_name": "Org B"}], "model": "fixture"}

    def product_transport(request: dict[str, object]) -> dict[str, object]:
        """Return task-specific product enrichments without using the Keyman adapter."""
        product_requests.append(request)
        if request["task"] == "entity_role_classification":
            return {"entity_role": "시장", "confidence": 0.8}
        if request["task"] == "roles_and_responsibilities":
            return {
                "roles_and_responsibilities": [
                    {
                        "actor_type": "organization",
                        "actor_name": "Fixture Authority",
                        "role": "승인 기관",
                        "responsibility": "승인",
                    }
                ]
            }
        if request["task"] == "appointment_extract":
            return {"appointments": []}
        if request["task"] == "customer_master":
            return {"accounts": [], "edges": []}
        raise AssertionError(f"unexpected product task: {request['task']}")

    payload = lw.build_payload(
        rows,
        enum_values=lw.load_common_enum_values(lw.DEFAULT_ENUM_ROWS),
        keyman_transport=keyman_transport,
        product_transport=product_transport,
        keyman_limit=2,
    )
    relations = {edge["relation"] for edge in payload["edges"]}
    kg_relations = {edge["relation"] for edge in payload["knowledge_graph"]["edges"]}
    assert {"row_successor", lw.SHARED_THREAD_RELATION} <= relations
    assert {"cross_pu_transaction", "cross_corp_same_pu_thread"} <= kg_relations
    assert any(edge["evidence_status"] == lw.EVIDENCE_INFERRED for edge in payload["edges"])
    assert all(
        edge["relation"] not in lw.TRANSITION_RELATIONS
        for edge in payload["edges"]
        if edge["evidence_status"] != lw.EVIDENCE_OBSERVED
    )
    assert payload["metadata"]["keyman_llm_documents"] == 2
    assert payload["metadata"]["content_manifest"]["inline_image_candidate_rows"] == 1
    assert payload["analytics"]["documents_with_multiple_rows"] == 1
    assert payload["knowledge_graph"]["nodes"]
    assert all("extract_side" in request for request in keyman_requests)
    assert {request["task"] for request in product_requests} == {
        "entity_role_classification",
        "roles_and_responsibilities",
        "appointment_extract",
        "customer_master",
    }

    filtered = lw.filter_payload_for_actor(
        payload,
        {"account_id": "account-1", "corp_code": "CORP_A", "pu_code": "PU_A", "roles": ["admin"]},
    )
    visible_documents = {node["document_no"] for node in filtered["nodes"] if node["type"] == "document"}
    assert visible_documents == {"DOC-1", "DOC-3"}
    assert filtered["metadata"]["authorization_boundary"] == "filtered_for_verified_actor"
    assert all("DOC-2" not in node.get("document_nos", []) for node in filtered["knowledge_graph"]["nodes"])


def test_select_keyman_documents_supports_non_overlapping_live_batches() -> None:
    """Advance a bounded live Keyman batch without selecting the newest documents again."""
    documents = [
        {"document_no": "DOC-1", "last_row_ts": "2026-01-01"},
        {"document_no": "DOC-2", "last_row_ts": "2026-01-02"},
        {"document_no": "DOC-3", "last_row_ts": "2026-01-03"},
        {"document_no": "DOC-4", "last_row_ts": "2026-01-04"},
    ]

    assert [item["document_no"] for item in lw.select_keyman_documents(documents, 2)] == ["DOC-4", "DOC-3"]
    assert [item["document_no"] for item in lw.select_keyman_documents(documents, 2, offset=2)] == ["DOC-2", "DOC-1"]


def test_knowledge_graph_scope_filter_removes_hidden_shared_context_and_evidence() -> None:
    """Keep shared KG entities useful without exposing an inaccessible document or evidence id."""
    graph = {
        "nodes": [
            {"id": "kg:document:DOC-1", "type": "document", "document_no": "DOC-1"},
            {"id": "kg:document:DOC-2", "type": "document", "document_no": "DOC-2"},
            {
                "id": "kg:person:shared",
                "type": "person",
                "document_nos": ["DOC-1", "DOC-2"],
                "document_no": "DOC-2",
            },
            {"id": "kg:topic:unscoped", "type": "topic"},
            {"id": "kg:person:hidden", "type": "person", "document_nos": ["DOC-2"]},
        ],
        "edges": [
            {"source": "kg:document:DOC-1", "target": "kg:person:shared", "evidence_id": "DOC-1"},
            {"source": "kg:document:DOC-1", "target": "kg:topic:unscoped"},
            {"source": "kg:document:DOC-1", "target": "kg:person:shared", "evidence_id": "DOC-2"},
            {"source": "kg:document:DOC-1", "target": "kg:person:hidden", "evidence_id": "DOC-2"},
        ],
    }

    filtered = lw._filter_knowledge_graph_for_documents(graph, {"DOC-1"}, {"DOC-1", "ROW-1"})
    nodes = {node["id"]: node for node in filtered["nodes"]}

    assert set(nodes) == {"kg:document:DOC-1", "kg:person:shared", "kg:topic:unscoped"}
    assert nodes["kg:person:shared"]["document_nos"] == ["DOC-1"]
    assert "document_no" not in nodes["kg:person:shared"]
    assert filtered["edges"] == [
        {"source": "kg:document:DOC-1", "target": "kg:person:shared", "evidence_id": "DOC-1"},
        {"source": "kg:document:DOC-1", "target": "kg:topic:unscoped"},
    ]


def test_structured_llm_unwrap_preserves_only_object_shaped_judge_results() -> None:
    """Normalize direct, enveloped, and malformed judge replies without fabricating a score."""
    assert lw._unwrap_structured_llm_object(None) == {}
    direct = {"verdict": "pass", "rationale": "direct"}
    assert lw._unwrap_structured_llm_object(direct) is direct
    assert lw._unwrap_structured_llm_object({"content": {"score": "fail"}}) == {"score": "fail"}
    assert lw._unwrap_structured_llm_object({"content": ""}) == {"content": ""}
    assert lw._unwrap_structured_llm_object(
        {"choices": [{"message": {"content": '{"verdict":"pass"}'}}]}
    ) == {"verdict": "pass"}
    assert lw._unwrap_structured_llm_object(
        {"answer": 'Explanation before {"score":"fail"} after'}
    ) == {"score": "fail"}
    assert lw._unwrap_structured_llm_object({"answer": "no structured verdict"}) == {
        "verdict": "no structured verdict",
        "rationale": "no structured verdict",
    }
    assert lw._unwrap_structured_llm_object({"answer": "prefix {not json} suffix"}) == {
        "verdict": "prefix {not json} suffix",
        "rationale": "prefix {not json} suffix",
    }
    assert lw._unwrap_structured_llm_object({"answer": "[\"not\", \"an object\"]"}) == {
        "verdict": "[\"not\", \"an object\"]",
        "rationale": "[\"not\", \"an object\"]",
    }
