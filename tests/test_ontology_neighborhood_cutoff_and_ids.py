"""Focused regression tests for cutoff-safe and canonical ontology traversal."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import backend.app.ontology_neighborhood_ingestion as ingestion
from lineageweave.knowledge_graph import NODE_POST

POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
CUTOFF = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


class CapturingConnection:
    """Capture the fact-loading SQL and parameters without a database."""

    def __init__(self) -> None:
        self.sql = ""
        self.args: tuple[object, ...] = ()

    async def fetch(self, sql: str, *args: object) -> list[object]:
        """Record one query and return an empty deterministic result."""
        self.sql = " ".join(sql.split())
        self.args = args
        return []


def test_load_facts_filters_available_evidence_before_sql_limit() -> None:
    """The cutoff must enter SQL before candidate ordering and LIMIT."""
    conn = CapturingConnection()

    facts = asyncio.run(
        ingestion._load_facts(
            conn,  # type: ignore[arg-type]
            [POST_ID],
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            maximum_depth=2,
            maximum_edges=10,
            knowledge_cutoff=CUTOFF,
        )
    )

    assert facts == []
    assert "post.created_at <= $6::timestamptz" in conn.sql
    assert "offset" not in conn.sql.lower()
    assert CUTOFF in conn.args


def test_visible_neighborhood_canonicalizes_uppercase_uuid_before_traversal(
    monkeypatch: Any,
) -> None:
    """UUID spelling must not change recursive-neighborhood reachability."""
    seen: dict[str, object] = {}
    sentinel = object()

    async def fake_focus_exists(_conn: object, node_type: str, node_id: str) -> bool:
        seen["exists"] = (node_type, node_id)
        return True

    async def fake_visible_posts(
        _conn: object,
        node_type: str,
        node_id: str,
        _can_see_post: object,
        **_kwargs: object,
    ) -> list[str]:
        seen["visible"] = (node_type, node_id)
        return [POST_ID]

    async def fake_load_facts(
        _conn: object,
        _visible_post_ids: list[str],
        **kwargs: object,
    ) -> list[object]:
        seen["facts"] = kwargs
        return []

    async def fake_empty(*_args: object, **_kwargs: object) -> list[object]:
        return []

    async def fake_labels(*_args: object, **_kwargs: object) -> dict[object, str]:
        return {}

    async def fake_metadata(*_args: object, **_kwargs: object) -> dict[object, object]:
        return {}

    def fake_assemble(**kwargs: object) -> object:
        seen["assemble"] = kwargs
        return sentinel

    monkeypatch.setattr(ingestion, "focus_catalog_exists", fake_focus_exists)
    monkeypatch.setattr(ingestion, "visible_post_ids_for_focus", fake_visible_posts)
    monkeypatch.setattr(ingestion, "_load_facts", fake_load_facts)
    monkeypatch.setattr(ingestion, "_load_skos_facts", fake_empty)
    monkeypatch.setattr(ingestion, "_load_labels", fake_labels)
    monkeypatch.setattr(ingestion, "_load_node_metadata", fake_metadata)
    monkeypatch.setattr(ingestion, "assemble_ontology_neighborhood", fake_assemble)

    result = asyncio.run(
        ingestion.visible_ontology_neighborhood(
            object(),  # type: ignore[arg-type]
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID.upper(),
            can_see_post=lambda _row: True,
            knowledge_cutoff=CUTOFF,
        )
    )

    assert result is sentinel
    assert seen["exists"] == (NODE_POST, POST_ID)
    assert seen["visible"] == (NODE_POST, POST_ID)
    assert isinstance(seen["facts"], dict)
    assert seen["facts"]["focus_node_id"] == POST_ID  # type: ignore[index]
    assert seen["facts"]["knowledge_cutoff"] == CUTOFF  # type: ignore[index]
    assert isinstance(seen["assemble"], dict)
    assert seen["assemble"]["focus_node_id"] == POST_ID  # type: ignore[index]
