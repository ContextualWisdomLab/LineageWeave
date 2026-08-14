"""Exercise document, KG, content, and mutation methods through the actual server implementation."""

from __future__ import annotations

import base64

import pytest

import lineageweave as lw
import lineageweave_server as server


ACTOR = {"account_id": "account-1", "corp_code": "CORP_A", "pu_code": "PU_A", "roles": ["admin"]}


class _Connection:
    """Provide the direct PostgreSQL context-manager boundary for method tests."""

    def __enter__(self) -> "_Connection":
        """Enter the database context."""
        return self

    def __exit__(self, *_args: object) -> bool:
        """Do not hide persistence errors."""
        return False


def _payload() -> dict[str, object]:
    """Return a compact, actor-visible graph spanning documents, rows, and a Keyman node."""
    document = {
        "id": "doc:DOC-1", "type": "document", "document_no": "DOC-1", "acthguid": "THREAD-1",
        "corp_code": "CORP_A", "owner_pu": "PU_A", "visibility": "private", "title_sample": "Fixture",
        "last_row_ts": "2026-01-02T00:00:00", "first_row_ts": "2026-01-01T00:00:00", "row_count": 1,
        "entity_role": "시장", "keyman_our_side": [{"person_name": "Ana", "org_name": "Org A"}],
        "keyman_counterpart_side": [{"person_name": "Bo", "org_name": "Org B"}], "issue_tickets": [],
    }
    row = {
        "id": "row:ROW-1", "type": "row", "document_no": "DOC-1", "guid": "ROW-1", "event": "opened",
        "stage": "open", "timestamp": "2026-01-01T00:00:00", "corp_code": "CORP_A", "owner_pu": "PU_A",
    }
    return {
        "metadata": {"row_count": 1}, "analytics": {}, "nodes": [document, row],
        "edges": [{"source": "doc:DOC-1", "target": "row:ROW-1", "relation": "observed", "acthguid": "THREAD-1"}],
        "knowledge_graph": {
            "nodes": [
                {"id": "kg:document:DOC-1", "type": "document", "label": "Fixture", "document_no": "DOC-1", "document_nos": ["DOC-1"]},
                {"id": "kg:person:ana", "type": "person", "label": "Ana", "document_nos": ["DOC-1"]},
            ],
            "edges": [{"source": "kg:document:DOC-1", "target": "kg:person:ana", "relation": "keyman_our_side", "evidence_id": "ROW-1"}],
        },
    }


def _application(monkeypatch) -> server.LineageApplication:
    """Create a server application backed by a stable in-memory payload and direct connection double."""
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    app._payload = _payload()
    monkeypatch.setattr(lw, "filter_payload_for_actor", lambda payload, _actor: payload)
    return app


