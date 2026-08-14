"""Exercise LineageApplication read and mutation behavior with a direct-DB boundary double."""

from __future__ import annotations

import base64
import json
import time

import pytest

import lineageweave as lw
import lineageweave_server as server


ACTOR = {
    "account_id": "fixture-account",
    "corp_code": "CORP_A",
    "pu_code": "PU_A",
    "roles": ["admin"],
}


class _Connection:
    """Minimal transaction context used by the direct PostgreSQL adapter calls."""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def commit(self):
        return None


def _payload():
    """Return a compact, single-tenant graph with a real inline asset contract."""
    document = {
        "id": "doc:DOC-1",
        "type": "document",
        "document_no": "DOC-1",
        "acthguid": "THREAD-1",
        "corp_code": "CORP_A",
        "owner_pu": "PU_A",
        "visibility": "private",
        "title_sample": "Fixture document",
        "last_row_ts": "2026-01-02T00:00:00",
        "row_count": 1,
        "keyman_our_side": [{"person_name": "Our person", "org_name": "Our org"}],
        "keyman_counterpart_side": [{"person_name": "Partner person", "org_name": "Partner org"}],
    }
    row = {
        "id": "row:ROW-1",
        "type": "row",
        "document_no": "DOC-1",
        "stage": "open",
        "status": "active",
    }
    return {
        "metadata": {"row_count": 1, "thread_count": 1},
        "analytics": {"total_rows": 1, "multi_document_threads": 0},
        "nodes": [document, row],
        "edges": [{"source": "doc:DOC-1", "target": "row:ROW-1", "relation": "observed", "acthguid": "THREAD-1"}],
        "access_directory": {"CORP_A": {"units": {"PU_A": "Fixture PU"}}},
        "knowledge_graph": {
            "nodes": [
                {"id": "kg:document:DOC-1", "type": "document", "document_no": "DOC-1", "document_nos": ["DOC-1"]},
                {"id": "kg:person:our", "type": "person", "label": "Our person", "document_nos": ["DOC-1"]},
            ],
            "edges": [{"source": "kg:document:DOC-1", "target": "kg:person:our", "relation": "mentions"}],
        },
    }


def _application(monkeypatch):
    """Create an application with direct connection creation isolated for the test."""
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    app._payload = _payload()
    return app


def test_admin_lineage_review_screen_can_suppress_and_restore_inferred_edges(monkeypatch) -> None:
    """Keep manual lineage corrections tenant-scoped, auditable, and non-transition-only."""
    app = _application(monkeypatch)
    candidate = {
        "source_node": "doc:DOC-1",
        "target_node": "doc:DOC-2",
        "source_document": "DOC-1",
        "target_document": "DOC-2",
        "source_title": "Fixture source",
        "target_title": "Fixture target",
        "relation": "topic_affinity",
        "evidence_status": lw.EVIDENCE_INFERRED,
        "override_status": "pending",
        "reason": "shared topic",
    }
    monkeypatch.setattr(lw, "load_lineage_review_edges", lambda *_args, **_kwargs: {"items": [candidate], "total": 1})
    persisted: list[dict[str, object]] = []
    monkeypatch.setattr(lw, "persist_lineage_edge_override", lambda _connection, **kwargs: persisted.append(kwargs))
    events: list[tuple[object, ...]] = []
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 1)

    assert app.lineage_review_edges(ACTOR)["items"] == [candidate]
    updated = app.update_lineage_edge_override(
        ACTOR,
        {"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation_name": "topic_affinity", "decision": "suppressed", "reason": " "},
    )
    assert updated["override_status"] == "suppressed"
    assert persisted[0]["updated_by"] == "fixture-account"
    assert events[0][0] == "lineage_edge_override_changed"
    assert app._payload is None
    with pytest.raises(PermissionError, match="keyverse_admin_required"):
        app.lineage_review_edges({**ACTOR, "roles": ["reader"]})


def test_admin_lineage_override_validates_identity_and_transition_boundaries(monkeypatch) -> None:
    """Reject malformed, missing, and observed-transition decisions before persistence."""
    app = _application(monkeypatch)
    for body, message in (
        ({}, "identity_required"),
        ({"source_node": "s", "target_node": "t", "relation": "r", "decision": "invalid"}, "unknown"),
        ({"source_node": "s" * 257, "target_node": "t", "relation": "r", "decision": "suppressed"}, "too_long"),
        ({"source_node": "s", "target_node": "t", "relation": "r", "decision": "suppressed", "reason": "x" * 501}, "reason_too_long"),
    ):
        with pytest.raises(ValueError, match=message):
            app.update_lineage_edge_override(ACTOR, body)
    monkeypatch.setattr(lw, "load_lineage_review_edges", lambda *_args, **_kwargs: {"items": []})
    with pytest.raises(KeyError, match="not_found"):
        app.update_lineage_edge_override(ACTOR, {"source_node": "s", "target_node": "t", "relation": "r", "decision": "suppressed"})
    monkeypatch.setattr(
        lw,
        "load_lineage_review_edges",
        lambda *_args, **_kwargs: {"items": [{"source_node": "s", "target_node": "t", "relation": "r", "evidence_status": lw.EVIDENCE_OBSERVED, "source_document": "DOC-1"}]},
    )
    with pytest.raises(PermissionError, match="observed"):
        app.update_lineage_edge_override(ACTOR, {"source_node": "s", "target_node": "t", "relation": "r", "decision": "suppressed", "reason": " "})


