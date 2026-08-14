"""Drive the shipped DAG builder on representative extracted rows.

These tests call ``build_payload`` / ``make_lineage_edge`` — the real
entry points used by the CLI — not a re-implemented graph.
"""

from __future__ import annotations

import pytest

import lineageweave as lw


def _row(
    *,
    guid: str,
    docno: str,
    acthguid: str,
    date: str,
    time: str = "10:00:00",
    title: str | None = None,
    source_row_number: str = "1",
) -> dict[str, str | None]:
    return {
        "guid_field": guid,
        "docnosub_field": docno,
        "acthguid_field": acthguid,
        "aedat_field": date,
        "aezet_field": time,
        "erdat_field": date,
        "erzet_field": time,
        "title_field": title,
        "voctp_field": None,
        "dtsts_field": None,
        "ststs_field": "Z",
        "grade_field": None,
        "bukrs_field": "CWL1",
        "pucode_field": "PU01",
        "ernam_field": "fixture-user",
        "aenam_field": "fixture-user",
        "userid_field": "fixture-user",
        "source_row_number": source_row_number,
    }


def test_same_document_rows_form_observed_successor() -> None:
    payload = lw.build_payload(
        [
            _row(guid="g1", docno="D1", acthguid="T1", date="2026-01-01", source_row_number="1"),
            _row(guid="g2", docno="D1", acthguid="T1", date="2026-01-02", source_row_number="2"),
        ]
    )
    successors = [edge for edge in payload["edges"] if edge["relation"] == "row_successor"]
    assert len(successors) == 1
    assert successors[0]["source"] == "row:g1"
    assert successors[0]["target"] == "row:g2"
    assert successors[0]["evidence_status"] == lw.EVIDENCE_OBSERVED
    assert successors[0]["relation"] in lw.TRANSITION_RELATIONS
    assert payload["metadata"]["row_count"] == 2
    assert payload["metadata"]["document_count"] == 1
    assert payload["metadata"]["thread_count"] == 1
    types = {node["type"] for node in payload["nodes"]}
    assert types == {"document", "row"}


def test_same_thread_documents_form_inferred_non_temporal_relatedness() -> None:
    payload = lw.build_payload(
        [
            _row(guid="g1", docno="D2", acthguid="T1", date="2026-01-01", title="alpha note"),
            _row(guid="g2", docno="D1", acthguid="T1", date="2026-01-03", title="beta note"),
            _row(guid="g3", docno="D3", acthguid="T1", date="2026-01-02", title="gamma note"),
        ]
    )
    related = [edge for edge in payload["edges"] if edge["relation"] == lw.SHARED_THREAD_RELATION]
    assert {(edge["source"], edge["target"]) for edge in related} == {
        ("doc:D1", "doc:D2"),
        ("doc:D1", "doc:D3"),
        ("doc:D2", "doc:D3"),
    }
    assert all(edge["evidence_status"] == lw.EVIDENCE_INFERRED for edge in related)
    assert all(edge["relation"] not in lw.TRANSITION_RELATIONS for edge in related)
    assert all(edge["reason"] == lw.SHARED_THREAD_REASON for edge in related)
    assert not any(edge["relation"] == "row_successor" for edge in payload["edges"])


def test_shared_thread_relatedness_never_creates_an_event_connector() -> None:
    document = {
        "id": "doc:D1",
        "document_no": "D1",
        "document_events": [
            {"guid": "g1", "event": "first", "timestamp": "2026-01-01T10:00:00"},
            {"guid": "g2", "event": "second", "timestamp": "2026-01-02T10:00:00"},
        ],
    }
    related = lw.make_lineage_edge(
        source="doc:D1",
        target="doc:D2",
        relation=lw.SHARED_THREAD_RELATION,
        reason=lw.SHARED_THREAD_REASON,
        evidence_status=lw.EVIDENCE_INFERRED,
        acthguid="T1",
    )

    event_lineage = lw.build_event_lineage(document, [related])

    assert [bead["connects_to_next"] for bead in event_lineage["beads"]] == [False, False]
    assert event_lineage["has_observed_transition"] is False
    assert event_lineage["relatedness"] == [
        {
            "kind": "relatedness",
            "label": lw.SHARED_THREAD_RELATION,
            "detail": "doc:D2",
            "evidence_status": lw.EVIDENCE_INFERRED,
            "evidence_id": "T1",
            "neighbor": "doc:D2",
        }
    ]


def test_identical_title_across_threads_is_inferred_not_transition() -> None:
    payload = lw.build_payload(
        [
            _row(guid="g1", docno="D1", acthguid="T1", date="2026-01-01", title="Quarterly budget pack"),
            _row(guid="g2", docno="D2", acthguid="T2", date="2026-02-01", title="Quarterly budget pack"),
        ]
    )
    affinities = [edge for edge in payload["edges"] if edge["relation"] == "topic_affinity"]
    assert len(affinities) == 1
    assert affinities[0]["evidence_status"] == lw.EVIDENCE_INFERRED
    assert affinities[0]["relation"] not in lw.TRANSITION_RELATIONS
    assert not any(edge["relation"] == lw.LEGACY_THREAD_TRANSITION_RELATION for edge in payload["edges"])
    assert payload["metadata"]["thread_count"] == 2
    assert "topic_affinity" in payload["metadata"]["evidence_policy"]["inferred_relations"]