def test_document_knowledge_content_and_evidence_data_flow(monkeypatch) -> None:
    """Serve the popup data path, bounded asset bytes, OCR search, and evidence drawer."""
    app = _application(monkeypatch)
    png = base64.b64encode(b"\x89PNG\r\n\x1a\nfixture").decode("ascii")
    source_asset = f"data:image/png;base64,{png}"
    asset_sha = lw.content_asset_sha256({"data_uri": source_asset})

    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if "content_preview" in sql:
            return [{"guid_field": "ROW-1", "docnosub_field": "DOC-1", "acthguid_field": "THREAD-1", "title_field": "Fixture", "voctp_field": "opened", "ststs_field": "open", "dtsts_field": "active", "grade_field": "A", "bukrs_field": "CORP_A", "pucode_field": "PU_A", "userid_field": "account-1", "erdat_field": "2026-01-01", "erzet_field": "10:00", "aedat_field": "2026-01-02", "aezet_field": "11:00", "source_row_number": "1", "content_bytes": len(source_asset), "content_preview": "fixture"}]
        if "voccts_field" in sql:
            return [{"guid_field": "ROW-1", "source_row_number": "1", "voccts_field": source_asset}]
        if "GROUP BY inspection.document_no" in sql:
            return [{"document_no": "DOC-1", "asset_index": 0, "mime_type": "image/png", "ocr_text": "fixture", "inspected_at": "2026-01-01", "object_labels": []}]
        if "inspection_label" in sql:
            return [{"asset_index": 0, "label_name": "chart", "label_description": "fixture chart", "label_position": 1}]
        if lw.ANALYSIS_INSPECTION_TABLE in sql:
            return [{"asset_index": 0, "asset_sha256": asset_sha, "ocr_text": "fixture", "mime_type": "image/png", "source_evidence_id": "ROW-1", "source_row_number": "1", "source_position": 0, "model_name": "vision", "inspected_by": "account-1", "inspected_at": "2026-01-01"}]
        return []

    monkeypatch.setattr(lw, "_database_query", query)
    monkeypatch.setattr(
        lw,
        "load_visible_document_index",
        lambda *_args, **_kwargs: {"items": [{"document_no": "DOC-1"}], "total": 1},
    )
    monkeypatch.setattr(lw, "ensure_content_inspection_tables", lambda _connection: None)
    monkeypatch.setattr(
        app,
        "_materialize_document_content",
        lambda _document_no: {
            "blocks": [
                {
                    "block_index": 0,
                    "source_evidence_id": "ROW-1",
                    "source_row_number": "1",
                    "block_kind": "text",
                    "source_position": 0,
                    "text_content": "fixture",
                    "text_sha256": "a" * 64,
                    "format_hints": [],
                }
            ],
            "assets": [
                {
                    "asset_index": 0,
                    "source_evidence_id": "ROW-1",
                    "source_row_number": "1",
                    "source_position": 0,
                    "mime_type": "image/png",
                    "encoded_bytes": len(png),
                    "content_kind": lw.CONTENT_INLINE_IMAGE,
                    "asset_sha256": asset_sha,
                    "inspection_eligible": True,
                }
            ],
        },
    )
    detail = app.document(ACTOR, "DOC-1")
    assert detail["rows"][0]["guid"] == "ROW-1"
    assert app.document_index(ACTOR, 5)["items"][0]["document_no"] == "DOC-1"
    assert app.knowledge(ACTOR, "DOC-1", {"person": ["Ana"], "depth": ["2"]})["nodes"]
    manifest = app.content_manifest(ACTOR, "DOC-1")
    assert manifest["inspections"][0]["object_labels"] == [{"label": "chart", "description": "fixture chart"}]
    assert app.asset_bytes(ACTOR, "DOC-1", 0) == ("image/png", b"\x89PNG\r\n\x1a\nfixture")
    assert app.image_search(ACTOR, "fixture")["items"][0]["document_no"] == "DOC-1"
    assert app.source_evidence(ACTOR, "DOC-1", "ROW-1")["content_preview"] == "fixture"