def test_event_queue_flush_and_health_keep_a_durable_backlog_when_valkey_fails(monkeypatch) -> None:
    """Publish committed events in order and leave the failed tail in the PostgreSQL outbox."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    pending = [
        {"event_id": "event-1", "event_type": "visibility_changed", "document_no": "DOC-1", "actor_id": "account-1"},
        {"event_id": "event-2", "event_type": "ticket_created", "document_no": "DOC-1", "actor_id": "account-1"},
    ]
    monkeypatch.setattr(lw, "pending_event_outbox", lambda _connection: pending)
    published: list[str] = []

    def publish(event: dict) -> None:
        published.append(event["event_id"])
        if event["event_id"] == "event-2":
            raise OSError("valkey unavailable")

    marked: list[str] = []
    monkeypatch.setattr(lw, "publish_valkey_event", publish)
    monkeypatch.setattr(lw, "mark_event_published", lambda _connection, event_id: marked.append(event_id))
    assert app._flush_event_outbox() == 1
    assert published == ["event-1", "event-2"]
    assert marked == ["event-1"]

    monkeypatch.setattr(lw, "valkey_ping", lambda: True)
    assert app.event_queue_health() == {
        "stream": lw.VALKEY_EVENT_STREAM,
        "ready": True,
        "pending_outbox": 2,
    }
    monkeypatch.setattr(
        server.psycopg,
        "connect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    assert app._flush_event_outbox() == 0
    monkeypatch.setattr(lw, "valkey_ping", lambda: (_ for _ in ()).throw(RuntimeError("valkey unavailable")))
    assert app.event_queue_health() == {
        "stream": lw.VALKEY_EVENT_STREAM,
        "ready": False,
        "pending_outbox": 0,
    }


def test_application_read_contracts_filter_documents_and_assets(monkeypatch) -> None:
    """Keep document, KG, content, and image-search responses actor scoped."""
    app = _application(monkeypatch)
    asset = {
        "asset_index": 0,
        "source_position": 3,
        "row_guid": "ROW-1",
        "source_row_number": "1",
        "mime_type": "image/png",
        "data_uri": "data:image/png;base64," + base64.b64encode(b"fixture-image").decode("ascii"),
        "encoded_bytes": len(b"fixture-image"),
        "content_kind": lw.CONTENT_INLINE_IMAGE,
    }
    asset["asset_sha256"] = lw.content_asset_sha256(asset)
    monkeypatch.setattr(app, "_document_assets", lambda _document_no: [asset])
    monkeypatch.setattr(
        app,
        "_materialize_document_content",
        lambda _document_no: {"blocks": [], "assets": [asset]},
    )
    monkeypatch.setattr(lw, "ensure_content_inspection_tables", lambda _connection: None)
    inspections = [
        {
            "asset_index": 0,
            "asset_sha256": asset["asset_sha256"],
            "source_evidence_id": "ROW-1",
            "source_row_number": "1",
            "source_position": 3,
            "mime_type": "image/png",
            "ocr_text": "fixture text",
            "model_name": "fixture-model",
            "inspected_by": "fixture-account",
            "inspected_at": "2026-01-01T00:00:00",
        }
    ]
    labels = [{"asset_index": 0, "label_name": "chart", "label_description": "fixture chart", "label_position": 0}]

    def query(_connection, sql, _params=()):
        if "GROUP BY inspection.document_no" in sql:
            return [
                {
                    "document_no": "DOC-1",
                    "asset_index": 0,
                    "mime_type": "image/png",
                    "ocr_text": "fixture text",
                    "inspected_at": "2026-01-01T00:00:00",
                    "object_labels": [{"label": "chart", "description": "fixture chart"}],
                }
            ]
        if "inspection_label" in sql:
            return labels
        if "analysis_content_inspections" in sql:
            return inspections
        if "content_preview" in sql:
            return [
                {
                    "guid_field": "ROW-1",
                    "docnosub_field": "DOC-1",
                    "acthguid_field": "THREAD-1",
                    "title_field": "Fixture document",
                    "voctp_field": "event",
                    "ststs_field": "open",
                    "dtsts_field": "active",
                    "grade_field": "A",
                    "bukrs_field": "CORP_A",
                    "pucode_field": "PU_A",
                    "userid_field": "fixture-account",
                    "erdat_field": "2026-01-01",
                    "erzet_field": "10:00:00",
                    "aedat_field": "2026-01-02",
                    "aezet_field": "11:00:00",
                    "source_row_number": "1",
                    "content_bytes": 13,
                    "content_preview": "fixture",
                }
            ]
        return [{"document_no": "DOC-1", "asset_index": 0, "ocr_text": "fixture text", "object_labels": []}]

    monkeypatch.setattr(lw, "_database_query", query)
    monkeypatch.setattr(
        lw,
        "load_visible_document_index",
        lambda _connection, _actor, _limit, _offset=0, search="": {
            "items": [] if search == "missing" else [{"document_no": "DOC-1", "acthguid": "THREAD-1", "title": "Fixture document", "corp_code": "CORP_A", "owner_pu": "PU_A", "row_count": 1, "first_row_ts": None, "last_row_ts": "2026-01-02T00:00:00", "entity_role": None, "visibility": "private"}],
            "total": 0 if search == "missing" else 1,
        },
    )
    detail = app.document(ACTOR, "DOC-1")
    assert detail["document"]["document_no"] == "DOC-1"
    assert detail["rows"][0]["id"] == "row:ROW-1"
    assert app.document_index(ACTOR, 1)["items"] == [{"document_no": "DOC-1", "acthguid": "THREAD-1", "title": "Fixture document", "corp_code": "CORP_A", "owner_pu": "PU_A", "row_count": 1, "first_row_ts": None, "last_row_ts": "2026-01-02T00:00:00", "entity_role": None, "visibility": "private"}]
    assert app.document_index(ACTOR, 1, search="fixture")["total"] == 1
    assert app.document_index(ACTOR, 1, search="missing")["total"] == 0
    assert app.knowledge(ACTOR, "DOC-1", {"depth": ["1"]})["nodes"]

    manifest = app.content_manifest(ACTOR, "DOC-1")
    assert manifest["asset_count"] == 1
    assert manifest["assets"][0]["inspection"]["object_labels"] == [{"label": "chart", "description": "fixture chart"}]
    mime, body = app.asset_bytes(ACTOR, "DOC-1", 0)
    assert (mime, body) == ("image/png", b"fixture-image")
    assert app.image_search(ACTOR, "fixture", limit=2)["items"][0]["document_no"] == "DOC-1"
    assert app.source_evidence(ACTOR, "DOC-1", "ROW-1")["content_preview"] == "fixture"
    with pytest.raises(ValueError, match="at least two"):
        app.image_search(ACTOR, "x")
    with pytest.raises(ValueError, match="too long"):
        app.image_search(ACTOR, "x" * 161)
    monkeypatch.setattr(app, "filtered_payload", lambda _actor: {"nodes": []})
    assert app.image_search(ACTOR, "fixture") == {"query": "fixture", "items": []}
    with pytest.raises(KeyError):
        app.document(ACTOR, "NOT-VISIBLE")


def test_application_verifies_inferred_lineage_with_llm_and_persists_a_run(monkeypatch) -> None:
    """Require an authorized actor, bounded evidence, and a Valkey outbox event."""
    app = _application(monkeypatch)
    graph = {
        "nodes": [
            {"id": "kg:document:DOC-1", "type": "document", "document_no": "DOC-1", "document_nos": ["DOC-1"], "label": "Fixture document"},
            {"id": "kg:org:left", "type": "organization", "document_nos": ["DOC-1"], "label": "Acme Korea"},
            {"id": "kg:org:right", "type": "organization", "document_nos": ["DOC-2"], "label": "Acme Plant"},
        ],
        "edges": [
            {"source": "kg:document:DOC-1", "target": "kg:org:left", "relation": "document_customer_entity", "evidence_id": "ROW-1"},
            {"source": "kg:org:left", "target": "kg:org:right", "relation": "affiliate_affinity", "evidence_status": "inferred", "reason": "tree"},
        ],
    }
    app._payload["knowledge_graph"] = graph
    monkeypatch.setattr(lw, "related_knowledge_graph", lambda _graph, _document_no: graph)
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {"decision": "verified", "confidence": 0.9, "evidence_ids": ["ROW-1"], "model": "fixture"}, "live_http"))
    monkeypatch.setattr(lw, "search_external_inference_evidence", lambda _labels: {"mode": "not_configured", "query": "", "evidence": []})
    persisted = {}
    monkeypatch.setattr(lw, "persist_inference_verification_run", lambda _connection, **kwargs: persisted.update(kwargs) or {"run_id": "run-1", "candidate_count": len(kwargs["verification_rows"]), "evidence_count": 1})
    events = []
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: "flushed")

    result = app.verify_lineage_inferences(ACTOR, "DOC-1")
    assert result["run_id"] == "run-1"
    assert result["items"][0]["decision"] == "verified"
    assert persisted["document_no"] == "DOC-1"
    assert events[0][0] == "lineage_inferences_verified"

    monkeypatch.setattr(
        lw,
        "resolve_product_transport",
        lambda: (_ for _ in ()).throw(RuntimeError("gateway unavailable")),
    )
    offline = app.verify_lineage_inferences(ACTOR, "DOC-1")
    assert offline["items"][0]["decision"] == "insufficient"


def test_application_resolves_organization_alias_into_verified_semantic_graph(monkeypatch) -> None:
    """Cross-check a document alias, audit the decision, and retain edge direction."""
    app = _application(monkeypatch)
    document = next(node for node in app._payload["nodes"] if node.get("type") == "document")
    monkeypatch.setattr(app, "document", lambda _actor, _document_no: {"document": document})
    app._payload = None
    monkeypatch.setattr(
        app,
        "payload",
        lambda: (_ for _ in ()).throw(AssertionError("alias resolution must not load the full KG")),
    )
    evidence = {
        "evidence_id": "external-1",
        "evidence_kind": "external",
        "title": "Official organization: Canonical Organization",
        "excerpt": "Alias and canonical name",
        "source_uri": "https://example.test/official",
        "source_rank": 1,
    }
    monkeypatch.setattr(app, "_document_content_structure", lambda _document_no: {"blocks": [], "assets": []})
    monkeypatch.setattr(
        lw,
        "search_external_organization_alias_evidence",
        lambda _alias: {"mode": "searxng", "query": "alias", "evidence": [evidence]},
    )
    monkeypatch.setattr(
        lw,
        "resolve_product_transport",
        lambda: (
            lambda _body: {
                "decision": "verified",
                "canonical_name": "Canonical Organization",
                "confidence": 0.91,
                "rationale": "official evidence",
                "evidence_ids": ["external-1"],
                "model": "fixture-model",
            },
            "live_http",
        ),
    )
    persisted = {}
    snapshots = []
    monkeypatch.setattr(
        lw,
        "persist_inference_verification_run",
        lambda _connection, **kwargs: persisted.update(kwargs)
        or {"run_id": "alias-run", "candidate_count": 1, "evidence_count": 1},
    )
    monkeypatch.setattr(lw, "persist_knowledge_graph_additions", lambda _connection, graph: snapshots.append(graph) or {})
    events = []
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: "flushed")

    result = app.resolve_organization_alias(ACTOR, "DOC-1", "Alias")

    assert result["decision"] == "verified"
    assert result["direction"] == "alias_to_canonical"
    assert persisted["external_search_mode"] == "searxng"
    assert len(snapshots[0]["nodes"]) == 2
    edge = next(item for item in snapshots[0]["edges"] if item.get("relation") == "organization_alias")
    assert edge["source"] == result["candidate"]["source_node"]
    assert edge["target"] == result["candidate"]["target_node"]
    assert events[0][0] == "organization_alias_resolved"

    app._payload = _payload()
    cached_result = app.resolve_organization_alias(ACTOR, "DOC-1", "Alias")
    assert cached_result["decision"] == "verified"
    assert any(
        edge.get("relation") == "organization_alias"
        for edge in app._payload["knowledge_graph"]["edges"]
    )


def test_application_rejects_foreign_or_invalid_alias_requests(monkeypatch) -> None:
    """Keep alias resolution behind the same document authorization and input boundary."""
    app = _application(monkeypatch)
    document = next(node for node in app._payload["nodes"] if node.get("type") == "document")
    monkeypatch.setattr(app, "document", lambda _actor, _document_no: {"document": document})
    foreign_actor = {"account_id": "foreign", "corp_code": "CORP_B", "pu_code": "PU_B", "roles": ["reader"]}
    with pytest.raises(PermissionError, match="corp"):
        app.resolve_organization_alias(foreign_actor, "DOC-1", "Alias")
    with pytest.raises(ValueError, match="2-160"):
        app.resolve_organization_alias(ACTOR, "DOC-1", "")


def test_application_records_unverified_alias_without_promoting_graph(monkeypatch) -> None:
    """Persist an inconclusive alias review while leaving the semantic graph unchanged."""
    app = _application(monkeypatch)
    evidence = {
        "evidence_id": "external-1",
        "evidence_kind": "external",
        "title": "Ambiguous result",
        "excerpt": "Insufficient evidence",
        "source_uri": "https://example.test/ambiguous",
        "source_rank": 1,
    }
    monkeypatch.setattr(app, "_document_content_structure", lambda _document_no: {"blocks": [], "assets": []})
    monkeypatch.setattr(
        lw,
        "search_external_organization_alias_evidence",
        lambda _alias: {"mode": "searxng", "query": "alias", "evidence": [evidence]},
    )
    monkeypatch.setattr(
        lw,
        "resolve_product_transport",
        lambda: (
            lambda _body: {
                "decision": "insufficient",
                "canonical_name": "",
                "confidence": 0.2,
                "rationale": "ambiguous",
                "evidence_ids": [],
                "model": "fixture-model",
            },
            "live_http",
        ),
    )
    monkeypatch.setattr(
        lw,
        "persist_inference_verification_run",
        lambda _connection, **_kwargs: {"run_id": "alias-review", "candidate_count": 1, "evidence_count": 1},
    )
    monkeypatch.setattr(lw, "persist_knowledge_graph_additions", lambda *_args: pytest.fail("unverified alias must not be promoted"))
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda *_args: None)
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 1)

    result = app.resolve_organization_alias(ACTOR, "DOC-1", "Alias")

    assert result["decision"] == "insufficient"
    assert result["external_search_mode"] == "searxng"


def test_application_records_empty_inference_verification_without_model(monkeypatch) -> None:
    """Audit an empty candidate set without calling the live model gateway."""
    app = _application(monkeypatch)
    empty_graph = {"nodes": [], "edges": []}
    app._payload["knowledge_graph"] = empty_graph
    monkeypatch.setattr(lw, "related_knowledge_graph", lambda _graph, _document_no: empty_graph)
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: pytest.fail("model must not run without candidates"))
    persisted = {}
    monkeypatch.setattr(
        lw,
        "persist_inference_verification_run",
        lambda _connection, **kwargs: persisted.update(kwargs)
        or {"run_id": "run-empty", "candidate_count": 0, "evidence_count": 0},
    )
    events = []
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: "flushed")

    result = app.verify_lineage_inferences(ACTOR, "DOC-1")

    assert result == {
        "run_id": "run-empty",
        "candidate_count": 0,
        "evidence_count": 0,
        "external_search_mode": "not_applicable",
        "items": [],
    }
    assert persisted["verification_rows"] == []
    assert events[0][0] == "lineage_inferences_verified"


def test_application_payload_outbox_and_actor_lifetimes(monkeypatch) -> None:
    """Use persisted snapshots, publish committed outbox rows, and expire local state."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    persisted = _payload()
    monkeypatch.setattr(lw, "load_persisted_analysis_payload", lambda *_args, **_kwargs: persisted)
    overrides = []
    monkeypatch.setattr(lw, "load_database_overrides", lambda *_args: overrides.append(True))
    monkeypatch.setattr(lw, "persist_knowledge_graph_snapshot", lambda *_args, **_kwargs: {})
    assert app.payload() is persisted
    assert overrides == [True]

    events = [
        {"event_id": "one", "event_type": "fixture", "document_no": "DOC-1", "actor_id": "fixture-account", "payload": {}},
        {"event_id": "two", "event_type": "fixture", "document_no": "DOC-1", "actor_id": "fixture-account", "payload": {}},
    ]
    published = []
    marked = []
    monkeypatch.setattr(lw, "pending_event_outbox", lambda *_args: events)
    monkeypatch.setattr(lw, "publish_valkey_event", lambda event: published.append(event))
    monkeypatch.setattr(lw, "mark_event_published", lambda _connection, event_id: marked.append(event_id))
    assert app._flush_event_outbox() == 2
    assert marked == ["one", "two"]
    monkeypatch.setattr(lw, "valkey_ping", lambda: True)
    assert app.event_queue_health() == {"stream": lw.VALKEY_EVENT_STREAM, "ready": True, "pending_outbox": 2}

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", json.dumps(ACTOR))
    assert app._development_actor() == {**ACTOR, "corp_name": None, "pu_name": None}
    app._sessions["expired"] = {"expires_at": time.time() - 1}
    app._keyverse_states["expired"] = {"expires_at": time.time() - 1}
    app._prune_auth_state()
    assert not app._sessions and not app._keyverse_states


