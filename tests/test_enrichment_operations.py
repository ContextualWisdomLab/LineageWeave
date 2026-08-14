"""Exercise the bounded administrator LLM enrichment operation boundary."""

from __future__ import annotations

import json

import pytest

import lineageweave as lw
import lineageweave_server as server


ACTOR = {"account_id": "admin-1", "corp_code": "CORP_A", "pu_code": "PU_A", "roles": ["admin"]}


class _Cursor:
    """Capture bulk writes without replacing the PostgreSQL connection boundary."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def executemany(self, statement, rows) -> None:
        self.calls.append((statement, list(rows)))


class _Connection:
    """Small context manager used by the direct PostgreSQL operation tests."""

    def __init__(self) -> None:
        self.cursor_value = _Cursor()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def commit(self) -> None:
        return None

    def cursor(self):
        return self.cursor_value


def _document_payload() -> dict:
    """Return one small persisted-looking document and its cache node."""
    document = {
        "id": "doc:DOC-1",
        "type": "document",
        "document_no": "DOC-1",
        "corp_code": "CORP_A",
        "owner_pu": "PU_A",
        "visibility": "public",
        "title_sample": "Fixture customer meeting",
        "korean_summary": "요약",
        "issue_tickets": [{"ticket_id": "ticket-1", "title": "후속 확인", "status": "open"}],
        "appointments": [],
    }
    return {"nodes": [document], "knowledge_graph": {"nodes": [], "edges": []}}


def _application() -> server.LineageApplication:
    """Create an application with a compact in-memory cache."""
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    app._payload = _document_payload()
    return app


def test_enrichment_scope_and_candidate_selection_cover_each_task(monkeypatch) -> None:
    """Select deduplicated pending documents inside the admin and reader scopes."""
    app = _application()
    assert app._enrichment_scope(ACTOR)[0] == "d.corp_code = %s"
    assert "visibility_code" in app._enrichment_scope({**ACTOR, "roles": ["reader"]})[0]
    with pytest.raises(ValueError, match="corp_required"):
        app._enrichment_scope({"roles": ["admin"]})

    def query(_connection, statement, _params=()):
        if "COALESCE(d.keyman_source" in statement:
            return [{"document_no": "KEY"}, {"document_no": "SHARED"}]
        if "todo.content_source" in statement:
            return [{"document_no": "PRODUCT"}, {"document_no": "SHARED"}]
        if "appointment.content_source" in statement:
            return [{"document_no": "APPOINTMENT"}, {"document_no": "SHARED"}]
        return []

    monkeypatch.setattr(lw, "_database_query", query)
    connection = _Connection()
    assert app._enrichment_candidates(connection, ACTOR, "keyman", 8) == ["KEY", "SHARED"]
    assert app._enrichment_candidates(connection, ACTOR, "product", 8) == ["PRODUCT", "SHARED"]
    assert app._enrichment_candidates(connection, ACTOR, "appointments", 8) == ["APPOINTMENT", "SHARED"]
    assert app._enrichment_candidates(connection, ACTOR, "all", 3) == ["KEY", "SHARED", "PRODUCT"]


def test_enrichment_status_is_bounded_and_reports_active_and_last_run(monkeypatch) -> None:
    """Expose pending counts without returning document content or graph bytes."""
    app = _application()
    app._enrichment_inflight["run-1"] = {"run_id": "run-1", "task": "keyman", "requested": 2}
    connection = _Connection()
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)

    def query(_connection, statement, _params=()):
        if "COALESCE(d.keyman_source" in statement:
            return [{"total": 2}]
        if "content_source = 'pending_llm'" in statement:
            return [{"total": 3}]
        if "content_source = 'extract'" in statement:
            return [{"total": 4}]
        return [{"event_type": "llm_enrichment_batch_completed", "payload": json.dumps({"run_id": "run-1"}), "published_at": None, "created_at": "now"}]

    monkeypatch.setattr(lw, "_database_query", query)
    result = app.enrichment_status(ACTOR)
    assert result["pending"] == {"keyman": 2, "product": 3, "appointments": 4}
    assert result["active_runs"][0]["run_id"] == "run-1"
    assert result["last_run"]["run_id"] == "run-1"

    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda *_args, **_kwargs: [
            {
                "event_type": "llm_enrichment_batch_completed",
                "payload": {"run_id": "run-2"},
                "published_at": "now",
                "created_at": "now",
            }
        ],
    )
    assert app.enrichment_status(ACTOR)["last_run"]["run_id"] == "run-2"

    monkeypatch.setattr(
        lw,
        "_database_table_exists",
        lambda _connection, table: table == lw.ANALYSIS_EVENT_OUTBOX_TABLE,
    )
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    assert app.enrichment_status(ACTOR)["last_run"] is None

    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: False)
    app._enrichment_inflight.clear()
    assert app.enrichment_status(ACTOR) == {"pending": {"keyman": 0, "product": 0, "appointments": 0}, "active_runs": [], "last_run": None}

    with pytest.raises(PermissionError, match="keyverse_admin_required"):
        app.enrichment_status({**ACTOR, "roles": ["reader"]})


def test_keyman_batch_persists_model_abstention_without_fabricating_people(monkeypatch) -> None:
    """Keep an empty live response explicit while preserving the KG refresh path."""
    app = _application()
    connection = _Connection()
    events: list[tuple[object, ...]] = []
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(lw, "ensure_keyman_override_columns", lambda _connection: None)
    monkeypatch.setattr(lw, "_database_exec", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    monkeypatch.setattr(lw, "refresh_document_keyman_knowledge_graph", lambda graph, _node: graph)
    monkeypatch.setattr(lw, "persist_knowledge_graph_snapshot", lambda *_args: None)
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 0)

    derived = {"our_side": [{"person_name": "우리 담당"}], "counterpart_side": [], "names": ["우리 담당"], "source": "llm", "status": "orchestrator", "orchestration": {}}
    updated = app._persist_keyman_result(ACTOR, "DOC-1", app._payload["nodes"][0], derived, "live_http")
    assert updated["keyman_source"] == "llm"
    assert events[-1][0] == "keyman_derived"

    with pytest.raises(ValueError, match="no Keyman"):
        app._persist_keyman_result(
            ACTOR,
            "DOC-1",
            app._payload["nodes"][0],
            {"our_side": [], "counterpart_side": [], "names": [], "source": "none", "status": "empty", "orchestration": {}},
            "live_http",
        )
    abstained = app._persist_keyman_result(
        ACTOR,
        "DOC-1",
        app._payload["nodes"][0],
        {"our_side": [], "counterpart_side": [], "names": [], "source": "none", "status": "empty", "orchestration": {}},
        "live_http",
        allow_empty=True,
    )
    assert abstained["keyman_status"] == "empty"
    assert abstained["keyman_our_side"] == []
    assert events[-1][-1]["abstained"] is True

    app._payload = None
    uncached = app._persist_keyman_result(ACTOR, "DOC-1", {"document_no": "DOC-1"}, derived, "live_http")
    assert uncached["keyman_status"] == "orchestrator"


def test_product_batch_persists_rr_work_and_appointments(monkeypatch) -> None:
    """Persist model-authored operational fields while retaining source markers."""
    app = _application()
    connection = _Connection()
    writes: list[tuple[object, ...]] = []
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)
    monkeypatch.setattr(lw, "_database_exec", lambda _connection, statement, params=(): writes.append((statement, params)))
    monkeypatch.setattr(lw, "persist_issue_work_items", lambda _connection, todo, calendar: writes.append((todo, calendar)))
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: writes.append(args))
    monkeypatch.setattr(lw, "derive_entity_role_via_llm", lambda _document, **_kwargs: {"entity_role": "고객", "source": "llm", "confidence": 0.88})
    monkeypatch.setattr(lw, "derive_roles_and_responsibilities_via_llm", lambda _document, transport: [{"source": "llm", "role": "담당", "responsibility": "확인"}])
    monkeypatch.setattr(lw, "enrich_pending_document_work", lambda document, transport: {**document, "issue_tickets": document["issue_tickets"], "todo_items": [{"todo_id": "todo-1", "source": "llm"}], "calendar_items": [{"calendar_id": "cal-1", "source": "llm"}]})
    monkeypatch.setattr(lw, "derive_appointments_via_llm", lambda *args, **kwargs: [{"appointment_id": "apt-1", "occurred_on": "2026-08-14", "label": "약속", "excerpt": "확인", "source": "llm"}])
    document = app._payload["nodes"][0]
    app._persist_product_enrichment(ACTOR, document, lambda _body: {}, include_appointments=False)
    app._persist_product_enrichment(ACTOR, document, lambda _body: {}, include_appointments=True)
    assert any(item[0].get("todo_id") == "todo-1" for item in writes if isinstance(item[0], dict))
    assert app._payload["nodes"][0]["entity_role"] == "고객"
    assert app._payload["nodes"][0]["entity_role_source"] == "llm"
    assert app._payload["nodes"][0]["roles_and_responsibilities"][0]["source"] == "llm"
    assert app._payload["nodes"][0]["appointments"][0]["source"] == "llm"

    monkeypatch.setattr(lw, "derive_entity_role_via_llm", lambda _document, **_kwargs: {"source": "llm_abstention", "confidence": 0.0})
    app._persist_product_enrichment(ACTOR, document, lambda _body: {}, include_appointments=False)

    app._payload = None
    app._persist_product_enrichment(ACTOR, document, lambda _body: {}, include_appointments=False)


def test_enrichment_batch_and_queue_validation(monkeypatch) -> None:
    """Cover successful, failed, empty, and malformed bounded batch requests."""
    app = _application()
    connection = _Connection()
    events: list[tuple[object, ...]] = []
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(lw, "resolve_keyman_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda _connection, _document_no, **_kwargs: {"document": app._payload["nodes"][0]})
    monkeypatch.setattr(lw, "derive_keymen_via_llm", lambda *args, **kwargs: {"our_side": [], "counterpart_side": [], "names": [], "source": "none", "status": "empty", "orchestration": {}})
    monkeypatch.setattr(app, "_persist_keyman_result", lambda *args, **kwargs: {})
    monkeypatch.setattr(app, "_persist_product_enrichment", lambda *args, **kwargs: None)
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    monkeypatch.setattr(app, "_flush_event_outbox", lambda: 0)
    app._run_enrichment_batch(ACTOR, "all", ["DOC-1"], "run-all")
    assert events[-1][0] == "llm_enrichment_batch_completed"
    assert events[-1][-1]["abstained"] == 1
    assert not app._enrichment_inflight

    monkeypatch.setattr(lw, "resolve_keyman_transport", lambda: (_ for _ in ()).throw(RuntimeError("missing")))
    app._enrichment_inflight["run-fail"] = {"run_id": "run-fail"}
    app._run_enrichment_batch(ACTOR, "keyman", ["DOC-1"], "run-fail")
    assert not app._enrichment_inflight

    monkeypatch.setattr(lw, "resolve_keyman_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda _connection, _document_no, **_kwargs: {"document": app._payload["nodes"][0]})
    app._run_enrichment_batch(ACTOR, "keyman", ["DOC-1"], "run-keyman")
    app._run_enrichment_batch(ACTOR, "appointments", ["DOC-1"], "run-appointments")
    monkeypatch.setattr(lw, "load_persisted_document_detail", lambda *_args, **_kwargs: None)
    app._run_enrichment_batch(ACTOR, "product", ["DOC-1"], "run-product")
    assert events[-1][-1]["failed"] == 1

    monkeypatch.setattr(
        lw,
        "load_persisted_document_detail",
        lambda *_args, **_kwargs: {"document": {**app._payload["nodes"][0], "corp_code": "OTHER_CORP"}},
    )
    app._run_enrichment_batch(ACTOR, "product", ["DOC-1"], "run-scope")
    assert events[-1][-1]["failed"] == 1

    monkeypatch.setattr(app, "_enrichment_candidates", lambda *_args: [])
    empty = app.run_enrichment(ACTOR, {"task": "keyman", "limit": 2})
    assert empty["status"] == "empty"
    monkeypatch.setattr(app, "_enrichment_candidates", lambda *_args: ["DOC-1"])
    started: list[tuple[object, ...]] = []

    class _Thread:
        def __init__(self, **kwargs) -> None:
            started.append((kwargs["target"], kwargs["args"]))

        def start(self) -> None:
            return None

    monkeypatch.setattr(server.threading, "Thread", _Thread)
    queued = app.run_enrichment(ACTOR, {"task": "keyman", "limit": 2})
    assert queued["status"] == "queued"
    assert started and started[-1][1][1] == "keyman"
    with pytest.raises(ValueError, match="unknown_enrichment_task"):
        app.run_enrichment(ACTOR, {"task": "unknown"})
    with pytest.raises(ValueError, match="enrichment_limit_invalid"):
        app.run_enrichment(ACTOR, {"task": "keyman", "limit": "bad"})
