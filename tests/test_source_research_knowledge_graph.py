"""ADR 0133 source research stays evidence-bearing in the KG projection."""

from __future__ import annotations

import asyncio

from backend.app import knowledge_graph


def test_supported_cited_actor_projects_standard_reference_and_attribution(
    monkeypatch,
) -> None:
    post_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"

    async def no_catalog_edges(conn, post_ids):
        return []

    async def focus_post(conn, related):
        return [
            {
                "node_type_code": "node_post",
                "node_id": post_id,
                "label": "Synthetic post",
            }
        ]

    monkeypatch.setattr(knowledge_graph, "load_visible_subgraph", no_catalog_edges)
    monkeypatch.setattr(knowledge_graph, "hydrate_related_nodes", focus_post)

    class Connection:
        async def fetch(self, query: str, *args: object):
            if "from post_summary_semantic_relationship" in query:
                return []
            if "from post_source_research_lead" in query:
                assert "research_supported" in query
                assert "post_source_research_citation" in query
                return [
                    {
                        "judgment_id": "judgment-1",
                        "retrieval_id": "retrieval-1",
                        "evidence_url": "https://example.test/patent",
                        "evidence_title": "Synthetic patent record",
                        "passage_text": "Example Research shared the synthetic record.",
                        "content_sha256": "a" * 64,
                        "sharing_actor_name": "Example Research",
                    }
                ]
            return []

        async def fetchrow(self, query: str, *args: object):
            assert "from source_post" in query
            return {
                "source_customer_code": None,
                "source_order_pool_code": None,
                "source_sales_order_code": None,
                "source_sales_order_item_number": None,
                "source_stage_code": None,
                "source_detail_state_code": None,
                "source_inspection_point_code": None,
                "source_deleted_flag": None,
            }

    result = asyncio.run(knowledge_graph.post_knowledge_graph(Connection(), post_id))

    projected = {
        edge["edge_type_code"]: edge
        for edge in result["edges"]
        if edge["edge_type_code"] in {"dct_references", "prov_was_attributed_to"}
    }
    assert set(projected) == {"dct_references", "prov_was_attributed_to"}
    assert (
        projected["dct_references"]["ontology_iri"]
        == "http://purl.org/dc/terms/references"
    )
    assert (
        projected["prov_was_attributed_to"]["ontology_iri"]
        == "http://www.w3.org/ns/prov#wasAttributedTo"
    )
    assert (
        projected["prov_was_attributed_to"]["assertion_status_code"]
        == "research_supported"
    )
    assert (
        projected["prov_was_attributed_to"]["evidence_url"]
        == "https://example.test/patent"
    )
    assert projected["prov_was_attributed_to"]["evidence_sha256"] == "a" * 64
    assert "confidence" not in projected["prov_was_attributed_to"]