def test_persisted_payload_repair_and_cold_document_denials_are_fail_closed(monkeypatch) -> None:
    """Persist repaired KG evidence and deny absent or foreign cold documents."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    persisted = _payload()
    snapshots: list[dict] = []
    monkeypatch.setattr(lw, "load_persisted_analysis_payload", lambda *_args, **_kwargs: persisted)
    monkeypatch.setattr(lw, "load_database_overrides", lambda *_args: None)
    monkeypatch.setattr(lw, "attach_customer_master_knowledge_graph", lambda graph, *_args: graph)
    monkeypatch.setattr(
        lw,
        "merge_lineage_evidence_into_knowledge_graph",
        lambda graph, _edges: (graph, [{"relation": "repaired_evidence"}]),
    )
    monkeypatch.setattr(
        lw,
        "persist_knowledge_graph_snapshot",
        lambda _connection, graph: snapshots.append(graph),
    )
    assert app.payload() is persisted
    assert snapshots == [persisted["knowledge_graph"]]

    cold = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda *_args: None)
    with pytest.raises(KeyError, match="MISSING"):
        cold.document(ACTOR, "MISSING")
    monkeypatch.setattr(
        lw,
        "load_persisted_document_detail",
        lambda *_args: {
            "document": {
                "document_no": "FOREIGN",
                "corp_code": "CORP_B",
                "owner_pu": "PU_B",
                "visibility": "private",
            }
        },
    )
    with pytest.raises(KeyError, match="FOREIGN"):
        cold.document(ACTOR, "FOREIGN")


def test_application_mutations_keep_cache_and_outbox_in_sync(monkeypatch) -> None:
    """Persist visibility, Keyman, ticket, and inspection changes before cache updates."""
    app = _application(monkeypatch)
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 0)
    monkeypatch.setattr(lw, "_database_exec", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "build_knowledge_graph", lambda *_args, **_kwargs: {"nodes": [], "edges": []})
    monkeypatch.setattr(lw, "persist_knowledge_graph_snapshot", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(lw, "persist_visibility", lambda *_args, **_kwargs: None)
    updated = app.set_visibility(ACTOR, "DOC-1", "public")
    assert updated["visibility"] == "public"

    monkeypatch.setattr(lw, "normalize_keyman_side", lambda value: list(value or []))
    sides = app.set_keymen(ACTOR, "DOC-1", {"our_side": [{"person_name": "Our"}], "counterpart_side": []})
    assert sides["our_side"] == [{"person_name": "Our"}]
    with pytest.raises(ValueError, match="at least one"):
        app.set_keymen(ACTOR, "DOC-1", {})
    authorize_access = lw.authorize_access
    document = app.document
    monkeypatch.setattr(
        app, "document", lambda *_args: {"document": {"document_no": "DOC-1"}}
    )
    monkeypatch.setattr(
        lw,
        "authorize_access",
        lambda **_kwargs: {"allowed": False, "reason": "keyman_forbidden"},
    )
    with pytest.raises(PermissionError, match="keyman_forbidden"):
        app.set_keymen(ACTOR, "DOC-1", {"our_side": [{"person_name": "Our"}]})
    monkeypatch.setattr(app, "document", document)
    monkeypatch.setattr(lw, "authorize_access", authorize_access)

    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    ticket = app.create_ticket(ACTOR, "DOC-1", {"title": "Fixture ticket"})
    assert ticket["ticket_id"].startswith("tkt-DOC-1-")
    with pytest.raises(ValueError, match="ticket title"):
        app.create_ticket(ACTOR, "DOC-1", {})
    monkeypatch.setattr(
        app, "document", lambda *_args: {"document": {"document_no": "DOC-1"}}
    )
    monkeypatch.setattr(
        lw,
        "authorize_access",
        lambda **_kwargs: {"allowed": False, "reason": "ticket_forbidden"},
    )
    with pytest.raises(PermissionError, match="ticket_forbidden"):
        app.create_ticket(ACTOR, "DOC-1", {"title": "Denied ticket"})
    monkeypatch.setattr(app, "document", document)
    monkeypatch.setattr(lw, "authorize_access", authorize_access)
    monkeypatch.setattr(
        lw,
        "resolve_product_transport",
        lambda: (_ for _ in ()).throw(RuntimeError("worker unavailable")),
    )
    monkeypatch.setattr(
        lw,
        "map_issue_to_work_items",
        lambda ticket, _document: {
            "todo": {"ticket_id": ticket["ticket_id"], "source": "fallback"},
            "calendar": {"ticket_id": ticket["ticket_id"], "source": "fallback"},
        },
    )
    fallback_ticket = app.create_ticket(ACTOR, "DOC-1", {"title": "Fallback ticket"})
    assert fallback_ticket["todo"]["source"] == "fallback"

    asset = {
        "asset_index": 0,
        "source_position": 1,
        "row_guid": "ROW-1",
        "source_row_number": "1",
        "mime_type": "image/png",
        "data_uri": "data:image/png;base64,Zm9v",
        "encoded_bytes": 3,
        "content_kind": lw.CONTENT_INLINE_IMAGE,
    }
    asset["asset_sha256"] = lw.content_asset_sha256(asset)
    monkeypatch.setattr(app, "_document_assets", lambda _document_no: [asset])
    monkeypatch.setattr(lw, "live_http_config", lambda: (_ for _ in ()).throw(RuntimeError("not configured")))
    monkeypatch.setattr(lw, "ensure_compose_standin", lambda: "ready")
    monkeypatch.setattr(lw, "derive_content_inspection_via_llm", lambda *_args, **_kwargs: {"ocr_text": "fixture", "object_labels": [], "asset_sha256": asset["asset_sha256"], "model_name": "fixture"})
    monkeypatch.setattr(lw, "persist_content_inspection", lambda *_args, **_kwargs: None)
    inspection = app.inspect_content_asset(ACTOR, "DOC-1", 0)
    assert inspection["transport"] == "compose_live_proxy"

    observed: dict[str, object] = {}
    monkeypatch.setattr(
        lw,
        "live_http_config",
        lambda: ("https://gateway.example", "fixture-token", "fixture-model"),
    )
    monkeypatch.setattr(
        lw,
        "post_content_inspection_http",
        lambda body, **kwargs: observed.update({"body": body, **kwargs})
        or {"ocr_text": "live fixture", "object_labels": [], "model": "fixture-model"},
    )
    monkeypatch.setattr(
        lw,
        "derive_content_inspection_via_llm",
        lambda _asset, *, transport: {
            **transport({"task": "content_inspection"}),
            "asset_sha256": asset["asset_sha256"],
        },
    )
    live_inspection = app.inspect_content_asset(ACTOR, "DOC-1", 0)
    assert live_inspection["transport"] == "live_http"
    assert observed["base_url"] == "https://gateway.example"

    encoded_asset = {**asset, "mime_type": "text/plain", "data_uri": "data:text/plain,owned%20text"}
    monkeypatch.setattr(app, "_document_assets", lambda _document_no: [encoded_asset])
    assert app.asset_bytes(ACTOR, "DOC-1", 0) == ("text/plain", b"owned text")
    with pytest.raises(KeyError):
        app.asset_bytes(ACTOR, "DOC-1", 1)

    monkeypatch.setattr(
        lw,
        "authorize_access",
        lambda **_kwargs: {"allowed": False, "reason": "inspection_forbidden"},
    )
    monkeypatch.setattr(app, "document", lambda *_args: {"document": {"document_no": "DOC-1"}})
    with pytest.raises(PermissionError, match="inspection_forbidden"):
        app.inspect_content_asset(ACTOR, "DOC-1", 0)
    monkeypatch.setattr(app, "document", document)
    monkeypatch.setattr(lw, "authorize_access", authorize_access)
    monkeypatch.setattr(app, "_document_assets", lambda _document_no: [])
    with pytest.raises(KeyError):
        app.inspect_content_asset(ACTOR, "DOC-1", 0)


def test_cold_mutations_persist_without_rebuilding_the_full_snapshot(monkeypatch) -> None:
    """Keep direct PostgreSQL mutations responsive when the large graph is cold."""
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    cold = server.LineageApplication("postgresql://fixture", "schema.table")
    document = dict(_payload()["nodes"][0])
    monkeypatch.setattr(cold, "document", lambda *_args: {"document": dict(document)})
    monkeypatch.setattr(cold, "_flush_event_outbox", lambda: 0)
    monkeypatch.setattr(lw, "persist_visibility", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "ensure_keyman_override_columns", lambda *_args: None)
    monkeypatch.setattr(lw, "_database_exec", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(
        lw,
        "map_issue_to_work_items",
        lambda ticket, _document: {
            "todo": {"ticket_id": ticket["ticket_id"]},
            "calendar": {"ticket_id": ticket["ticket_id"]},
        },
    )
    monkeypatch.setattr(lw, "persist_issue_work_items", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "resolve_keyman_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(
        lw,
        "derive_keymen_via_llm",
        lambda *_args, **_kwargs: {
            "our_side": [{"person_name": "Ana", "org_name": "Org A"}],
            "counterpart_side": [],
            "names": ["Ana"],
            "source": "llm",
            "status": "ready",
            "orchestration": {},
        },
    )

    assert cold.set_visibility(ACTOR, "DOC-1", "public")["visibility"] == "public"
    assert cold.set_keymen(ACTOR, "DOC-1", {"our_side": ["Ana"], "counterpart_side": []})["our_side"]
    assert cold.create_ticket(ACTOR, "DOC-1", {"title": "Cold follow-up"})["todo"]
    assert cold.derive_keymen(ACTOR, "DOC-1")["keyman"]["names"] == ["Ana"]
    assert cold._payload is None


def test_content_manifest_hides_assets_when_safe_materialization_is_unavailable(monkeypatch) -> None:
    """Leave no byte handle in an authorized manifest after a materialization outage."""
    app = _application(monkeypatch)
    monkeypatch.setattr(
        app,
        "_materialize_document_content",
        lambda _document_no: (_ for _ in ()).throw(RuntimeError("content unavailable")),
    )
    manifest = app.content_manifest(ACTOR, "DOC-1")
    assert manifest == {
        "document_no": "DOC-1",
        "assets": [],
        "asset_count": 0,
        "inspections": [],
        "semantic_blocks": [],
        "semantic_block_count": 0,
    }


def test_workspace_surface_and_reports_skip_full_graph(monkeypatch) -> None:
    """Analytics and persisted reports must not materialize the 43k-node snapshot."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(
        lw,
        "load_workspace_surface",
        lambda _connection, *, actor: {
            "metadata": {"row_count": 43814, "document_count": 43707, "thread_count": 42467},
            "analytics": {"total_rows": 43814, "total_documents": 43707, "multi_document_threads": 42467},
            "affiliate_tree": {
                "edges": [{"parent": "삼성전자", "child": "삼성전자 평택사업장", "source": "llm"}],
                "nodes": ["삼성전자", "삼성전자 평택사업장"],
                "parent_of": {},
            },
            "customer_master": {"source": "llm", "edges": [{"parent": "삼성전자", "child": "삼성전자 평택사업장"}]},
            "period_reports": [
                {"report_id": "weekly-pu-D02", "period_kind": "weekly", "slice_kind": "pu", "slice_key": "D02", "document_nos": ["DOC-D02"], "judge": {"verdict": "pass"}},
                {"report_id": "weekly-pu-other", "period_kind": "weekly", "slice_kind": "pu", "slice_key": "OTHER", "document_nos": ["DOC-OTHER"], "judge": {"verdict": "pass"}},
                {"report_id": "weekly-team-1", "period_kind": "weekly", "slice_kind": "team", "slice_key": "T1", "document_nos": ["DOC-TEAM"], "judge": {"verdict": "pass"}},
            ],
            "factor_definitions": lw.default_factor_definitions(),
        },
    )
    monkeypatch.setattr(
        app,
        "payload",
        lambda: (_ for _ in ()).throw(AssertionError("full payload must stay cold")),
    )
    monkeypatch.setattr(
        lw,
        "load_authorized_report_document_numbers",
        lambda _connection, _actor: {"DOC-D02", "DOC-TEAM", "DOC-PROJECT"},
    )
    actor = {**ACTOR, "pu_code": "D02"}
    surface = app.workspace_surface(actor)
    assert surface["analytics"]["total_rows"] == 43814
    assert [item["report_id"] for item in surface["period_reports"]] == [
        "weekly-pu-D02",
        "weekly-team-1",
    ]
    monkeypatch.setattr(
        lw,
        "load_period_reports",
        lambda _connection: [
            {
                "report_id": "monthly-project-1",
                "period_kind": "monthly",
                "slice_kind": "project",
                "slice_key": "P1",
                "document_nos": ["DOC-PROJECT"],
                "judge": {"verdict": "pass"},
                "linked_scores": [{"score_id": "s1", "linking_method": "fipc"}],
            }
        ],
    )
    reports = app.reports(actor)
    assert reports["source"] == "persisted"
    assert reports["reports"][0]["slice_kind"] == "project"