def test_keyman_chat_inspection_and_mutation_data_flow(monkeypatch) -> None:
    """Persist authorized live-model actions and update the cached product graph after each mutation."""
    app = _application(monkeypatch)
    asset = {
        "asset_index": 0, "row_guid": "ROW-1", "source_row_number": "1", "source_position": 0,
        "mime_type": "image/png", "data_uri": "data:image/png;base64,iVBORw0KGgpmaXh0dXJl",
    }
    asset["asset_sha256"] = lw.content_asset_sha256(asset)
    writes: list[str] = []
    monkeypatch.setattr(app, "_document_assets", lambda _document_no: [asset])
    content_structure = {
        "blocks": [
            {
                "block_index": 0,
                "source_evidence_id": "ROW-1",
                "source_row_number": "1",
                "block_kind": "paragraph",
                "source_position": 0,
                "text_content": "fixture context",
                "text_sha256": "a" * 64,
                "format_hints": [],
            }
        ],
        "assets": [],
    }
    monkeypatch.setattr(app, "_materialize_document_content", lambda _document_no: content_structure)
    monkeypatch.setattr(lw, "load_document_content_structure", lambda *_args: content_structure)
    monkeypatch.setattr(lw, "_database_exec", lambda _connection, sql, _params=(): writes.append(sql))
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda *_args, **_kwargs: "event")
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 1)
    monkeypatch.setattr(lw, "build_knowledge_graph", lambda *_args, **_kwargs: {"nodes": [], "edges": []})
    monkeypatch.setattr(lw, "persist_knowledge_graph_snapshot", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(lw, "resolve_keyman_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    reader = {**ACTOR, "roles": ["reader"]}
    with pytest.raises(PermissionError):
        app.derive_keymen(reader, "DOC-1")
    monkeypatch.setattr(
        lw,
        "derive_keymen_via_llm",
        lambda *_args, **_kwargs: {
            "our_side": [],
            "counterpart_side": [],
            "names": [],
            "source": "none",
            "status": "empty",
            "orchestration": {},
        },
    )
    with pytest.raises(ValueError, match="live model returned no Keyman"):
        app.derive_keymen(ACTOR, "DOC-1")
    monkeypatch.setattr(lw, "derive_keymen_via_llm", lambda *_args, **_kwargs: {"our_side": [{"person_name": "Ana", "org_name": "Org A"}], "counterpart_side": [{"person_name": "Bo", "org_name": "Org B"}], "names": ["Ana", "Bo"], "source": "llm", "status": "ready", "orchestration": {}})
    assert app.derive_keymen(ACTOR, "DOC-1")["keyman"]["names"] == ["Ana", "Bo"]
    monkeypatch.setattr(lw, "live_http_config", lambda: ("https://gateway.example", "token", "model"))
    semantic_context = {"node_terms": [{"term_label": "CreativeWork"}], "edge_assertions": []}
    monkeypatch.setattr(lw, "load_knowledge_semantic_context", lambda *_args, **_kwargs: semantic_context)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        lw,
        "post_lineage_chat",
        lambda body, **_kwargs: captured.update(body) or {"answer": "opened", "evidence_ids": ["ROW-1"]},
    )
    assert app.chat(ACTOR, "DOC-1", "what happened?")["evidence_ids"] == ["ROW-1"]
    assert captured["context"]["semantic_layer"] == semantic_context
    monkeypatch.setattr(lw, "derive_content_inspection_via_llm", lambda *_args, **_kwargs: {"asset_sha256": asset["asset_sha256"], "ocr_text": "fixture", "object_labels": ["chart"], "model_name": "vision"})
    monkeypatch.setattr(lw, "persist_content_inspection", lambda *_args, **_kwargs: None)
    assert app.inspect_content_asset(ACTOR, "DOC-1", 0)["transport"] == "live_http"
    monkeypatch.setattr(lw, "persist_visibility", lambda *_args, **_kwargs: None)
    assert app.set_visibility(ACTOR, "DOC-1", "public")["visibility"] == "public"
    assert app.set_keymen(ACTOR, "DOC-1", {"our_side": ["Ana"], "counterpart_side": ["Bo"]})["our_side"][0]["person_name"] == "Ana"
    assert app.create_ticket(ACTOR, "DOC-1", {"title": "Follow up"})["status"] == "open"
    assert writes


def test_chat_fails_closed_without_authorized_semantic_rows(monkeypatch) -> None:
    """Do not send an event-chat prompt when the semantic DB cannot ground it."""
    app = _application(monkeypatch)
    monkeypatch.setattr(app, "_materialize_document_content", lambda _document_no: {"blocks": [], "assets": []})
    monkeypatch.setattr(lw, "load_document_content_structure", lambda *_args: {"blocks": [], "assets": []})
    monkeypatch.setattr(
        lw,
        "load_knowledge_semantic_context",
        lambda *_args, **_kwargs: {"node_terms": [], "edge_assertions": []},
    )
    with pytest.raises(RuntimeError, match="knowledge_semantic_context_unavailable"):
        app.chat(ACTOR, "DOC-1", "what happened?")


def test_chat_validates_questions_and_uses_the_configured_worker_fallback(monkeypatch) -> None:
    """Preserve bounded input validation when direct live-gateway settings are unavailable."""
    app = _application(monkeypatch)
    with pytest.raises(ValueError, match="message is required"):
        app.chat(ACTOR, "DOC-1", "  ")
    with pytest.raises(ValueError, match="message is too long"):
        app.chat(ACTOR, "DOC-1", "x" * 4001)

    monkeypatch.setattr(app, "_materialize_document_content", lambda _document_no: {"blocks": [], "assets": []})
    monkeypatch.setattr(lw, "load_document_content_structure", lambda *_args: {"blocks": [], "assets": []})
    monkeypatch.setattr(
        lw,
        "load_knowledge_semantic_context",
        lambda *_args, **_kwargs: {"node_terms": [{"term_label": "CreativeWork"}], "edge_assertions": []},
    )
    monkeypatch.setattr(
        lw,
        "live_http_config",
        lambda: (_ for _ in ()).throw(RuntimeError("gateway_not_configured")),
    )
    ensured: list[bool] = []
    captured: dict[str, object] = {}
    monkeypatch.setattr(lw, "ensure_compose_standin", lambda: ensured.append(True) or "live_url_present")
    monkeypatch.setattr(
        lw,
        "compose_standin_transport",
        lambda body: captured.update(body) or {"answer": "Worker grounded response", "evidence_ids": ["ROW-1"]},
    )

    response = app.chat(ACTOR, "DOC-1", "What changed?")
    assert ensured == [True]
    assert captured["task"] == "event_lineage_chat"
    assert response["answer"] == "Worker grounded response"
    assert response["evidence_ids"] == ["ROW-1"]


def test_cold_chat_rebuilds_its_authorized_graph_scope_before_model_call(monkeypatch) -> None:
    """A restarted service must rebuild only the requested document's semantic scope."""
    app = _application(monkeypatch)
    app._payload = None
    detail = {
        "document": {
            "id": "doc:DOC-1",
            "type": "document",
            "document_no": "DOC-1",
            "title_sample": "Cold-start fixture",
            "entity_role": "시장",
        },
        "edges": [],
        "knowledge_graph": {"nodes": [], "edges": []},
    }
    semantic_ids: list[list[str]] = []
    captured: dict[str, object] = {}
    monkeypatch.setattr(app, "document", lambda _actor, _document_no: detail)
    monkeypatch.setattr(app, "_materialize_document_content", lambda _document_no: {"blocks": [], "assets": []})
    monkeypatch.setattr(lw, "build_knowledge_graph", lambda *_args: {"nodes": [], "edges": []})
    monkeypatch.setattr(
        lw,
        "load_knowledge_semantic_context",
        lambda _connection, node_ids: semantic_ids.append(node_ids)
        or {"node_terms": [{"term_label": "CreativeWork"}], "edge_assertions": []},
    )
    monkeypatch.setattr(lw, "load_document_content_structure", lambda *_args: {"blocks": [], "assets": []})
    monkeypatch.setattr(lw, "live_http_config", lambda: ("https://gateway.example", "token", "model"))
    monkeypatch.setattr(
        lw,
        "post_lineage_chat",
        lambda body, **_kwargs: captured.update(body) or {"answer": "Cold-start answer", "evidence_ids": []},
    )

    response = app.chat(ACTOR, "DOC-1", "What changed?")

    assert semantic_ids == [["kg:document:DOC-1"]]
    assert captured["document_no"] == "DOC-1"
    assert response["answer"] == "Cold-start answer"


def test_inference_verification_rejects_actor_without_lineage_permission(monkeypatch) -> None:
    """A reader cannot cause an external evidence-verification model request."""
    app = _application(monkeypatch)

    with pytest.raises(PermissionError, match="rbac_role"):
        app.verify_lineage_inferences({**ACTOR, "roles": ["reader"]}, "DOC-1")
