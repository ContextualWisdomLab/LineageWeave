"""ABAC regression for Event Lineage channel evidence."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from backend.app.lineage_ingestion import visible_lineage_graph


class _Connection:
    def __init__(self) -> None:
        self.channel_query_count = 0

    async def fetch(self, query: str, *arguments: Any) -> list[dict[str, Any]]:
        if "from source_post" in query:
            return [
                {
                    "post_id": "post-visible",
                    "post_title": "Visible parent",
                    "voc_type_code": "voc",
                    "visibility_code": "public",
                    "corporate_entity_id": "visible-corp",
                    "process_unit_id": None,
                    "thread_group_key": "thread-a",
                    "created_at": datetime(2026, 1, 1),
                },
                {
                    "post_id": "post-hidden",
                    "post_title": "Hidden child",
                    "voc_type_code": "voc",
                    "visibility_code": "private",
                    "corporate_entity_id": "hidden-corp",
                    "process_unit_id": None,
                    "thread_group_key": "thread-a",
                    "created_at": datetime(2026, 1, 2),
                },
            ]
        if "from post_lineage_edge" in query:
            return [
                {
                    "parent_post_id": "post-visible",
                    "child_post_id": "post-hidden",
                    "fused_score": 0.8,
                    "lineage_reconstruction_run_id": "run-hidden",
                }
            ]
        if "from lineage_edge_channel_score" in query:
            self.channel_query_count += 1
            raise AssertionError("hidden endpoint evidence must not be queried")
        raise AssertionError(f"unexpected query: {query}; args={arguments}")


def test_hidden_endpoint_removes_edge_and_skips_channel_evidence_query() -> None:
    connection = _Connection()
    graph = asyncio.run(
        visible_lineage_graph(
            connection,
            lambda row: row["visibility_code"] == "public",
        )
    )

    assert [node["id"] for node in graph["nodes"]] == ["post-visible"]
    assert graph["edges"] == []
    assert connection.channel_query_count == 0