def test_persisted_report_refresh_retries_unavailable_global_results(monkeypatch) -> None:
    """Recover stale persisted reports only after the live judge path is available."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    app._payload = {"period_reports": []}
    monkeypatch.setenv("LINEAGEWEAVE_REPORT_REFRESH_MAX_SLICES", "1")
    monkeypatch.setenv("LINEAGEWEAVE_REPORT_REFRESH_MAX_ATTEMPTS", "1")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    lock_calls: list[str] = []

    def advisory_query(_connection, sql, _params=()):  # noqa: ANN001
        if "pg_try_advisory_lock" in sql:
            lock_calls.append("lock")
            return [{"locked": True}]
        if "pg_advisory_unlock" in sql:
            lock_calls.append("unlock")
            return [{"unlocked": True}]
        raise AssertionError(sql)

    fresh = {
        "report_id": "report-fresh",
        "judge": {"source": "llm_judge"},
        "linked_scores": [{"score_id": "score-fresh"}],
    }
    stale = {
        "report_id": "report-stale",
        "judge": {"source": "unavailable"},
        "linked_scores": [],
    }
    stale_later = {
        "report_id": "report-stale-later",
        "judge": {"source": "unavailable"},
        "linked_scores": [],
    }
    documents = [{"type": "document", "document_no": "DOC-1", "owner_pu": "PU_A"}]
    scored = [{"report_id": "report-stale", "judge": {"source": "llm_judge"}, "linked_scores": [{"score_id": "score-1"}]}]
    monkeypatch.setattr(lw, "_database_query", advisory_query)
    monkeypatch.setattr(lw, "load_period_reports", lambda _connection: [fresh, stale, stale_later])
    monkeypatch.setattr(lw, "load_report_document_nodes", lambda _connection: documents)
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "resolve_mlsirm_transport", lambda: (None, "fast_mlsirm_local_unavailable"))
    all_slices = [
        {"report_id": "report-fresh"},
        {"report_id": "report-stale"},
        {"report_id": "report-stale-later"},
    ]
    monkeypatch.setattr(lw, "build_period_report_slices", lambda rows: all_slices if rows else [])
    score_calls: list[list[dict]] = []
    score_options: list[dict] = []

    def score_reports(rows, *_args, **_kwargs):  # noqa: ANN001
        score_calls.append(rows)
        score_options.append(_kwargs)
        return scored

    monkeypatch.setattr(lw, "score_period_reports", score_reports)
    written: list[dict] = []
    monkeypatch.setattr(lw, "persist_period_reports", lambda _connection, rows: written.extend(rows))

    assert app.refresh_persisted_reports() == 1
    assert score_calls == [[{"report_id": "report-stale"}]]
    assert callable(score_options[0]["judge_transport"])
    assert score_options[0]["mlsirm_transport"] is None
    assert score_options[0]["judge_max_attempts"] == 1
    assert written == [fresh, *scored, stale_later]
    assert app._payload["period_reports"] == [fresh, *scored, stale_later]
    assert lock_calls == ["lock", "unlock"]

    app._payload = None
    assert app.refresh_persisted_reports() == 1

    initial_scored = [
        {
            "report_id": "report-initial",
            "judge": {"source": "llm_judge"},
            "linked_scores": [{"score_id": "score-initial"}],
        }
    ]
    monkeypatch.setattr(lw, "load_period_reports", lambda _connection: [])
    monkeypatch.setattr(lw, "build_period_report_slices", lambda _rows: [{"report_id": "report-initial"}])
    monkeypatch.setattr(lw, "score_period_reports", lambda *_args, **_kwargs: initial_scored)
    written.clear()
    app._payload = {}
    assert app.refresh_persisted_reports() == 1
    assert written == initial_scored
    assert app._payload["period_reports"] == initial_scored


def test_persisted_report_refresh_skips_busy_or_unconfigured_runtime(monkeypatch) -> None:
    """Leave stale report rows intact when another process owns the refresh or the gateway is absent."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [{"locked": False}])
    assert app.refresh_persisted_reports() == 0

    lock_calls: list[str] = []

    def advisory_query(_connection, sql, _params=()):  # noqa: ANN001
        lock_calls.append("unlock" if "unlock" in sql else "lock")
        return [{"unlocked": True}] if "unlock" in sql else [{"locked": True}]

    monkeypatch.setattr(lw, "_database_query", advisory_query)
    monkeypatch.setattr(
        lw,
        "load_period_reports",
        lambda _connection: [{"report_id": "report-1", "judge": {"source": "unavailable"}, "linked_scores": []}],
    )
    monkeypatch.setattr(lw, "load_report_document_nodes", lambda _connection: [{"document_no": "DOC-1"}])
    monkeypatch.setattr(
        lw,
        "resolve_product_transport",
        lambda: (_ for _ in ()).throw(RuntimeError("gateway_unavailable")),
    )
    assert app.refresh_persisted_reports() == 0
    assert lock_calls == ["lock", "unlock"]

    monkeypatch.setattr(
        lw,
        "load_period_reports",
        lambda _connection: [{"judge": {"source": "llm_judge"}, "linked_scores": [{"score_id": "score-1"}]}],
    )
    assert app.refresh_persisted_reports() == 0

    monkeypatch.setattr(
        lw,
        "load_period_reports",
        lambda _connection: [{"report_id": "report-1", "judge": {"source": "unavailable"}, "linked_scores": []}],
    )
    monkeypatch.setattr(lw, "load_report_document_nodes", lambda _connection: [])
    assert app.refresh_persisted_reports() == 0

    documents = [{"document_no": "DOC-1"}]
    monkeypatch.setattr(lw, "load_report_document_nodes", lambda _connection: documents)
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "build_period_report_slices", lambda _documents: [])
    assert app.refresh_persisted_reports() == 0

    monkeypatch.setattr(lw, "build_period_report_slices", lambda _documents: [{"report_id": "unexpected"}])
    assert app.refresh_persisted_reports() == 0

    monkeypatch.setattr(lw, "build_period_report_slices", lambda _documents: [{"report_id": "report-1"}])
    monkeypatch.setattr(lw, "resolve_mlsirm_transport", lambda: (None, "not_configured"))
    monkeypatch.setattr(lw, "score_period_reports", lambda *_args, **_kwargs: [])
    assert app.refresh_persisted_reports() == 0

    monkeypatch.setattr(
        lw,
        "score_period_reports",
        lambda *_args, **_kwargs: [{"report_id": "unexpected"}],
    )
    assert app.refresh_persisted_reports() == 0