def test_predicted_link_cannot_be_promoted_to_transition() -> None:
    with pytest.raises(ValueError, match="legacy_thread_transition_relation_not_allowed"):
        lw.make_lineage_edge(
            source="doc:A",
            target="doc:B",
            relation=lw.LEGACY_THREAD_TRANSITION_RELATION,
            reason="historical_fixture",
            evidence_status=lw.EVIDENCE_OBSERVED,
        )
    with pytest.raises(ValueError, match="cannot be promoted"):
        lw.make_lineage_edge(
            source="doc:A",
            target="doc:B",
            relation="row_successor",
            reason="hypothetical",
            evidence_status=lw.EVIDENCE_PREDICTED,
        )
    predicted = lw.make_lineage_edge(
        source="doc:A",
        target="doc:B",
        relation="topic_affinity",
        reason="hypothetical_schema_completion",
        evidence_status=lw.EVIDENCE_PREDICTED,
    )
    assert predicted["evidence_status"] == lw.EVIDENCE_PREDICTED
    assert predicted["relation"] not in lw.TRANSITION_RELATIONS


def test_admin_lineage_override_filters_only_selected_inferred_edges() -> None:
    """An admin exclusion removes the same document relation from lineage and KG projections."""
    edges = [
        {"source": "doc:A", "target": "doc:B", "relation": "topic_affinity", "evidence_status": lw.EVIDENCE_INFERRED},
        {"source": "doc:A", "target": "doc:C", "relation": "entity_role_affinity", "evidence_status": lw.EVIDENCE_PREDICTED},
    ]
    overrides = [{"source_node": "doc:A", "target_node": "doc:B", "relation_name": "topic_affinity", "override_status": "suppressed"}]
    assert lw.filter_lineage_edges_by_overrides(edges, []) == edges
    assert lw.filter_lineage_edges_by_overrides(edges, [{**overrides[0], "override_status": "restored"}]) == edges
    assert lw.filter_lineage_edges_by_overrides(edges, overrides) == [edges[1]]
    graph = {
        "nodes": [],
        "edges": [
            {"source": "kg:document:A", "target": "kg:document:B", "relation": "topic_affinity"},
            {"source": "kg:document:A", "target": "kg:document:C", "relation": "entity_role_affinity"},
            {"source": "kg:person:A", "target": "kg:person:B", "relation": "person_affinity"},
        ],
    }
    assert [edge["relation"] for edge in lw.filter_knowledge_graph_by_lineage_overrides(graph, overrides)["edges"]] == [
        "entity_role_affinity",
        "person_affinity",
    ]


def test_inline_image_metadata_is_classified_without_exporting_bytes() -> None:
    assert lw.classify_content_kind("data:image/png;base64," + "A" * 64, 1024) == lw.CONTENT_INLINE_IMAGE
    assert lw.classify_content_kind("<svg viewBox='0 0 1 1'>", 128) == lw.CONTENT_INLINE_MARKUP
    assert lw.classify_content_kind("A" * 64, 1024) == lw.CONTENT_INLINE_BINARY
    payload = lw.build_payload(
        [{
            **_row(guid="g1", docno="D1", acthguid="T1", date="2026-01-01"),
            "content_bytes": "1024",
            "content_prefix": "data:image/png;base64," + "A" * 64,
        }]
    )
    document = next(node for node in payload["nodes"] if node["type"] == "document")
    assert document["content_manifest"]["inline_image_candidate_rows"] == 1
    assert "content_prefix" not in document


def test_kg_links_llm_keyman_to_same_corporate_scope_source_person() -> None:
    """A LLM Keyman must join its observed same-corporation identity, not stay isolated."""
    graph = lw.build_knowledge_graph(
        [
            {"type": "document", "document_no": "", "title_sample": "ignored"},
            {
                "type": "document",
                "document_no": "DOC-1",
                "title_sample": "Supplier meeting",
                "corp_code": "CORP-1",
                "owner_pu": "PU-1",
                "keyman_our_side": [{"person_name": "Kim", "org_name": ""}, {}],
                "keyman_counterpart_side": [{"person_name": "Kim", "org_name": "Counterparty"}],
            },
            {
                "type": "row",
                "document_no": "missing-document",
                "guid": "ignored-row",
            },
            {
                "type": "row",
                "document_no": "DOC-1",
                "guid": "event-1",
                "event": "meeting",
                "corp_code": "CORP-1",
                "owner_pu": "PU-1",
                "created_by": "Kim",
                "changed_by": None,
                "user_id": None,
            },
        ],
        [],
    )
    matches = [edge for edge in graph["edges"] if edge["relation"] == "identity_name_match"]
    assert len(matches) == 1
    assert matches[0]["evidence_id"] == "DOC-1"
