"""Bounded-window and proximity-first ontology pagination regressions."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone

from backend.app import ontology_neighborhood_ingestion as ingestion
from backend.app.ontology_neighborhood_ingestion import _load_facts
from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_MENTION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
)
from lineageweave.ontology_neighborhood import (
    PROPERTY_AFFILIATED_WITH,
    PROPERTY_MENTIONS,
    assemble_ontology_neighborhood,
    fact_from_knowledge_graph_edge,
    skos_broader_fact,
)
from lineageweave.ontology_source_cursor import OntologySourceCursor, OntologySourceKey

POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"
CORP_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc1"
GROUP_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1"
T0 = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


class WindowConnection:
    """Return one more row than the requested bounded fact window."""

    async def fetch(self, _sql: str, *_args: object) -> list[dict[str, object]]:
        """Return four deterministic rows for a three-row window."""
        return [
            {
                "source_node_type_code": NODE_POST,
                "source_node_id": POST_ID,
                "target_node_type_code": NODE_PERSON,
                "target_node_id": f"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb{index}",
                "edge_type_code": EDGE_MENTION,
                "available_at": T0,
                "evidence_ids": [POST_ID],
            }
            for index in range(1, 5)
        ]


def test_fact_window_reports_source_truncation_without_exceeding_bound() -> None:
    """One look-ahead row must expose a bounded-window limitation."""
    window = asyncio.run(
        _load_facts(
            WindowConnection(),  # type: ignore[arg-type]
            [POST_ID],
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            maximum_depth=1,
            maximum_edges=1,
        )
    )

    assert len(window) == 1
    assert window.truncated is True


def test_source_window_truncation_remains_visible_without_a_fake_cursor() -> None:
    """A bounded SQL window must never be reported as a complete graph."""
    fact = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PERSON,
        target_node_id=PERSON_ID,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
    )

    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[fact],
        labels={(NODE_POST, POST_ID): "Focus", (NODE_PERSON, PERSON_ID): "Person"},
        maximum_edges=10,
        source_truncated=True,
    )

    assert neighborhood.truncated is True
    assert neighborhood.next_cursor is None


def test_first_page_preserves_breadth_first_proximity_before_property_sort() -> None:
    """A one-edge first page must stay connected to the focus node."""
    focus_edge = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PERSON,
        target_node_id=PERSON_ID,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
    )
    second_hop = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        edge_type_code=EDGE_AFFILIATION,
        recorded_at=T0,
    )

    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[second_hop, focus_edge],
        labels={
            (NODE_POST, POST_ID): "Focus",
            (NODE_PERSON, PERSON_ID): "Person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Organization",
        },
        maximum_depth=2,
        maximum_edges=1,
    )

    assert len(neighborhood.edges) == 1
    assert neighborhood.edges[0].property_code == PROPERTY_MENTIONS
    assert neighborhood.edges[0].property_code != PROPERTY_AFFILIATED_WITH


def test_source_page_keeps_sql_reachable_edges_without_focus_bridge() -> None:
    """A later source page may contain only a relation beyond the focus edge."""
    second_hop = replace(
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id=PERSON_ID,
            target_node_type_code=NODE_CORPORATE_ENTITY,
            target_node_id=CORP_ID,
            edge_type_code=EDGE_AFFILIATION,
            recorded_at=T0,
        ),
        source_hop_depth=1,
    )

    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[second_hop],
        labels={
            (NODE_POST, POST_ID): "Focus",
            (NODE_PERSON, PERSON_ID): "Person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Organization",
        },
        maximum_depth=2,
        maximum_edges=1,
        source_truncated=True,
    )

    assert len(neighborhood.edges) == 1
    assert neighborhood.edges[0].property_code == PROPERTY_AFFILIATED_WITH


def test_source_page_deduplicates_edges_and_unions_evidence() -> None:
    """Window expansion must not duplicate one relation or drop evidence."""
    first_evidence = replace(
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id=PERSON_ID,
            target_node_type_code=NODE_CORPORATE_ENTITY,
            target_node_id=CORP_ID,
            edge_type_code=EDGE_AFFILIATION,
            recorded_at=T0,
            evidence_references=(POST_ID,),
        ),
        source_hop_depth=1,
    )
    second_evidence = replace(first_evidence, evidence_references=("other-evidence",))

    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[first_evidence, second_evidence],
        labels={
            (NODE_POST, POST_ID): "Focus",
            (NODE_PERSON, PERSON_ID): "Person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Organization",
        },
        maximum_depth=2,
        maximum_edges=2,
        source_truncated=True,
    )

    assert len(neighborhood.edges) == 1
    assert neighborhood.edges[0].evidence_references == (POST_ID, "other-evidence")


def test_source_page_uses_sql_order_when_display_order_differs() -> None:
    """Source paging must select and continue in the sealed SQL order."""
    first_in_sql = replace(
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id=PERSON_ID,
            target_node_type_code=NODE_POST,
            target_node_id=POST_ID,
            edge_type_code=EDGE_MENTION,
            recorded_at=T0,
        ),
        source_hop_depth=0,
        source_order_key=(0, EDGE_MENTION, NODE_PERSON, "z", NODE_POST, POST_ID),
    )
    second_in_sql = replace(
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
            target_node_type_code=NODE_POST,
            target_node_id=POST_ID,
            edge_type_code=EDGE_MENTION,
            recorded_at=T0,
        ),
        source_hop_depth=0,
        source_order_key=(0, EDGE_MENTION, NODE_PERSON, "a", NODE_POST, POST_ID),
    )

    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[second_in_sql, first_in_sql],
        labels={
            (NODE_POST, POST_ID): "Focus",
            (NODE_PERSON, PERSON_ID): "Person A",
            (NODE_PERSON, "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2"): "Person Z",
        },
        maximum_edges=1,
        source_truncated=True,
    )

    assert len(neighborhood.edges) == 1
    assert neighborhood.edges[0].target_node_id == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2"


class CapturingWindowConnection:
    """Record the keyset query without a live PostgreSQL instance."""

    def __init__(self) -> None:
        self.query = ""
        self.arguments: tuple[object, ...] = ()

    async def fetch(self, query: str, *arguments: object) -> list[object]:
        """Capture SQL and return no rows."""
        self.query = query
        self.arguments = arguments
        return []


def test_load_facts_uses_keyset_not_offset() -> None:
    """Source continuation must resume after the last SQL key, never OFFSET."""
    from lineageweave.ontology_source_cursor import OntologySourceKey

    conn = CapturingWindowConnection()
    after = OntologySourceKey(
        hop_depth=0,
        edge_type_code=EDGE_MENTION,
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PERSON,
        target_node_id=PERSON_ID,
    )
    window = asyncio.run(
        _load_facts(
            conn,  # type: ignore[arg-type]
            [POST_ID],
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            maximum_depth=1,
            maximum_edges=1,
            after_key=after,
        )
    )
    normalized = " ".join(conn.query.lower().split())
    assert "offset" not in normalized
    assert "$8::integer is null" in normalized
    assert conn.arguments[7] == 0
    assert conn.arguments[8] == EDGE_MENTION
    assert conn.arguments[10] == POST_ID
    assert conn.arguments[12] == PERSON_ID
    assert window == []


def test_load_facts_binds_edges_to_the_sealed_snapshot() -> None:
    """New graph edges must not splice into an already sealed continuation."""
    conn = CapturingWindowConnection()
    asyncio.run(
        _load_facts(
            conn,  # type: ignore[arg-type]
            [POST_ID],
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            maximum_depth=1,
            maximum_edges=1,
            snapshot_at=T0,
        )
    )
    normalized = " ".join(conn.query.lower().split())
    assert "edge.created_at <= $7::timestamptz" in normalized
    assert conn.arguments[6] == T0


def test_load_facts_binds_edge_creation_to_the_knowledge_cutoff() -> None:
    """A graph assertion created later must not appear in an earlier view."""
    conn = CapturingWindowConnection()
    asyncio.run(
        _load_facts(
            conn,  # type: ignore[arg-type]
            [POST_ID],
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            maximum_depth=1,
            maximum_edges=1,
            knowledge_cutoff=T0,
        )
    )
    normalized = " ".join(conn.query.lower().split())
    assert "edge.created_at <= $6::timestamptz" in normalized
    assert "greatest(edge.created_at, min(post.created_at))" in normalized
    assert conn.arguments[5] == T0


def test_loaded_display_edge_keeps_its_raw_sql_cursor_key() -> None:
    """A reversed display relation must still resume with the raw SQL orientation."""
    window = asyncio.run(
        _load_facts(
            WindowConnection(),  # type: ignore[arg-type]
            [POST_ID],
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            maximum_depth=1,
            maximum_edges=1,
        )
    )
    display_key = next(iter(window.source_keys_by_edge))
    source_key = window.source_keys_by_edge[display_key]
    assert display_key[0] == PROPERTY_MENTIONS
    assert display_key[1] == NODE_PERSON
    assert source_key.edge_type_code == EDGE_MENTION
    assert source_key.source_node_id == POST_ID


class CursorConnection:
    """Supply the focus label used by the in-memory continuation regression."""

    async def fetchval(self, query: str, *_args: object) -> str | None:
        """Return only the synthetic focus title."""
        return "Focus" if "post_title" in query else None


def test_source_continuation_uses_sealed_snapshot_and_rechecks_page_endpoints(monkeypatch) -> None:
    """Continuation must use the sealed time and authorize newly loaded endpoints."""
    fact = replace(
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_POST,
            source_node_id=POST_ID,
            target_node_type_code=NODE_PERSON,
            target_node_id=PERSON_ID,
            edge_type_code=EDGE_MENTION,
            recorded_at=T0,
            evidence_references=(POST_ID,),
        ),
        source_hop_depth=0,
    )
    last_key = OntologySourceKey(
        hop_depth=0,
        edge_type_code=EDGE_MENTION,
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PERSON,
        target_node_id=PERSON_ID,
    )
    claims = OntologySourceCursor(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        knowledge_cutoff=None,
        maximum_depth=1,
        maximum_nodes=10,
        maximum_edges=1,
        allowed_property_codes=None,
        last_key=last_key,
        snapshot_at=T0,
        eligibility_digest="digest",
        expires_at=T0,
    )
    load_snapshots: list[datetime | None] = []
    focus_visibility_snapshots: list[datetime | None] = []
    load_after_keys: list[OntologySourceKey | None] = []
    verify_modes: list[bool] = []
    minted_keys: list[OntologySourceKey] = []
    display_edge_key = (
        fact.property_code,
        fact.source_node_type_code,
        fact.source_node_id,
        fact.target_node_type_code,
        fact.target_node_id,
    )

    async def fake_load_facts(*_args, snapshot_at=None, after_key=None, **_kwargs):
        load_snapshots.append(snapshot_at)
        load_after_keys.append(after_key)
        return ingestion._LoadedFactWindow(
            [fact],
            truncated=True,
            last_source_key=last_key,
            source_keys_by_edge={display_edge_key: last_key},
        )

    async def fake_visible_post_ids(*_args, snapshot_at=None, **_kwargs):
        focus_visibility_snapshots.append(snapshot_at)
        return [POST_ID]

    async def fake_focus_exists(*_args, **_kwargs):
        return True

    async def fake_visible_by_nodes(_conn, endpoint_keys, _can_see_post, **_kwargs):
        assert (NODE_PERSON, PERSON_ID) in endpoint_keys
        return {(NODE_PERSON, PERSON_ID): [POST_ID]}

    async def fake_skos(*_args, **_kwargs):
        return []

    async def fake_labels(*_args, **_kwargs):
        return {(NODE_POST, POST_ID): "Focus", (NODE_PERSON, PERSON_ID): "Person"}

    async def fake_metadata(*_args, **_kwargs):
        return {}

    def fake_verify(_token, **kwargs):
        verify_modes.append(kwargs["validate_eligibility"])
        return claims

    def fake_mint(**kwargs):
        minted_keys.append(kwargs["last_key"])
        return "src.v2.next"

    monkeypatch.setattr(ingestion, "focus_catalog_exists", fake_focus_exists)
    monkeypatch.setattr(ingestion, "visible_post_ids_for_focus", fake_visible_post_ids)
    monkeypatch.setattr(ingestion, "_load_facts", fake_load_facts)
    monkeypatch.setattr(ingestion, "_visible_post_ids_by_nodes", fake_visible_by_nodes)
    monkeypatch.setattr(ingestion, "_load_skos_facts", fake_skos)
    monkeypatch.setattr(ingestion, "_load_labels", fake_labels)
    monkeypatch.setattr(ingestion, "_load_node_metadata", fake_metadata)
    monkeypatch.setattr(ingestion, "_load_voice_assignments", fake_skos)
    monkeypatch.setattr(ingestion, "verify_source_cursor", fake_verify)
    monkeypatch.setattr(ingestion, "mint_source_cursor", fake_mint)

    result = asyncio.run(
        ingestion.visible_ontology_neighborhood(
            CursorConnection(),  # type: ignore[arg-type]
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            can_see_post=lambda _row: True,
            maximum_depth=1,
            maximum_nodes=10,
            maximum_edges=1,
            cursor="src.v2.synthetic",
            source_cursor_secret="s" * 32,
            source_cursor_scope="account",
        )
    )

    assert verify_modes == [False, True]
    assert focus_visibility_snapshots == [T0]
    assert load_snapshots == [T0, T0]
    assert load_after_keys == [None, last_key]
    assert minted_keys == [last_key]
    assert result.edges


def test_skos_overflow_mints_source_cursor_for_continuation(monkeypatch) -> None:
    """Derived SKOS overflow must not expose an unusable in-memory cursor."""
    fact = replace(
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id=PERSON_ID,
            target_node_type_code=NODE_CORPORATE_ENTITY,
            target_node_id=CORP_ID,
            edge_type_code=EDGE_AFFILIATION,
            recorded_at=T0,
            evidence_references=(POST_ID,),
        ),
        source_hop_depth=0,
        source_order_key=(
            0,
            EDGE_AFFILIATION,
            NODE_PERSON,
            PERSON_ID,
            NODE_CORPORATE_ENTITY,
            CORP_ID,
        ),
    )
    skos = skos_broader_fact(
        narrower_entity_id=CORP_ID,
        broader_entity_id=GROUP_ID,
        recorded_at=T0,
    )
    last_key = OntologySourceKey(
        hop_depth=0,
        edge_type_code=EDGE_AFFILIATION,
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
    )
    claims = OntologySourceCursor(
        focus_node_type_code=NODE_CORPORATE_ENTITY,
        focus_node_id=CORP_ID,
        knowledge_cutoff=None,
        maximum_depth=1,
        maximum_nodes=10,
        maximum_edges=1,
        allowed_property_codes=None,
        last_key=last_key,
        snapshot_at=T0,
        eligibility_digest="digest",
        expires_at=T0,
    )
    load_after_keys: list[OntologySourceKey | None] = []
    minted_keys: list[OntologySourceKey] = []

    async def fake_load_facts(*_args, after_key=None, **_kwargs):
        load_after_keys.append(after_key)
        if after_key is not None:
            return ingestion._LoadedFactWindow()  # type: ignore[attr-defined]
        return ingestion._LoadedFactWindow(  # type: ignore[attr-defined]
            [fact],
            source_keys_by_edge={
                (
                    fact.property_code,
                    fact.source_node_type_code,
                    fact.source_node_id,
                    fact.target_node_type_code,
                    fact.target_node_id,
                ): last_key
            },
        )

    async def fake_visible_post_ids(*_args, **_kwargs):
        return [POST_ID]

    async def fake_focus_exists(*_args, **_kwargs):
        return True

    async def fake_visible_by_nodes(_conn, endpoint_keys, _can_see_post, **_kwargs):
        return {key: [POST_ID] for key in endpoint_keys}

    async def fake_skos(*_args, **_kwargs):
        return [skos]

    async def fake_labels(*_args, **_kwargs):
        return {
            (NODE_PERSON, PERSON_ID): "Person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Organization",
            (NODE_CORPORATE_ENTITY, GROUP_ID): "Group",
        }

    async def fake_metadata(*_args, **_kwargs):
        return {}

    def fake_verify(_token, **_kwargs):
        return claims

    def fake_mint(**kwargs):
        minted_keys.append(kwargs["last_key"])
        return "src.v2.synthetic-next"

    monkeypatch.setattr(ingestion, "focus_catalog_exists", fake_focus_exists)
    monkeypatch.setattr(ingestion, "visible_post_ids_for_focus", fake_visible_post_ids)
    monkeypatch.setattr(ingestion, "_load_facts", fake_load_facts)
    monkeypatch.setattr(ingestion, "_visible_post_ids_by_nodes", fake_visible_by_nodes)
    monkeypatch.setattr(ingestion, "_load_skos_facts", fake_skos)
    monkeypatch.setattr(ingestion, "_load_labels", fake_labels)
    monkeypatch.setattr(ingestion, "_load_node_metadata", fake_metadata)
    monkeypatch.setattr(ingestion, "verify_source_cursor", fake_verify)
    monkeypatch.setattr(ingestion, "mint_source_cursor", fake_mint)

    first_page = asyncio.run(
        ingestion.visible_ontology_neighborhood(
            CursorConnection(),  # type: ignore[arg-type]
            focus_node_type_code=NODE_CORPORATE_ENTITY,
            focus_node_id=CORP_ID,
            can_see_post=lambda _row: True,
            maximum_depth=1,
            maximum_nodes=10,
            maximum_edges=1,
            source_cursor_secret="s" * 32,
            source_cursor_scope="account",
        )
    )
    second_page = asyncio.run(
        ingestion.visible_ontology_neighborhood(
            CursorConnection(),  # type: ignore[arg-type]
            focus_node_type_code=NODE_CORPORATE_ENTITY,
            focus_node_id=CORP_ID,
            can_see_post=lambda _row: True,
            maximum_depth=1,
            maximum_nodes=10,
            maximum_edges=1,
            cursor=first_page.next_cursor,
            source_cursor_secret="s" * 32,
            source_cursor_scope="account",
        )
    )

    assert first_page.next_cursor == "src.v2.synthetic-next"
    assert [edge.property_code for edge in second_page.edges] == ["skos_broader"]
    assert second_page.next_cursor is None
    assert load_after_keys == [None, None, last_key]
    assert minted_keys == [last_key]