def test_lineage_review_admin_methods_validate_scope_and_emit_audit_event(monkeypatch) -> None:
    """Allow only an admin-reviewed inferred edge to change and invalidate its cached projection."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    candidate = {
        "source_node": "doc:DOC-1",
        "target_node": "doc:DOC-2",
        "source_document": "DOC-1",
        "target_document": "DOC-2",
        "relation": "similar",
        "evidence_status": lw.EVIDENCE_INFERRED,
        "reason": "fixture",
    }
    monkeypatch.setattr(
        lw,
        "load_lineage_review_edges",
        lambda _connection, _actor, **_kwargs: {"items": [candidate]},
    )
    assert app.lineage_review_edges(ACTOR, query="fixture", limit=3) == {"items": [candidate]}

    for body, error in (
        ({}, "lineage_edge_identity_required"),
        ({"source_node": "x" * 257, "target_node": "doc:DOC-2", "relation": "similar", "override_status": "suppressed"}, "lineage_edge_identity_too_long"),
        ({"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation": "similar", "override_status": "invalid"}, "unknown_lineage_edge_override_status"),
        ({"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation": "similar", "override_status": "suppressed", "reason": "x" * 501}, "lineage_edge_reason_too_long"),
    ):
        with pytest.raises(ValueError, match=error):
            app.update_lineage_edge_override(ACTOR, body)

    persisted: list[dict] = []
    events: list[tuple] = []
    flushed: list[bool] = []
    monkeypatch.setattr(lw, "persist_lineage_edge_override", lambda _connection, **kwargs: persisted.append(kwargs))
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: flushed.append(True))
    app._payload = {"cached": True}
    result = app.update_lineage_edge_override(
        ACTOR,
        {"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation_name": "similar", "decision": "suppressed"},
    )
    assert result["override_status"] == "suppressed"
    assert persisted == [
        {
            "source_node": "doc:DOC-1",
            "target_node": "doc:DOC-2",
            "relation_name": "similar",
            "override_status": "suppressed",
            "reason": "관리자 Lineage 검토",
            "updated_by": "fixture-account",
        }
    ]
    assert events[0][0] == "lineage_edge_override_changed"
    assert app._payload is None
    assert flushed == [True]

    monkeypatch.setattr(lw, "load_lineage_review_edges", lambda *_args, **_kwargs: {"items": []})
    with pytest.raises(KeyError, match="lineage_edge_not_found"):
        app.update_lineage_edge_override(ACTOR, {"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation": "similar", "override_status": "restored"})
    monkeypatch.setattr(
        lw,
        "load_lineage_review_edges",
        lambda *_args, **_kwargs: {"items": [{**candidate, "evidence_status": lw.EVIDENCE_OBSERVED}]},
    )
    with pytest.raises(PermissionError, match="observed_transition_not_overridable"):
        app.update_lineage_edge_override(ACTOR, {"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation": "similar", "override_status": "restored"})


def test_customer_surface_filters_query_and_keeps_evidence_links(monkeypatch) -> None:
    """The customer screen receives only the actor-scoped persisted customer master."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(
        lw,
        "load_workspace_surface",
        lambda _connection, *, actor: {
            "customer_master": {
                "source": "llm",
                "accounts": [
                    {"account_name": "Group", "parent_name": "", "tier": "group", "entity_role": "고객", "document_nos": ["DOC-1"]},
                    {"account_name": "Fixture customer", "parent_name": "Group", "tier": "hq", "entity_role": "고객", "document_nos": ["DOC-1"]},
                    {"account_name": "Other customer", "parent_name": "Other", "tier": "plant", "entity_role": "고객", "document_nos": ["DOC-2"]},
                ],
                "edges": [
                    {"parent": "Group", "child": "Fixture customer", "document_nos": ["DOC-1"]},
                    {"parent": "Other", "child": "Other customer", "document_nos": ["DOC-2"]},
                ],
                "parent_of": {"Fixture customer": "Group", "Other customer": "Other"},
            }
        },
    )
    surface = app.customer_surface(ACTOR, query="fixture", limit=500)
    assert surface["source"] == "llm"
    assert [account["account_name"] for account in surface["accounts"]] == ["Fixture customer", "Group"]
    assert surface["nodes"] == ["Fixture customer", "Group"]
    assert surface["edges"] == [{"parent": "Group", "child": "Fixture customer", "document_nos": ["DOC-1"]}]
    with pytest.raises(ValueError, match="customer_query_too_long"):
        app.customer_surface(ACTOR, query="x" * 129)


def test_cold_document_index_and_detail_query_one_scope(monkeypatch) -> None:
    """A cold API must page documents and open one popup without loading the graph."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    app._payload = {"nodes": [{"type": "document", "document_no": "CACHED"}]}
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(
        app,
        "payload",
        lambda: (_ for _ in ()).throw(AssertionError("full payload must stay cold")),
    )
    monkeypatch.setattr(
        app,
        "filtered_payload",
        lambda *_args: (_ for _ in ()).throw(AssertionError("cached graph must not be scanned")),
    )
    monkeypatch.setattr(
        lw,
        "load_visible_document_index",
        lambda _connection, _actor, limit, offset, search="": {
            "items": [{"document_no": "DOC-9", "title": "Live post"}],
            "total": 9,
            "limit": limit,
            "offset": offset,
            "search": search,
        },
    )
    index = app.document_index(ACTOR, 100, 0, "live")
    assert index["items"][0]["document_no"] == "DOC-9"
    assert index["search"] == "live"
    assert app.document_index(ACTOR, 1, 0)["items"][0]["document_no"] == "DOC-9"
    app._payload = None
    monkeypatch.setattr(
        lw,
        "load_persisted_document_detail",
        lambda _connection, document_no: {
            "document": {
                "id": f"doc:{document_no}",
                "document_no": document_no,
                "corp_code": "CORP_A",
                "owner_pu": "PU_A",
                "visibility": "public",
                "title_sample": "Live post",
                "keyman_our_side": [{"person_name": "Our"}],
                "keyman_counterpart_side": [{"person_name": "Them"}],
            },
            "rows": [],
            "edges": [],
            "knowledge_graph": {"nodes": [], "edges": []},
        },
    )
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    detail = app.document(ACTOR, "DOC-9")
    assert detail["document"]["document_no"] == "DOC-9"
    assert detail["document"]["keyman_our_side"][0]["person_name"] == "Our"


def test_document_content_materialization_preserves_location_and_persists_kg(monkeypatch) -> None:
    """Keep safe DOM/image semantics tied to source evidence before the popup exposes them."""
    app = _application(monkeypatch)
    image = base64.b64encode(b"\x89PNG\r\n\x1a\nfixture").decode("ascii")
    monkeypatch.setattr(
        app,
        "_document_content_records",
        lambda _document_no: [
            {"guid_field": "ROW-1", "source_row_number": 1, "voccts_field": "<p>first event</p>"},
            {
                "guid_field": "ROW-2",
                "source_row_number": 2,
                "voccts_field": f'<p align="right">second event</p><img src="data:image/png;base64,{image}">',
            },
        ],
    )
    structure = app._document_content_structure("DOC-1")
    assert [block["source_evidence_id"] for block in structure["blocks"]] == ["ROW-1", "ROW-2"]
    assert structure["blocks"][1]["block_index"] == 1
    assert structure["assets"][0]["asset_index"] == 0
    assert structure["assets"][0]["source_row_number"] == 2
    assert "data_uri" not in structure["assets"][0]

    persisted: list[tuple[str, object]] = []
    monkeypatch.setattr(
        lw,
        "attach_document_content_knowledge_graph",
        lambda _graph, document_no, value: {"nodes": [{"id": f"kg:document:{document_no}"}], "edges": [], "content": value},
    )
    monkeypatch.setattr(
        lw,
        "persist_document_content_structure",
        lambda _connection, document_no, value: persisted.append((document_no, value)),
    )
    monkeypatch.setattr(
        lw,
        "persist_knowledge_graph_snapshot",
        lambda _connection, graph: persisted.append(("knowledge", graph)),
    )
    assert app._materialize_document_content("DOC-1") == structure
    assert persisted[0] == ("DOC-1", structure)
    assert app._payload["knowledge_graph"]["nodes"] == [{"id": "kg:document:DOC-1"}]


def test_persisted_knowledge_neighborhood_and_report_build_paths(monkeypatch) -> None:
    """Use direct PostgreSQL scopes before falling back to a single authorized report build."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    persisted_document = {
        "document": {
            "id": "doc:DOC-9",
            "document_no": "DOC-9",
            "corp_code": "CORP_A",
            "owner_pu": "PU_A",
            "visibility": "public",
        }
    }
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda *_args: persisted_document)
    monkeypatch.setattr(
        lw,
        "load_persisted_keyman_neighborhood",
        lambda _connection, person, depth=None: {"nodes": [{"id": f"kg:person:{person}", "depth": depth}], "edges": []},
    )
    assert app.knowledge(ACTOR, "DOC-9", {"person": ["Analyst"], "depth": ["3"]})["nodes"] == [
        {"id": "kg:person:Analyst", "depth": 3}
    ]
    with pytest.raises(ValueError, match="depth must be an integer"):
        app.knowledge(ACTOR, "DOC-9", {"depth": ["not-a-number"]})

    denied_document = {
        "document": {
            **persisted_document["document"],
            "corp_code": "CORP_B",
            "visibility": "private",
        }
    }
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda *_args: denied_document)
    with pytest.raises(KeyError):
        app.knowledge(ACTOR, "DOC-9", {})

    app._payload = _payload()
    monkeypatch.setattr(
        lw,
        "load_persisted_document_detail",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    fallback = app.knowledge(ACTOR, "DOC-1", {"node": ["kg:person:our"], "depth": ["1"]})
    assert {node["id"] for node in fallback["nodes"]} == {"kg:document:DOC-1", "kg:person:our"}

    requested: dict[str, object] = {}
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda *_args: persisted_document)
    persisted_neighborhood = {
        "nodes": [
            {"id": "kg:person:analyst", "type": "person", "traversal_depth": 0},
            {"id": "kg:organization:affiliate", "type": "organization", "traversal_depth": 1},
            {"id": "kg:pu:affiliate", "type": "pu", "traversal_depth": 2},
        ],
        "edges": [
            {"source": "kg:person:analyst", "target": "kg:organization:affiliate", "relation": "member_of"},
            {"source": "kg:organization:affiliate", "target": "kg:pu:affiliate", "relation": "unit_of"},
        ],
    }
    monkeypatch.setattr(lw, "load_persisted_keyman_neighborhood", lambda *_args, **_kwargs: {"nodes": [], "edges": []})

    def load_persisted_neighborhood(_connection, seeds, depth=None):
        requested.update({"seeds": seeds, "depth": depth})
        return persisted_neighborhood

    monkeypatch.setattr(lw, "load_persisted_knowledge_neighborhood", load_persisted_neighborhood)
    assert app.knowledge(ACTOR, "DOC-9", {"node": ["kg:person:analyst"], "depth": ["2"]}) == persisted_neighborhood
    assert requested == {"seeds": {"kg:person:analyst"}, "depth": 2}

    app._payload = _payload()
    monkeypatch.setattr(lw, "load_period_reports", lambda _connection: [])
    monkeypatch.setattr(lw, "load_authorized_report_document_numbers", lambda _connection, _actor: {"DOC-1"})
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (_ for _ in ()).throw(RuntimeError("gateway_unavailable")))
    monkeypatch.setattr(lw, "resolve_mlsirm_transport", lambda: (None, "not_configured"))
    monkeypatch.setattr(lw, "build_period_report_slices", lambda documents: [{"slice_key": documents[0]["document_no"]}])
    scored = [{"report_id": "report-1", "slice_key": "DOC-1", "linked_scores": []}]
    monkeypatch.setattr(
        lw,
        "score_period_reports",
        lambda slices, documents, **kwargs: scored if slices and documents and kwargs["judge_transport"] is None else [],
    )
    written: list[object] = []
    monkeypatch.setattr(lw, "persist_period_reports", lambda _connection, rows: written.extend(rows))
    result = app.reports(ACTOR)
    assert result["source"] == "built"
    assert result["judge_transport"] == "gateway_unavailable"
    assert result["mlsirm_transport"] == "not_configured"
    assert written == scored
    assert app._payload["period_reports"] == scored


def test_persisted_keyman_neighborhood_uses_only_the_bounded_graph_star(monkeypatch) -> None:
    """Return a persisted Keyman walk without materializing the full KG snapshot."""
    star = {
        "nodes": [
            {"id": "kg:document:DOC-1", "type": "document", "label": "Fixture document"},
            {"id": "kg:person:analyst", "type": "person", "label": "Analyst"},
        ],
        "edges": [
            {
                "source": "kg:document:DOC-1",
                "target": "kg:person:analyst",
                "relation": "mentions",
            }
        ],
    }
    loaded: list[list[str]] = []
    monkeypatch.setattr(
        lw,
        "load_persisted_kg_star",
        lambda _connection, seeds: loaded.append(list(seeds)) or star,
    )

    neighborhood = lw.load_persisted_knowledge_neighborhood(
        _Connection(), {"kg:document:DOC-1"}, depth=1
    )
    assert loaded == [["kg:document:DOC-1"]]
    assert {node["id"] for node in neighborhood["nodes"]} == {
        "kg:document:DOC-1",
        "kg:person:analyst",
    }

    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)
    monkeypatch.setattr(lw, "_database_query", lambda *_args: [{"node_id": "kg:person:analyst"}])
    monkeypatch.setattr(lw, "load_customer_master", lambda *_args: {"edges": []})
    loaded.clear()
    keyman = lw.load_persisted_keyman_neighborhood(_Connection(), "Analyst", depth=1)
    assert "kg:person:analyst" in loaded[0]
    assert keyman["person_name"] == "Analyst"
    assert {node["id"] for node in keyman["nodes"]} == {
        "kg:document:DOC-1",
        "kg:person:analyst",
    }


def test_content_manifest_asset_and_evidence_fallbacks_remain_document_scoped(monkeypatch) -> None:
    """Return safe fallbacks when enrichment storage is unavailable and retain only document evidence."""
    app = _application(monkeypatch)
    monkeypatch.setattr(
        app,
        "_materialize_document_content",
        lambda _document_no: (_ for _ in ()).throw(RuntimeError("content storage unavailable")),
    )
    monkeypatch.setattr(
        lw,
        "ensure_content_inspection_tables",
        lambda _connection: (_ for _ in ()).throw(RuntimeError("inspection storage unavailable")),
    )
    manifest = app.content_manifest(ACTOR, "DOC-1")
    assert manifest == {
        "document_no": "DOC-1",
        "assets": [],
        "asset_count": 0,
        "inspections": [],
        "semantic_blocks": [],
        "semantic_block_count": 0,
    }

    monkeypatch.setattr(
        app,
        "_document_assets",
        lambda _document_no: [{"data_uri": "data:text/plain,fixture%20asset"}],
    )
    assert app.asset_bytes(ACTOR, "DOC-1", 0) == ("text/plain", b"fixture asset")
    with pytest.raises(KeyError):
        app.asset_bytes(ACTOR, "DOC-1", -1)

    monkeypatch.setattr(lw, "voc_evidence_guid_candidates", lambda *_args: ["missing", "also-missing"])
    row = {
        "guid_field": "ROW-FALLBACK",
        "docnosub_field": "DOC-1",
        "acthguid_field": "THREAD-1",
        "title_field": "Fixture evidence",
        "voctp_field": "opened",
        "ststs_field": "open",
        "dtsts_field": "active",
        "grade_field": "A",
        "bukrs_field": "CORP_A",
        "pucode_field": "PU_A",
        "userid_field": "fixture-account",
        "erdat_field": "2026-01-01",
        "erzet_field": "09:00:00",
        "aedat_field": "2026-01-02",
        "aezet_field": "10:00:00",
        "source_row_number": 7,
        "content_bytes": 12,
        "content_preview": "bounded text",
    }
    calls: list[tuple[object, ...]] = []

    def query(_connection, _sql, params=()):  # noqa: ANN001
        calls.append(tuple(params))
        return [row] if len(params) == 1 else []

    monkeypatch.setattr(lw, "_database_query", query)
    evidence = app.source_evidence(ACTOR, "DOC-1", "requested")
    assert evidence["evidence_id"] == "ROW-FALLBACK"
    assert evidence["created_at"] == "2026-01-01 09:00:00"
    assert calls[-1] == ("DOC-1",)
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    with pytest.raises(KeyError):
        app.source_evidence(ACTOR, "DOC-1", "requested")


def test_knowledge_falls_back_to_a_cold_authorized_graph_when_persisted_walks_are_empty(monkeypatch) -> None:
    """Keep a person lookup useful when the persisted KG neighborhood has not materialized yet."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    persisted = {
        "document": {
            "id": "doc:DOC-9",
            "document_no": "DOC-9",
            "corp_code": "CORP_A",
            "owner_pu": "PU_A",
            "visibility": "private",
        }
    }
    built_graph = {"nodes": [{"id": "kg:person:analyst"}], "edges": []}
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda *_args: persisted)
    monkeypatch.setattr(lw, "load_persisted_keyman_neighborhood", lambda *_args, **_kwargs: {"nodes": [], "edges": []})
    monkeypatch.setattr(lw, "load_persisted_knowledge_neighborhood", lambda *_args, **_kwargs: {"nodes": [], "edges": []})
    monkeypatch.setattr(
        app,
        "document",
        lambda *_args: {"document": persisted["document"], "edges": [], "knowledge_graph": {}},
    )
    monkeypatch.setattr(lw, "build_knowledge_graph", lambda *_args, **_kwargs: built_graph)
    monkeypatch.setattr(lw, "related_keyman_graph", lambda graph, person, **_kwargs: {"graph": graph, "person": person})

    assert app.knowledge(ACTOR, "DOC-9", {"person": ["Analyst"]}) == {
        "graph": built_graph,
        "person": "Analyst",
    }


def test_cold_content_materialization_persists_structure_without_attaching_a_process_graph(monkeypatch) -> None:
    """Avoid publishing a graph snapshot when a cold document read has no cached KG to update."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    structure = {"blocks": [{"block_index": 0, "text": "fixture"}], "assets": []}
    persisted: list[tuple[str, dict]] = []
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(app, "_document_content_structure", lambda _document_no: structure)
    monkeypatch.setattr(
        lw,
        "persist_document_content_structure",
        lambda _connection, document_no, value: persisted.append((document_no, value)),
    )
    monkeypatch.setattr(
        lw,
        "persist_knowledge_graph_snapshot",
        lambda *_args: pytest.fail("cold content materialization must not write a process graph snapshot"),
    )

    assert app._materialize_document_content("DOC-1") == structure
    assert persisted == [("DOC-1", structure)]


def test_document_returns_pending_work_when_queue_persistence_fails(monkeypatch) -> None:
    """Return the authorized document when the asynchronous work request cannot be queued."""
    class _CommitFailureConnection(_Connection):
        def commit(self):
            raise OSError("temporary write outage")

    app = _application(monkeypatch)
    document = app._payload["nodes"][0]
    document["todo_items"] = [{"source": "pending_llm"}]
    document["calendar_items"] = [{"source": "pending_llm"}]
    persisted: list[tuple[dict, dict]] = []
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _CommitFailureConnection())
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        lw,
        "persist_issue_work_items",
        lambda _connection, todo, calendar: persisted.append((todo, calendar)),
    )

    result = app.document(ACTOR, "DOC-1")

    assert result["document"]["todo_items"] == [{"source": "pending_llm"}]
    assert persisted == []
    assert app._document_work_inflight == set()


def test_document_schedules_pending_work_after_returning_the_detail(monkeypatch) -> None:
    """Send a pending detail immediately and run its LLM enrichment in the worker thread."""
    app = _application(monkeypatch)
    document = app._payload["nodes"][0]
    document["issue_tickets"] = [{"ticket_id": "ticket-1", "title": "Follow up"}]
    document["todo_items"] = [{"source": "pending_llm"}]
    document["calendar_items"] = [{"source": "pending_llm"}]
    events: list[tuple] = []
    persisted: list[tuple[dict, dict]] = []
    flushed: list[int] = []
    worker: list[object] = []
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(
        lw,
        "enqueue_event_outbox",
        lambda _connection, *args: events.append(args) or "event-1",
    )
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: flushed.append(1) or 1)
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(
        lw,
        "enrich_pending_document_work",
        lambda value, **_kwargs: {
            **value,
            "issue_tickets": [{"ticket_id": "ticket-1", "title": "Follow up", "status": "ready"}],
            "todo_items": [{"ticket_id": "ticket-1", "source": "live_llm"}],
            "calendar_items": [{"ticket_id": "ticket-1", "source": "live_llm"}],
        },
    )
    monkeypatch.setattr(
        lw,
        "persist_issue_work_items",
        lambda _connection, todo, calendar: persisted.append((todo, calendar)),
    )

    class _ImmediateThread:
        def __init__(self, target, args, **_kwargs):
            self.target = target
            self.args = args
            worker.append(self)

        def start(self):
            return None

    monkeypatch.setattr(server.threading, "Thread", _ImmediateThread)

    result = app.document(ACTOR, "DOC-1")

    assert result["document"]["todo_items"] == [{"source": "pending_llm"}]
    worker[0].target(*worker[0].args)
    assert events[0][0] == "document_work_enrichment_requested"
    assert events[0][1:] == (
        "DOC-1",
        "fixture-account",
        {"work": "issue_work_items", "document_no": "DOC-1"},
    )
    assert persisted == [
        (
            {"ticket_id": "ticket-1", "source": "live_llm"},
            {"ticket_id": "ticket-1", "source": "live_llm"},
        )
    ]
    assert flushed == [1, 1]
    assert app._payload["nodes"][0]["todo_items"] == [{"ticket_id": "ticket-1", "source": "live_llm"}]
    assert app._document_work_inflight == set()


def test_document_work_scheduler_deduplicates_inflight_requests(monkeypatch) -> None:
    """Do not start a second LLM request while the first document job is running."""
    app = _application(monkeypatch)
    events: list[tuple] = []
    starts: list[int] = []
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(
        lw,
        "enqueue_event_outbox",
        lambda _connection, *args: events.append(args) or "event-1",
    )
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 1)

    class _DeferredThread:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            starts.append(1)

    monkeypatch.setattr(server.threading, "Thread", _DeferredThread)
    document = app._payload["nodes"][0]

    app._schedule_document_work(ACTOR, document)
    app._schedule_document_work(ACTOR, document)

    assert len(events) == 1
    assert starts == [1]
    app._document_work_inflight.clear()


def test_document_work_worker_releases_inflight_state_when_model_is_unavailable(monkeypatch) -> None:
    """Release the deduplication marker even when the background model call fails."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    app._document_work_inflight.add("DOC-1")
    monkeypatch.setattr(
        lw,
        "resolve_product_transport",
        lambda: (_ for _ in ()).throw(RuntimeError("gateway unavailable")),
    )

    app._run_document_work({"document_no": "DOC-1"})

    assert app._document_work_inflight == set()


def test_document_work_worker_handles_cold_and_missing_cached_documents(monkeypatch) -> None:
    """Persist successful work even when the process cache is cold or lacks the document."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "enrich_pending_document_work", lambda value, **_kwargs: dict(value))
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 1)

    app._document_work_inflight.add("DOC-1")
    app._run_document_work({"document_no": "DOC-1"})
    assert app._document_work_inflight == set()

    app._payload = {"nodes": []}
    app._document_work_inflight.add("DOC-1")
    app._run_document_work({"document_no": "DOC-1"})
    assert app._document_work_inflight == set()


def test_document_work_worker_handles_missing_payload_and_missing_cached_node(monkeypatch) -> None:
    """Persist completed work even when no matching in-memory cache entry exists."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(
        lw,
        "enrich_pending_document_work",
        lambda value, **_kwargs: {**value, "todo_items": [], "calendar_items": []},
    )
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 0)

    app._document_work_inflight.add("DOC-1")
    app._run_document_work({"document_no": "DOC-1"})
    app._payload = {"nodes": []}
    app._document_work_inflight.add("DOC-2")
    app._run_document_work({"document_no": "DOC-2"})

    assert app._document_work_inflight == set()


def test_content_manifest_ignores_an_inspection_for_a_different_asset_revision(monkeypatch) -> None:
    """Do not expose stale OCR or labels after the source asset changes at the same index."""
    app = _application(monkeypatch)
    asset = {
        "asset_index": 0,
        "source_position": 1,
        "row_guid": "ROW-1",
        "source_row_number": "1",
        "mime_type": "image/png",
        "data_uri": "data:image/png;base64,Zm9v",
        "encoded_bytes": 3,
        "content_kind": lw.CONTENT_INLINE_IMAGE,
    }
    asset["asset_sha256"] = lw.content_asset_sha256(asset)
    monkeypatch.setattr(app, "_materialize_document_content", lambda _document_no: {"blocks": [], "assets": [asset]})
    monkeypatch.setattr(lw, "ensure_content_inspection_tables", lambda _connection: None)
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda _connection, sql, _params=(): [
            {"asset_index": 0, "asset_sha256": "stale", "ocr_text": "old OCR"}
        ]
        if "analysis_content_inspections" in sql
        else [],
    )

    manifest = app.content_manifest(ACTOR, "DOC-1")

    assert manifest["inspections"] == []
    assert "inspection" not in manifest["assets"][0]


def test_cold_report_build_does_not_require_an_unrelated_cached_payload(monkeypatch) -> None:
    """Persist a first report slice when a process has no existing graph snapshot yet."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    documents = [{"type": "document", "document_no": "DOC-1", "corp_code": "CORP_A", "owner_pu": "PU_A"}]
    scored = [{"report_id": "report-1", "slice_key": "DOC-1", "linked_scores": []}]
    persisted: list[dict] = []
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "load_period_reports", lambda _connection: [])
    monkeypatch.setattr(lw, "load_authorized_report_document_numbers", lambda _connection, _actor: {"DOC-1"})
    monkeypatch.setattr(app, "filtered_payload", lambda _actor: {"nodes": documents})
    monkeypatch.setattr(lw, "build_period_report_slices", lambda rows: [{"slice_key": rows[0]["document_no"]}])
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (None, "not_configured"))
    monkeypatch.setattr(lw, "resolve_mlsirm_transport", lambda: (None, "not_configured"))
    monkeypatch.setattr(lw, "score_period_reports", lambda *_args, **_kwargs: scored)
    monkeypatch.setattr(lw, "persist_period_reports", lambda _connection, rows: persisted.extend(rows))

    result = app.reports(ACTOR)

    assert result["source"] == "built"
    assert persisted == scored
    assert app._payload is None


def test_cold_document_preserves_a_persisted_event_lineage_without_rebuilding_it(monkeypatch) -> None:
    """Keep a direct-PostgreSQL event lineage immutable when it was already materialized."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    event_lineage = {"beads": [{"id": "event:1", "kind": "observed"}], "links": []}
    detail = {
        "document": {
            "id": "doc:DOC-1",
            "document_no": "DOC-1",
            "corp_code": "CORP_A",
            "owner_pu": "PU_A",
            "visibility": "private",
        },
        "rows": [],
        "edges": [],
        "knowledge_graph": {"nodes": [{"id": "kg:document:DOC-1"}], "edges": []},
        "event_lineage": event_lineage,
    }
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda *_args: detail)
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(lw, "build_event_lineage", lambda *_args, **_kwargs: pytest.fail("persisted event lineage must be reused"))

    assert app.document(ACTOR, "DOC-1")["event_lineage"] is event_lineage


def test_cold_knowledge_and_chat_reuse_a_persisted_nonempty_graph(monkeypatch) -> None:
    """Avoid rebuilding a graph when direct PostgreSQL already returned the authorized semantic slice."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    detail = {
        "document": {
            "id": "doc:DOC-1",
            "document_no": "DOC-1",
            "corp_code": "CORP_A",
            "owner_pu": "PU_A",
            "visibility": "private",
            "title_sample": "Fixture event",
        },
        "rows": [{"guid": "ROW-1", "event": "open"}],
        "edges": [],
        "knowledge_graph": {"nodes": [{"id": "kg:document:DOC-1", "type": "document"}], "edges": []},
        "event_lineage": {"beads": []},
    }
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda *_args: detail)
    monkeypatch.setattr(lw, "load_persisted_knowledge_neighborhood", lambda *_args, **_kwargs: {"nodes": [], "edges": [], "depths": {}})
    monkeypatch.setattr(app, "document", lambda *_args: detail)
    monkeypatch.setattr(lw, "build_knowledge_graph", lambda *_args, **_kwargs: pytest.fail("existing graph must not rebuild"))
    monkeypatch.setattr(lw, "related_knowledge_graph", lambda graph, document_no, **_kwargs: {"graph": graph, "document_no": document_no})
    assert app.knowledge(ACTOR, "DOC-1", {}) == {
        "graph": detail["knowledge_graph"],
        "document_no": "DOC-1",
    }

    monkeypatch.setattr(app, "_materialize_document_content", lambda _document_no: {"blocks": [], "assets": []})
    monkeypatch.setattr(lw, "load_knowledge_semantic_context", lambda *_args: {"node_terms": [{"node_id": "kg:document:DOC-1"}], "edge_assertions": []})
    monkeypatch.setattr(lw, "load_document_content_structure", lambda *_args: {"blocks": [], "assets": []})
    monkeypatch.setattr(lw, "live_http_config", lambda: ("https://gateway.example", "fixture", "model"))
    monkeypatch.setattr(lw, "post_lineage_chat", lambda *_args, **_kwargs: {"answer": "확인됨", "evidence_ids": ["ROW-1"]})
    chat = app.chat(ACTOR, "DOC-1", "무슨 일이 있었나요?")
    assert chat["evidence_ids"] == ["ROW-1"]


def test_ticket_status_transition_is_authorized_persisted_and_cached(monkeypatch) -> None:
    """Keep ticket and To Do state synchronized through the direct PostgreSQL outbox path."""
    app = _application(monkeypatch)
    document = next(node for node in app._payload["nodes"] if node["type"] == "document")
    document["issue_tickets"] = [
        {"ticket_id": "ticket-1", "status": "open"},
        {"ticket_id": "ticket-other", "status": "open"},
    ]
    document["todo_items"] = [
        {"ticket_id": "ticket-1", "status": "open"},
        {"ticket_id": "ticket-other", "status": "open"},
    ]
    writes: list[tuple[str, tuple[object, ...]]] = []
    events: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda *_args, **_kwargs: [
            {
                "ticket_id": "ticket-1",
                "document_no": "DOC-1",
                "title": "Fixture ticket",
                "status": "open",
                "assignee": None,
                "created_by": "fixture-account",
            }
        ],
    )
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): writes.append((sql, tuple(params))),
    )
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 1)

    updated = app.update_ticket(ACTOR, "DOC-1", "ticket-1", {"status": "resolved"})

    assert updated["status"] == "resolved"
    assert document["issue_tickets"][0]["status"] == "resolved"
    assert document["issue_tickets"][1]["status"] == "open"
    assert document["todo_items"][0]["status"] == "resolved"
    assert document["todo_items"][1]["status"] == "open"
    assert any(f"UPDATE {lw.ANALYSIS_TICKET_TABLE}" in sql for sql, _params in writes)
    assert any(f"UPDATE {lw.ANALYSIS_TODO_TABLE}" in sql for sql, _params in writes)
    assert events == [
        (
            "issue_ticket_changed",
            "DOC-1",
            "fixture-account",
            {"ticket_id": "ticket-1", "status": "resolved"},
        )
    ]
    with pytest.raises(ValueError, match="unknown ticket status"):
        app.update_ticket(ACTOR, "DOC-1", "ticket-1", {"status": "unknown"})
    original_authorize = lw.authorize_access
    monkeypatch.setattr(app, "document", lambda *_args: {"document": document})
    monkeypatch.setattr(lw, "authorize_access", lambda **_kwargs: {"allowed": False, "reason": "ticket_forbidden"})
    with pytest.raises(PermissionError, match="ticket_forbidden"):
        app.update_ticket(ACTOR, "DOC-1", "ticket-1", {"status": "open"})
    monkeypatch.setattr(lw, "authorize_access", original_authorize)
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    with pytest.raises(KeyError, match="missing-ticket"):
        app.update_ticket(ACTOR, "DOC-1", "missing-ticket", {"status": "open"})
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda *_args, **_kwargs: [{
            "ticket_id": "ticket-1",
            "document_no": "DOC-1",
            "title": "Fixture ticket",
            "status": "open",
            "assignee": None,
            "created_by": "fixture-account",
        }],
    )
    app._payload = {"nodes": []}
    assert app.update_ticket(ACTOR, "DOC-1", "ticket-1", {"status": "open"})["status"] == "open"
    app._payload = None
    assert app.update_ticket(ACTOR, "DOC-1", "ticket-1", {"status": "resolved"})["status"] == "resolved"
