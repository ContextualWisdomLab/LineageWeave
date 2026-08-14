"""Exercise PostgreSQL persistence and Valkey Stream contracts without a file-store fallback."""

from __future__ import annotations

import json

import pytest

import lineageweave as lw


class _RecordingCursor:
    """Capture direct-database batch writes for contract assertions."""

    def __init__(self) -> None:
        self.executemany_calls: list[tuple[str, list[tuple[object, ...]]]] = []
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []

    def __enter__(self) -> "_RecordingCursor":
        """Return the cursor as a context manager."""
        return self

    def __exit__(self, *_args: object) -> bool:
        """Do not suppress an adapter error."""
        return False

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
        """Record a parameterized statement such as a score-row delete."""
        self.execute_calls.append((sql, tuple(params)))

    def executemany(self, sql: str, values: list[tuple[object, ...]]) -> None:
        """Record a parameterized bulk insert."""
        self.executemany_calls.append((sql, values))


class _RecordingConnection:
    """Provide the cursor surface used by persistence functions."""

    def __init__(self) -> None:
        self.recording_cursor = _RecordingCursor()

    def cursor(self, *_args: object, **_kwargs: object) -> _RecordingCursor:
        """Return one reusable cursor for batch-write checks."""
        return self.recording_cursor


def test_bounded_llm_appointment_enrichment_replaces_only_complete_model_rows(monkeypatch) -> None:
    """Keep fallback extracts intact while one bounded operator batch writes genuine model rows."""
    connection = _RecordingConnection()
    query_calls: list[tuple[str, tuple[object, ...]]] = []
    events: list[tuple[object, ...]] = []
    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)

    def query(_connection, statement, params=()):  # noqa: ANN001
        query_calls.append((statement, tuple(params)))
        return [
            {"document_no": "DOC-1", "title_sample": "고객 미팅", "korean_summary": "일정 확인"},
            {"document_no": "DOC-2", "title_sample": "고객 미팅", "korean_summary": "일정 확인"},
            {"document_no": "DOC-3", "title_sample": "고객 미팅", "korean_summary": "일정 확인"},
        ]

    def derive(_text, *, document_no, **_kwargs):  # noqa: ANN001
        if document_no == "DOC-1":
            return [{"appointment_id": "apt-1", "occurred_on": "2026-08-15", "label": "고객 약속", "excerpt": "방문", "source": "llm"}]
        if document_no == "DOC-2":
            return [{"appointment_id": "apt-2", "occurred_on": "2026-08-16", "label": "고객 약속", "excerpt": "추출", "source": "extract"}]
        raise RuntimeError("gateway unavailable")

    monkeypatch.setattr(lw, "_database_query", query)
    monkeypatch.setattr(lw, "derive_appointments_via_llm", derive)
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    result = lw.enrich_pending_appointment_records(
        connection,
        transport=lambda _body: {},
        limit=3,
        batch_id="batch-1",
    )
    assert result == {"requested": 3, "completed": 1, "fallback": 1, "failed": 1, "appointment_rows": 1}
    assert query_calls[0][1] == (3,)
    assert "appointment.content_source = 'llm'" in query_calls[0][0]
    assert "meeting|visit|kickoff" in query_calls[0][0]
    assert any("DELETE FROM" in sql and params == ("DOC-1",) for sql, params in connection.recording_cursor.execute_calls)
    assert connection.recording_cursor.executemany_calls[0][1] == [
        ("apt-1", "DOC-1", "2026-08-15", "고객 약속", "방문", "llm")
    ]
    assert events == [
        (
            "llm_enrichment_document_completed",
            "DOC-1",
            lw.APPOINTMENT_ENRICHMENT_SYSTEM_ACTOR,
            {
                "appointment_source": "llm",
                "appointment_rows": 1,
                lw.APPOINTMENT_ENRICHMENT_BATCH_KEY: "batch-1",
            },
        )
    ]
    with pytest.raises(ValueError, match="appointment_enrichment_limit_invalid"):
        lw.enrich_pending_appointment_records(connection, transport=lambda _body: {}, limit=0)

    monkeypatch.setattr(lw, "_database_query", lambda *_args: [])
    assert lw.enrich_pending_appointment_records(connection, transport=lambda _body: {}, limit=999)["requested"] == 0
    with pytest.raises(ValueError, match="appointment_enrichment_batch_invalid"):
        lw.enrich_pending_appointment_records(connection, transport=lambda _body: {}, batch_id=" ")


def test_appointment_enrichment_event_delivery_is_batch_scoped(monkeypatch) -> None:
    """Deliver only the committed batch and leave an unacknowledged event pending."""
    queries: list[tuple[str, tuple[object, ...]]] = []
    published: list[str] = []
    marked: list[str] = []

    def query(_connection, statement, params=()):  # noqa: ANN001
        queries.append((statement, tuple(params)))
        if params[3] == "empty-batch":
            return []
        return [
            {"event_id": "event-1", "event_type": "llm_enrichment_document_completed", "document_no": "DOC-1", "actor_id": lw.APPOINTMENT_ENRICHMENT_SYSTEM_ACTOR, "payload": {}},
            {"event_id": "event-2", "event_type": "llm_enrichment_document_completed", "document_no": "DOC-2", "actor_id": lw.APPOINTMENT_ENRICHMENT_SYSTEM_ACTOR, "payload": {}},
        ]

    def publish(event):  # noqa: ANN001
        published.append(str(event["event_id"]))
        if event["event_id"] == "event-2":
            raise OSError("valkey unavailable")
        return "stream-id"

    monkeypatch.setattr(lw, "_database_query", query)
    monkeypatch.setattr(lw, "publish_valkey_event", publish)
    monkeypatch.setattr(lw, "mark_event_published", lambda _connection, event_id: marked.append(event_id))
    result = lw.publish_appointment_enrichment_events(object(), batch_id="batch-1", limit=999)

    assert result == {"requested": 2, "published": 1, "pending": 1}
    assert published == ["event-1", "event-2"]
    assert marked == ["event-1"]
    assert "payload ->> %s = %s" in queries[0][0]
    assert queries[0][1] == (
        "llm_enrichment_document_completed",
        lw.APPOINTMENT_ENRICHMENT_SYSTEM_ACTOR,
        lw.APPOINTMENT_ENRICHMENT_BATCH_KEY,
        "batch-1",
        lw.MAX_APPOINTMENT_ENRICHMENT_DOCUMENTS,
    )
    assert lw.publish_appointment_enrichment_events(object(), batch_id="empty-batch") == {
        "requested": 0,
        "published": 0,
        "pending": 0,
    }
    with pytest.raises(ValueError, match="appointment_enrichment_batch_invalid"):
        lw.publish_appointment_enrichment_events(object(), batch_id=" ")


def test_bounded_llm_issue_work_enrichment_replaces_only_complete_model_rows(monkeypatch) -> None:
    """Keep incomplete issue-work responses pending while persisting one genuine LLM result."""
    connection = _RecordingConnection()
    query_calls: list[tuple[str, tuple[object, ...]]] = []
    persisted: list[tuple[dict[str, object], dict[str, object]]] = []
    events: list[tuple[object, ...]] = []
    requests: list[dict[str, object]] = []
    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)

    def query(_connection, statement, params=()):  # noqa: ANN001
        query_calls.append((statement, tuple(params)))
        return [
            {
                "ticket_id": "ticket-1",
                "document_no": "DOC-1",
                "title": "Customer follow-up",
                "status": "open",
                "title_sample": "Customer follow-up",
                "korean_summary": "Confirm the accountable owner.",
            },
            {
                "ticket_id": "ticket-2",
                "document_no": "DOC-2",
                "title": "Incomplete response",
                "status": "open",
                "title_sample": "Incomplete response",
                "korean_summary": "Await complete work details.",
            },
        ]

    def transport(body):  # noqa: ANN001
        requests.append(body)
        if body["ticket"]["ticket_id"] == "ticket-1":
            return {"todo_body": "Confirm accountable owner", "calendar_body": "Arrange follow-up"}
        return {"todo_body": "Only one field"}

    monkeypatch.setattr(lw, "_database_query", query)
    monkeypatch.setattr(
        lw,
        "persist_issue_work_items",
        lambda _connection, todo, calendar: persisted.append((todo, calendar)),
    )
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda _connection, *args: events.append(args))
    result = lw.enrich_pending_issue_work_items(
        connection,
        transport=transport,
        limit=3,
        batch_id="issue-batch",
    )

    assert result == {"requested": 2, "completed": 1, "fallback": 1, "todo_rows": 1, "calendar_rows": 1}
    assert query_calls[0][1] == (3,)
    assert "todo.content_source = 'pending_llm'" in query_calls[0][0]
    assert "calendar.content_source = 'pending_llm'" in query_calls[0][0]
    assert requests[0]["korean_summary"] == "Confirm the accountable owner."
    assert persisted[0][0]["source"] == "llm"
    assert persisted[0][1]["occurred_on"] is None
    assert events == [
        (
            "llm_enrichment_document_completed",
            "DOC-1",
            lw.ISSUE_WORK_ENRICHMENT_SYSTEM_ACTOR,
            {"issue_work_source": "llm", lw.ISSUE_WORK_ENRICHMENT_BATCH_KEY: "issue-batch"},
        )
    ]
    with pytest.raises(ValueError, match="issue_work_enrichment_limit_invalid"):
        lw.enrich_pending_issue_work_items(connection, transport=transport, limit=0)

    monkeypatch.setattr(lw, "_database_query", lambda *_args: [])
    assert lw.enrich_pending_issue_work_items(connection, transport=transport, limit=999)["requested"] == 0
    with pytest.raises(ValueError, match="issue_work_enrichment_batch_invalid"):
        lw.enrich_pending_issue_work_items(connection, transport=transport, batch_id=" ")


def test_issue_work_enrichment_event_delivery_is_batch_scoped(monkeypatch) -> None:
    """Keep the issue-work batch isolated from unrelated unpublished outbox rows."""
    queries: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda _connection, statement, params=(): queries.append((statement, tuple(params))) or [],
    )

    assert lw.publish_issue_work_enrichment_events(object(), batch_id="issue-batch") == {
        "requested": 0,
        "published": 0,
        "pending": 0,
    }
    assert queries[0][1] == (
        "llm_enrichment_document_completed",
        lw.ISSUE_WORK_ENRICHMENT_SYSTEM_ACTOR,
        lw.ISSUE_WORK_ENRICHMENT_BATCH_KEY,
        "issue-batch",
        lw.MAX_ISSUE_WORK_ENRICHMENT_DOCUMENTS,
    )
    with pytest.raises(ValueError, match="issue_work_enrichment_batch_invalid"):
        lw.publish_issue_work_enrichment_events(object(), batch_id=" ")


def test_lineage_review_overrides_preserve_authorized_kg_projection(monkeypatch) -> None:
    """Keep review decisions auditable, ABAC-scoped, and reflected in the KG projection."""
    graph = {
        "edges": [
            {"source": "kg:document:DOC-1", "target": "kg:document:DOC-2", "relation": "similar"},
            {"source": "doc:DOC-2", "target": "kg:document:DOC-1", "relation": "related"},
        ]
    }
    overrides = [
        {"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation_name": "similar", "override_status": "suppressed"},
        {"source_node": "doc:DOC-2", "target_node": "doc:DOC-1", "relation_name": "related", "override_status": "restored"},
    ]
    assert lw.filter_knowledge_graph_by_lineage_overrides(graph, []) is graph
    filtered = lw.filter_knowledge_graph_by_lineage_overrides(graph, overrides)
    assert filtered["edges"] == [graph["edges"][1]]

    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    with pytest.raises(ValueError, match="unknown_lineage_edge_override_status"):
        lw.persist_lineage_edge_override(
            object(),
            source_node="doc:DOC-1",
            target_node="doc:DOC-2",
            relation_name="similar",
            override_status="invalid",
            reason="fixture",
            updated_by="admin-1",
        )
    lw.persist_lineage_edge_override(
        object(),
        source_node="doc:DOC-1",
        target_node="doc:DOC-2",
        relation_name="similar",
        override_status="suppressed",
        reason="fixture",
        updated_by="admin-1",
    )
    assert "ON CONFLICT" in statements[0][0]
    assert statements[0][1] == ("doc:DOC-1", "doc:DOC-2", "similar", "suppressed", "fixture", "admin-1")

    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: False)
    assert lw.load_lineage_edge_overrides(object()) == []
    assert lw.load_lineage_review_edges(object(), {"corp_code": "CORP-A", "pu_code": "PU-A", "roles": ["reader"]}) == {"items": [], "total": 0}

    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: True)

    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if lw.ANALYSIS_DOCUMENT_TABLE in sql:
            return [
                {"document_no": "DOC-1", "corp_code": "CORP-A", "owner_pu": "PU-A", "title_sample": "Alpha", "visibility_code": "private"},
                {"document_no": "DOC-2", "corp_code": "CORP-A", "owner_pu": "PU-A", "title_sample": "Beta", "visibility_code": "private"},
                {"document_no": "DOC-3", "corp_code": "CORP-A", "owner_pu": "PU-B", "title_sample": "Hidden", "visibility_code": "private"},
            ]
        if lw.ANALYSIS_LINEAGE_OVERRIDE_TABLE in sql:
            return [overrides[0]]
        if lw.ANALYSIS_EDGE_TABLE in sql:
            return [
                {"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation_name": "similar", "evidence_status": lw.EVIDENCE_INFERRED, "acthguid": "thread-1", "reason": "Alpha evidence"},
                {"source_node": "doc:DOC-1", "target_node": "doc:DOC-3", "relation_name": "related", "evidence_status": lw.EVIDENCE_PREDICTED, "acthguid": "thread-2", "reason": "hidden"},
                {"source_node": "doc:DOC-3", "target_node": "doc:DOC-2", "relation_name": "related", "evidence_status": lw.EVIDENCE_PREDICTED, "acthguid": "thread-2", "reason": "hidden source"},
                {"source_node": "doc:missing", "target_node": "doc:DOC-2", "relation_name": "related", "evidence_status": lw.EVIDENCE_PREDICTED, "acthguid": "thread-3", "reason": "missing"},
            ]
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_query", query)
    actor = {"corp_code": "CORP-A", "pu_code": "PU-A", "roles": ["reader"]}
    with pytest.raises(ValueError, match="lineage_review_query_too_long"):
        lw.load_lineage_review_edges(object(), actor, query="x" * 129)
    reviewed = lw.load_lineage_review_edges(object(), actor, query="alpha", limit=0)
    assert reviewed == {
        "items": [
            {
                "source_node": "doc:DOC-1",
                "target_node": "doc:DOC-2",
                "source_document": "DOC-1",
                "target_document": "DOC-2",
                "source_title": "Alpha",
                "target_title": "Beta",
                "relation": "similar",
                "evidence_status": lw.EVIDENCE_INFERRED,
                "acthguid": "thread-1",
                "reason": "Alpha evidence",
                "override_status": "suppressed",
            }
        ],
        "total": 1,
        "limit": 1,
    }
    assert lw.load_lineage_review_edges(object(), actor, query="no-match")["items"] == []


def test_database_copy_rows_uses_native_postgres_copy() -> None:
    """Stream snapshot rows through psycopg COPY when the live cursor supports it."""
    written: list[tuple[object, ...]] = []
    statements: list[str] = []

    class CopyStream:
        def __enter__(self) -> "CopyStream":
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def write_row(self, row: tuple[object, ...]) -> None:
            written.append(row)

    class CopyCursor(_RecordingCursor):
        def copy(self, statement: str) -> CopyStream:
            statements.append(statement)
            return CopyStream()

    class CopyConnection:
        def __init__(self) -> None:
            self.copy_cursor = CopyCursor()

        def cursor(self) -> CopyCursor:
            return self.copy_cursor

    connection = CopyConnection()
    lw._database_copy_rows(
        connection,
        lw.ANALYSIS_KG_NODE_TABLE,
        ("node_id", "node_type"),
        [("kg:document:one", "document"), ("kg:person:two", "person")],
    )

    assert statements == [
        "COPY analysis_knowledge_graph_nodes (node_id, node_type) FROM STDIN"
    ]
    assert written == [("kg:document:one", "document"), ("kg:person:two", "person")]
    assert connection.copy_cursor.executemany_calls == []


def test_database_copy_rows_rejects_invalid_column_identifier() -> None:
    """Reject an untrusted column name before constructing COPY SQL."""
    with pytest.raises(ValueError, match="invalid column identifier"):
        lw._database_copy_rows(
            _RecordingConnection(),
            lw.ANALYSIS_KG_NODE_TABLE,
            ("node-id",),
            [("kg:document:one",)],
        )


def test_release_snapshot_schema_locks_commits_and_reacquires(monkeypatch) -> None:
    """Release DDL locks only for production writers and reacquire the data lock."""
    events: list[str] = []

    class CommittingConnection:
        def commit(self) -> None:
            events.append("commit")

    monkeypatch.setattr(lw, "_lock_knowledge_graph_snapshot", lambda _connection: events.append("lock"))
    lw.release_snapshot_schema_locks(CommittingConnection(), False)
    assert events == []
    lw.release_snapshot_schema_locks(CommittingConnection(), True)
    assert events == ["commit", "lock"]
    lw.release_snapshot_schema_locks(object(), True)
    assert events == ["commit", "lock", "lock"]


class _BytesSocket:
    """Small RESP socket double that records command bytes and reads exact replies."""

    def __init__(self, response: bytes) -> None:
        self.response = bytearray(response)
        self.sent = b""
        self.closed = False

    def recv(self, size: int) -> bytes:
        """Return at most one byte so exact-read loops are exercised."""
        if not self.response:
            return b""
        actual = min(size, 1, len(self.response))
        chunk = bytes(self.response[:actual])
        del self.response[:actual]
        return chunk

    def sendall(self, value: bytes) -> None:
        """Record a complete RESP request."""
        self.sent += value

    def close(self) -> None:
        """Record that callers close the Valkey connection."""
        self.closed = True


def test_enum_and_normalized_inspection_schema_contract(monkeypatch) -> None:
    """Create the shared enum and legacy-safe inspection schema through direct SQL."""
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: lw.DEFAULT_ENUM_ROWS)
    families = lw.ensure_common_enum_table(object())
    assert families["visibility"] == ["public", "private"]
    assert any("CREATE TABLE IF NOT EXISTS common_enum_values" in sql for sql, _ in statements)

    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [{"found": 1}])
    lw.ensure_content_inspection_tables(object())
    sql_text = "\n".join(sql for sql, _ in statements)
    assert "analysis_content_inspection_labels" in sql_text
    assert "DROP COLUMN object_labels" in sql_text
    assert "DROP COLUMN label_description" in sql_text


def test_normalized_dom_content_schema_and_kg_contract(monkeypatch) -> None:
    """Persist safe HTML semantics in 3NF and add only metadata-only KG nodes."""
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    lw.ensure_content_structure_tables(object())
    schema_sql = "\n".join(sql for sql, _ in statements)
    assert "analysis_content_blocks" in schema_sql
    assert "analysis_content_format_hints" in schema_sql
    assert "analysis_content_asset_profiles" in schema_sql
    assert "REFERENCES analysis_content_blocks" in schema_sql

    connection = _RecordingConnection()
    monkeypatch.setattr(lw, "ensure_content_structure_tables", lambda _connection: None)
    monkeypatch.setattr(
        lw,
        "load_document_content_structure",
        lambda *_args: {"blocks": [], "assets": []},
    )
    structure = {
        "blocks": [
            {
                "block_index": 0,
                "source_evidence_id": "ROW-1",
                "source_row_number": "7",
                "block_kind": "paragraph",
                "source_position": 3,
                "text_content": "배송 일정 협의",
                "text_sha256": "a" * 64,
                "format_hints": [{"hint_kind": "text_align", "hint_value": "right"}],
            }
        ],
        "assets": [
            {
                "asset_index": 0,
                "source_evidence_id": "ROW-1",
                "source_row_number": "7",
                "source_position": 42,
                "mime_type": "image/png",
                "encoded_bytes": 12,
                "content_kind": lw.CONTENT_INLINE_IMAGE,
                "asset_sha256": "b" * 64,
                "inspection_eligible": True,
            }
        ],
    }
    counts = lw.persist_document_content_structure(connection, "DOC-1", structure)
    assert counts == {"content_block_rows": 1, "content_format_hint_rows": 1, "content_asset_rows": 1}
    assert len(connection.recording_cursor.executemany_calls) == 3
    assert all("<p" not in str(values) and "data:image" not in str(values) for _, values in connection.recording_cursor.executemany_calls)

    graph = lw.attach_document_content_knowledge_graph(
        {
            "nodes": [{"id": "kg:document:DOC-1", "type": "document", "label": "Fixture", "document_no": "DOC-1"}],
            "edges": [],
        },
        "DOC-1",
        structure,
    )
    block_node = next(node for node in graph["nodes"] if node["type"] == "content_block")
    assert block_node["source_evidence_id"] == "ROW-1"
    assert "text_content" not in block_node
    assert graph["edges"] == [{"source": "kg:document:DOC-1", "target": block_node["id"], "relation": "document_content_block", "evidence_id": "ROW-1"}]
    records = lw.semantic_layer_records(graph)
    assert any(term["standard_uri"] == "https://schema.org/Text" for term in records["terms"])
    assert any(term["standard_uri"] == "https://schema.org/hasPart" for term in records["terms"])


def test_content_inspection_and_snapshot_persistence_contract(monkeypatch) -> None:
    """Persist normalized OCR labels and a compact graph snapshot with parameterized writes."""
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    monkeypatch.setattr(lw, "ensure_content_inspection_tables", lambda _connection: None)
    asset = {
        "asset_index": 1,
        "row_guid": "row-1",
        "source_row_number": "7",
        "source_position": 4,
        "mime_type": "image/png",
    }
    inspection = {
        "asset_sha256": "a" * 64,
        "ocr_text": "chart caption",
        "model_name": "vision-test",
        "object_labels": [{"label": "chart", "description": "bar chart"}, ""],
    }
    lw.persist_content_inspection(object(), "DOC-1", asset, inspection, "account-1")
    assert any("analysis_object_label_catalog" in sql for sql, _ in statements)
    assert any("bar chart" in params for _, params in statements)
    with pytest.raises(ValueError, match="invalid content inspection asset"):
        lw.persist_content_inspection(object(), "DOC-1", {"asset_index": -1}, inspection, "account-1")
    with pytest.raises(ValueError, match="content inspection identity"):
        lw.persist_content_inspection(object(), "", asset, inspection, "account-1")
    with pytest.raises(ValueError, match="content inspection identity"):
        lw.persist_content_inspection(object(), "DOC-1", asset, inspection, "")

    connection = _RecordingConnection()
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        lw,
        "build_org_unit_affiliate_tree",
        lambda _documents: {"nodes": ["Corp A"], "edges": [{"parent": "Corp A", "child": "Corp A PU A", "relation": "corp_pu"}], "parent_of": {"Corp A PU A": "Corp A"}},
    )
    monkeypatch.setattr(
        lw,
        "build_knowledge_graph",
        lambda _nodes, _edges, **_kwargs: {
            "nodes": [{"id": "kg:document:DOC-1", "type": "document", "label": "Fixture", "document_no": "DOC-1"}],
            "edges": [{"source": "kg:document:DOC-1", "target": "kg:document:DOC-1", "relation": "observed"}],
        },
    )
    payload = {
        "metadata": {"row_count": 1, "document_count": 1, "thread_count": 1},
        "nodes": [{"id": "doc:DOC-1", "type": "document", "document_no": "DOC-1", "corp_code": "CORP_A", "owner_pu": "PU_A"}, {"id": "row:1", "type": "row", "document_no": "DOC-1"}],
        "edges": [{"source": "doc:DOC-1", "target": "row:1", "relation": "observed", "evidence_status": lw.EVIDENCE_OBSERVED}],
    }
    counts = lw.persist_analysis_payload(connection, payload)
    assert counts["document_rows"] == 1
    assert counts["edge_rows"] == 1
    assert counts["knowledge_node_rows"] == 1
    assert counts["knowledge_edge_rows"] == 1
    assert counts["semantic_node_rows"] == 1
    assert counts["semantic_edge_rows"] == 1
    assert counts["affiliate_edge_rows"] == 1
    assert counts["todo_rows"] == 0
    assert counts["report_rows"] == 0
    assert len(connection.recording_cursor.executemany_calls) == 7
    assert any("DELETE FROM analysis_document_nodes" in sql for sql, _ in statements)
    assert any("analysis_ontology_terms" in sql for sql, _ in statements)
    snapshot_lock = next(
        index
        for index, (sql, _params) in enumerate(statements)
        if "pg_advisory_xact_lock" in sql
    )
    evidence_upgrade = next(
        index
        for index, (sql, _params) in enumerate(statements)
        if "ADD COLUMN evidence_status" in sql
    )
    kg_nodes = next(
        index
        for index, (sql, _params) in enumerate(statements)
        if "DELETE FROM analysis_knowledge_graph_nodes" in sql
    )
    kg_edges = next(
        index
        for index, (sql, _params) in enumerate(statements)
        if "DELETE FROM analysis_knowledge_graph_edges" in sql
    )
    assert snapshot_lock < evidence_upgrade < kg_nodes < kg_edges


def test_semantic_layer_normalizes_kg_terms_rules_and_authorized_context(monkeypatch) -> None:
    """Persist standard URIs as 3NF terms and retrieve only selected KG semantics."""
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    graph = {
        "nodes": [
            {
                "id": "kg:document:DOC-1",
                "type": "document",
                "label": "Fixture",
                "entity_role": "고객",
            },
            {"id": "kg:person:ana", "type": "person", "label": "Ana"},
            {"id": "kg:pu:one", "type": "pu", "label": "PU One"},
            {"id": "kg:org:one", "type": "organization", "label": "Org One"},
        ],
        "edges": [
            {
                "source": "kg:document:DOC-1",
                "target": "kg:person:ana",
                "relation": "keyman_our_side",
                "evidence_id": "ROW-1",
            },
            {
                "source": "kg:person:ana",
                "target": "kg:pu:one",
                "relation": "person_pu",
                "evidence_id": "ROW-1",
            },
            {
                "source": "kg:pu:one",
                "target": "kg:org:one",
                "relation": "pu_corp",
                "evidence_id": "ROW-1",
            },
        ],
    }
    records = lw.semantic_layer_records(graph)
    assert any(term["standard_uri"] == "http://www.w3.org/ns/org#unitOf" for term in records["terms"])
    assert any(term["term_code"] == "entity_role_customer" for term in records["terms"])
    assert len(records["rules"]) == 3

    connection = _RecordingConnection()
    counts = lw.persist_knowledge_semantic_layer(connection, graph)
    assert counts == {
        "ontology_namespace_rows": len(lw.SEMANTIC_NAMESPACE_ROWS),
        "ontology_term_rows": len(records["terms"]),
        "ontology_rule_rows": 3,
        "semantic_node_rows": 5,
        "semantic_edge_rows": 3,
    }
    assert any("REFERENCES analysis_ontology_terms" in sql for sql, _ in statements)
    assert len(connection.recording_cursor.executemany_calls) == 2

    statements.clear()
    connection.recording_cursor.executemany_calls.clear()
    incremental = lw.persist_knowledge_semantic_layer(
        connection,
        graph,
        replace_existing=False,
    )
    assert incremental == counts
    assert not any("DELETE FROM" in sql for sql, _params in statements)
    assert connection.recording_cursor.executemany_calls == []
    assert any("ON CONFLICT (assertion_id)" in sql for sql, _params in statements)

    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if lw.ANALYSIS_SEMANTIC_NODE_TABLE in sql:
            return [{"node_id": "kg:document:DOC-1", "assignment_kind": "node_type", "term_label": "CreativeWork", "definition_text": "fixture", "standard_uri": "https://schema.org/CreativeWork"}]
        return [{"source_node": "kg:document:DOC-1", "target_node": "kg:person:ana", "relation_name": "keyman_our_side", "evidence_id": "ROW-1", "term_label": "Keyman Our Side", "definition_text": "fixture", "standard_uri": "urn:lineageweave:ontology:predicate/keyman_our_side"}]

    monkeypatch.setattr(lw, "_database_query", query)
    context = lw.load_knowledge_semantic_context(connection, ["kg:document:DOC-1", "kg:person:ana"])
    assert context["node_terms"] == [
        {
            "node_id": "kg:document:DOC-1",
            "assignment_kind": "node_type",
            "term_label": "CreativeWork",
            "definition_text": "fixture",
            "standard_uri": "https://schema.org/CreativeWork",
        }
    ]
    assert context["edge_assertions"][0]["evidence_id"] == "ROW-1"


def test_knowledge_snapshot_replaces_graph_and_semantics_together(monkeypatch) -> None:
    """Keep KG rows and semantic assertions on one direct-PostgreSQL snapshot path."""
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    monkeypatch.setattr(
        lw,
        "persist_knowledge_semantic_layer",
        lambda _connection, _graph: {"semantic_node_rows": 1, "semantic_edge_rows": 1},
    )
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    connection = _RecordingConnection()
    counts = lw.persist_knowledge_graph_snapshot(
        connection,
        {
            "nodes": [{"id": "kg:document:DOC-1", "type": "document", "label": "Fixture"}],
            "edges": [{"source": "kg:document:DOC-1", "target": "kg:document:DOC-1", "relation": "topic_affinity", "evidence_id": "ROW-1", "evidence_status": lw.EVIDENCE_INFERRED, "reason": "shared_topic"}],
        },
    )
    assert counts == {
        "knowledge_node_rows": 1,
        "knowledge_edge_rows": 1,
        "semantic_node_rows": 1,
        "semantic_edge_rows": 1,
    }
    snapshot_lock_index = next(
        index
        for index, (sql, _params) in enumerate(statements)
        if "pg_advisory_xact_lock" in sql
    )
    evidence_upgrade_index = next(
        index
        for index, (sql, _params) in enumerate(statements)
        if "ADD COLUMN evidence_status" in sql
    )
    node_delete_index = next(
        index
        for index, (sql, _params) in enumerate(statements)
        if "DELETE FROM analysis_knowledge_graph_nodes" in sql
    )
    edge_delete_index = next(
        index
        for index, (sql, _params) in enumerate(statements)
        if "DELETE FROM analysis_knowledge_graph_edges" in sql
    )
    assert snapshot_lock_index < evidence_upgrade_index < node_delete_index < edge_delete_index
    edge_sql, edge_rows = connection.recording_cursor.executemany_calls[1]
    assert "evidence_status" in edge_sql
    assert edge_rows[0][-2:] == (lw.EVIDENCE_INFERRED, "shared_topic")
    assert len(connection.recording_cursor.executemany_calls) == 2


def test_knowledge_snapshot_retains_verified_organization_alias_additions(monkeypatch) -> None:
    """Carry verified alias nodes and edges across a rebuilt source snapshot."""
    monkeypatch.setattr(lw, "_database_exec", lambda *_args, **_kwargs: None)
    semantic_graphs: list[dict[str, object]] = []
    monkeypatch.setattr(
        lw,
        "persist_knowledge_semantic_layer",
        lambda _connection, graph: semantic_graphs.append(graph)
        or {"semantic_node_rows": len(graph["nodes"]), "semantic_edge_rows": len(graph["edges"])},
    )

    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if "FROM information_schema.columns" in sql:
            return [{"column_name": "evidence_status"}, {"column_name": "reason"}]
        if f"FROM {lw.ANALYSIS_INFERENCE_CANDIDATE_TABLE} AS candidate" in sql:
            return []
        if f"FROM {lw.ANALYSIS_KG_EDGE_TABLE}" in sql:
            return [
                {
                    "source_node": "kg:organization_alias:short",
                    "target_node": "kg:organization:canonical",
                    "relation_name": "organization_alias",
                    "evidence_id": "candidate-1",
                    "evidence_status": lw.EVIDENCE_INFERRED,
                    "reason": "verified alias",
                }
            ]
        if f"FROM {lw.ANALYSIS_KG_NODE_TABLE}" in sql:
            return [
                {
                    "node_id": "kg:organization:canonical",
                    "node_type": "organization",
                    "label": "Persisted canonical",
                    "document_no": "DOC-1",
                    "metadata_payload": None,
                },
                {
                    "node_id": "kg:organization_alias:short",
                    "node_type": "organization_alias",
                    "label": "Short",
                    "document_no": "DOC-1",
                    "metadata_payload": {"verification": "verified"},
                },
            ]
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_query", query)
    connection = _RecordingConnection()
    counts = lw.persist_knowledge_graph_snapshot(
        connection,
        {
            "nodes": [
                {
                    "id": "kg:organization:canonical",
                    "type": "organization",
                    "label": "Current canonical",
                    "document_no": "DOC-1",
                }
            ],
            "edges": [],
        },
    )

    assert counts["knowledge_node_rows"] == 2
    assert counts["knowledge_edge_rows"] == 1
    assert next(node for node in semantic_graphs[0]["nodes"] if node["id"] == "kg:organization:canonical")["label"] == "Current canonical"
    assert any(node.get("verification") == "verified" for node in semantic_graphs[0]["nodes"])
    assert semantic_graphs[0]["edges"][0]["relation"] == "organization_alias"


def test_knowledge_snapshot_recovers_alias_from_verified_review_labels(monkeypatch) -> None:
    """Rebuild an alias even after a prior snapshot removed its incremental KG rows."""
    monkeypatch.setattr(lw, "_database_exec", lambda *_args, **_kwargs: None)
    captured: list[dict[str, object]] = []
    monkeypatch.setattr(
        lw,
        "persist_knowledge_semantic_layer",
        lambda _connection, graph: captured.append(graph)
        or {"semantic_node_rows": len(graph["nodes"]), "semantic_edge_rows": len(graph["edges"])},
    )

    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if "FROM information_schema.columns" in sql:
            return [{"column_name": "source_label"}, {"column_name": "target_label"}]
        if f"FROM {lw.ANALYSIS_INFERENCE_CANDIDATE_TABLE} AS candidate" in sql:
            return [
                {
                    "source_node": "kg:organization_alias:short",
                    "target_node": "kg:organization:canonical",
                    "source_label": "Short",
                    "target_label": "Canonical",
                    "candidate_id": "candidate-2",
                    "run_id": "run-2",
                    "decision_confidence": "0.95",
                    "rationale_text": "verified review",
                    "document_no": "DOC-2",
                }
            ]
        if f"FROM {lw.ANALYSIS_INFERENCE_EVIDENCE_TABLE}" in sql:
            return [
                {
                    "evidence_id": "external-2",
                    "title_text": "Short / Canonical organization",
                    "excerpt_text": "Short is the alias for Canonical.",
                }
            ]
        if f"FROM {lw.ANALYSIS_KG_EDGE_TABLE}" in sql:
            return []
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_query", query)
    counts = lw.persist_knowledge_graph_snapshot(_RecordingConnection(), {"nodes": [], "edges": []})

    assert counts["knowledge_node_rows"] == 2
    assert counts["knowledge_edge_rows"] == 1
    assert {node["label"] for node in captured[0]["nodes"]} == {"Short", "Canonical"}
    assert captured[0]["edges"][0]["evidence_id"] == "candidate-2"


def test_knowledge_snapshot_hides_historical_alias_without_canonical_text(monkeypatch) -> None:
    """Keep an unsupported historical alias in the ledger but out of the KG projection."""
    monkeypatch.setattr(lw, "_database_exec", lambda *_args, **_kwargs: None)
    captured: list[dict[str, object]] = []
    monkeypatch.setattr(
        lw,
        "persist_knowledge_semantic_layer",
        lambda _connection, graph: captured.append(graph)
        or {"semantic_node_rows": len(graph["nodes"]), "semantic_edge_rows": len(graph["edges"])},
    )

    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if "FROM information_schema.columns" in sql:
            return [{"column_name": "source_label"}, {"column_name": "target_label"}]
        if f"FROM {lw.ANALYSIS_INFERENCE_CANDIDATE_TABLE} AS candidate" in sql:
            return [
                {
                    "source_node": "kg:organization_alias:short",
                    "target_node": "kg:organization:canonical",
                    "source_label": "Short",
                    "target_label": "Canonical",
                    "candidate_id": "candidate-old",
                    "run_id": "run-old",
                    "decision_confidence": "0.95",
                    "rationale_text": "historical review",
                    "document_no": "DOC-OLD",
                }
            ]
        if f"FROM {lw.ANALYSIS_INFERENCE_EVIDENCE_TABLE}" in sql:
            return [{"evidence_id": "external-old", "title_text": "Short", "excerpt_text": "Other organization"}]
        if f"FROM {lw.ANALYSIS_KG_EDGE_TABLE}" in sql:
            return [
                {
                    "source_node": "kg:organization_alias:short",
                    "target_node": "kg:organization:canonical",
                    "relation_name": "organization_alias",
                    "evidence_id": "external-old",
                    "evidence_status": lw.EVIDENCE_INFERRED,
                    "reason": "historical edge",
                }
            ]
        if f"FROM {lw.ANALYSIS_KG_NODE_TABLE}" in sql:
            return [
                {
                    "node_id": "kg:organization_alias:short",
                    "node_type": "organization_alias",
                    "label": "Short",
                    "document_no": "DOC-OLD",
                    "metadata_payload": None,
                },
                {
                    "node_id": "kg:organization:canonical",
                    "node_type": "organization",
                    "label": "Canonical",
                    "document_no": "DOC-OLD",
                    "metadata_payload": None,
                },
            ]
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_query", query)
    counts = lw.persist_knowledge_graph_snapshot(_RecordingConnection(), {"nodes": [], "edges": []})

    assert counts["knowledge_node_rows"] == 0
    assert counts["knowledge_edge_rows"] == 0
    assert captured[0] == {"nodes": [], "edges": []}


def test_knowledge_snapshot_keeps_supported_legacy_alias_evidence(monkeypatch) -> None:
    """Retain a legacy alias edge only when its own external evidence supports both labels."""
    monkeypatch.setattr(lw, "_database_exec", lambda *_args, **_kwargs: None)
    captured: list[dict[str, object]] = []
    monkeypatch.setattr(
        lw,
        "persist_knowledge_semantic_layer",
        lambda _connection, graph: captured.append(graph)
        or {"semantic_node_rows": len(graph["nodes"]), "semantic_edge_rows": len(graph["edges"])},
    )

    def query(_connection, sql: str, params=()):  # noqa: ANN001
        if "FROM information_schema.columns" in sql:
            return [{"column_name": "source_label"}, {"column_name": "target_label"}]
        if f"FROM {lw.ANALYSIS_INFERENCE_CANDIDATE_TABLE} AS candidate" in sql:
            return [
                {
                    "source_node": "kg:organization_alias:short",
                    "target_node": "kg:organization:canonical",
                    "source_label": "Short",
                    "target_label": "Canonical",
                    "candidate_id": "candidate-supported",
                    "run_id": "run-supported",
                    "decision_confidence": "0.95",
                    "rationale_text": "supported review",
                    "document_no": "DOC-SUPPORTED",
                }
            ]
        if f"FROM {lw.ANALYSIS_INFERENCE_EVIDENCE_TABLE}" in sql:
            if len(params) == 3:
                return [{"evidence_id": "external-candidate", "title_text": "Short Canonical", "excerpt_text": ""}]
            return [{"evidence_id": "external-legacy", "title_text": "Short Canonical", "excerpt_text": ""}]
        if f"FROM {lw.ANALYSIS_KG_EDGE_TABLE}" in sql:
            return [
                {
                    "source_node": "kg:document:one",
                    "target_node": "kg:document:two",
                    "relation_name": "topic_affinity",
                    "evidence_id": "observed-1",
                    "evidence_status": lw.EVIDENCE_OBSERVED,
                    "reason": "topic",
                },
                {
                    "source_node": "kg:organization_alias:short",
                    "target_node": "kg:organization:canonical",
                    "relation_name": "organization_alias",
                    "evidence_id": "external-legacy",
                    "evidence_status": lw.EVIDENCE_INFERRED,
                    "reason": "supported legacy",
                },
                {
                    "source_node": "kg:organization_alias:short",
                    "target_node": "kg:organization:canonical",
                    "relation_name": "organization_alias",
                    "evidence_id": None,
                    "evidence_status": lw.EVIDENCE_INFERRED,
                    "reason": "missing evidence",
                },
            ]
        if f"FROM {lw.ANALYSIS_KG_NODE_TABLE}" in sql:
            return [
                {"node_id": "kg:document:one", "node_type": "document", "label": "One", "document_no": "DOC-1", "metadata_payload": None},
                {"node_id": "kg:document:two", "node_type": "document", "label": "Two", "document_no": "DOC-2", "metadata_payload": None},
                {"node_id": "kg:organization_alias:short", "node_type": "organization_alias", "label": "Short", "document_no": "DOC-SUPPORTED", "metadata_payload": None},
                {"node_id": "kg:organization:canonical", "node_type": "organization", "label": "Canonical", "document_no": "DOC-SUPPORTED", "metadata_payload": None},
            ]
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_query", query)
    counts = lw.persist_knowledge_graph_snapshot(_RecordingConnection(), {"nodes": [], "edges": []})

    assert counts["knowledge_edge_rows"] == 3
    assert sum(edge["relation"] == "organization_alias" for edge in captured[0]["edges"]) == 2


def test_knowledge_additions_upsert_without_deleting_snapshot(monkeypatch) -> None:
    """Keep an interactive alias mutation bounded to its two nodes and one edge."""
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    semantic_calls = []
    monkeypatch.setattr(
        lw,
        "persist_knowledge_semantic_layer",
        lambda _connection, graph, **kwargs: semantic_calls.append((graph, kwargs))
        or {"semantic_node_rows": 2, "semantic_edge_rows": 1},
    )
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    counts = lw.persist_knowledge_graph_additions(
        _RecordingConnection(),
        {
            "nodes": [
                {"id": "kg:alias:one", "type": "organization_alias", "label": "Alias"},
                {"id": "kg:organization:one", "type": "organization", "label": "Canonical"},
            ],
            "edges": [
                {
                    "source": "kg:alias:one",
                    "target": "kg:organization:one",
                    "relation": "organization_alias",
                    "evidence_id": "external-1",
                    "evidence_status": lw.EVIDENCE_INFERRED,
                }
            ],
        },
    )
    assert counts == {
        "knowledge_node_rows": 2,
        "knowledge_edge_rows": 1,
        "semantic_node_rows": 2,
        "semantic_edge_rows": 1,
    }
    assert not any("DELETE FROM" in sql for sql, _params in statements)
    assert sum("ON CONFLICT (node_id)" in sql for sql, _params in statements) == 2
    assert any("WHERE NOT EXISTS" in sql for sql, _params in statements)
    assert semantic_calls[0][1] == {"replace_existing": False}


def test_knowledge_graph_edge_schema_check_skips_current_columns(monkeypatch) -> None:
    """Avoid table-rewrite locks when both current KG edge columns already exist."""
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda *_args, **_kwargs: [
            {"column_name": "evidence_status"},
            {"column_name": "reason"},
        ],
    )
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )

    lw.ensure_knowledge_graph_edge_evidence_columns(object())

    assert statements == []


def test_customer_master_semantics_require_document_evidence() -> None:
    """Keep customer affiliates in the KG only when the LLM provides a source document."""
    customer_master = lw.parse_customer_master_response(
        {
            "accounts": [
                {"account_name": "Group", "entity_role": "고객", "document_nos": ["DOC-1"]},
                {"account_name": "Plant", "parent_name": "Group", "document_nos": "DOC-1"},
                {"account_name": "Unscoped", "document_nos": []},
            ]
        }
    )
    graph = lw.build_knowledge_graph(
        [
            {
                "type": "document",
                "document_no": "DOC-1",
                "title_sample": "Fixture",
                "entity_role": "고객",
            }
        ],
        [],
        customer_master=customer_master,
    )
    labels = {node["label"] for node in graph["nodes"]}
    assert {"Group", "Plant"} <= labels
    assert "Unscoped" not in labels
    assert any(edge["relation"] == "customer_affiliate" for edge in graph["edges"])
    visible = lw.filter_customer_master_for_documents(customer_master, {"DOC-1"})
    assert {account["account_name"] for account in visible["accounts"]} == {"Group", "Plant"}


def test_customer_master_loads_normalized_document_evidence(monkeypatch) -> None:
    """Rehydrate customer scope from the 3NF account-to-document relation."""
    def query(_connection, sql: str, params=()):  # noqa: ANN001
        if "to_regclass" in sql:
            return [{"table_name": params[0]}]
        if lw.ANALYSIS_CUSTOMER_DOCUMENT_TABLE in sql:
            return [
                {"account_name": "Group", "document_no": "DOC-1"},
                {"account_name": "Plant", "document_no": "DOC-1"},
            ]
        if lw.ANALYSIS_CUSTOMER_AFFILIATE_TABLE in sql:
            return [{"parent_label": "Group", "child_label": "Plant", "relation_name": "customer_affiliate", "content_source": "llm"}]
        if lw.ANALYSIS_CUSTOMER_TABLE in sql:
            return [
                {"account_name": "Group", "parent_name": None, "tier_name": "group", "entity_role": "고객", "content_source": "llm"},
                {"account_name": "Plant", "parent_name": "Group", "tier_name": "plant", "entity_role": "고객", "content_source": "llm"},
            ]
        return []

    monkeypatch.setattr(lw, "_database_query", query)
    master = lw.load_customer_master(object())
    assert master["accounts"][0]["document_nos"] == ["DOC-1"]
    assert master["edges"][0]["document_nos"] == ["DOC-1"]


def test_customer_master_actor_scope_uses_only_authorized_linked_documents(monkeypatch) -> None:
    """Customer screens must apply document ABAC before returning normalized account links."""
    tables = {
        lw.ANALYSIS_CUSTOMER_TABLE,
        lw.ANALYSIS_CUSTOMER_AFFILIATE_TABLE,
        lw.ANALYSIS_CUSTOMER_DOCUMENT_TABLE,
        lw.ANALYSIS_DOCUMENT_TABLE,
    }
    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, table: table in tables)

    def query(_connection, sql: str, params=()):  # noqa: ANN001
        if lw.ANALYSIS_CUSTOMER_DOCUMENT_TABLE in sql:
            return [
                {"account_name": "Group", "document_no": "DOC-1"},
                {"account_name": "Plant", "document_no": "DOC-2"},
                {"account_name": "Other", "document_no": "DOC-3"},
            ]
        if lw.ANALYSIS_DOCUMENT_TABLE in sql:
            assert params == (["DOC-1", "DOC-2", "DOC-3"],)
            return [
                {"document_no": "DOC-1", "corp_code": "CORP_A", "owner_pu": "PU_A", "visibility": "private"},
                {"document_no": "DOC-2", "corp_code": "CORP_A", "owner_pu": "PU_B", "visibility": "public"},
                {"document_no": "DOC-3", "corp_code": "CORP_B", "owner_pu": "PU_A", "visibility": "public"},
            ]
        if lw.ANALYSIS_CUSTOMER_AFFILIATE_TABLE in sql:
            return [{"parent_label": "Group", "child_label": "Plant", "relation_name": "customer_affiliate", "content_source": "llm"}]
        if lw.ANALYSIS_CUSTOMER_TABLE in sql:
            return [
                {"account_name": "Group", "parent_name": None, "tier_name": "group", "entity_role": "고객", "content_source": "llm"},
                {"account_name": "Plant", "parent_name": "Group", "tier_name": "plant", "entity_role": "고객", "content_source": "llm"},
                {"account_name": "Other", "parent_name": None, "tier_name": "hq", "entity_role": "고객", "content_source": "llm"},
            ]
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_query", query)
    actor = {"corp_code": "CORP_A", "pu_code": "PU_A", "roles": ["reader"], "account_id": "reader-1"}
    master = lw.load_customer_master(object(), actor=actor)
    assert {account["account_name"] for account in master["accounts"]} == {"Group", "Plant"}
    assert master["accounts"][0]["document_nos"] == ["DOC-1"]
    assert master["accounts"][1]["document_nos"] == ["DOC-2"]
    assert master["edges"] == []


def test_keyman_refresh_preserves_existing_event_history() -> None:
    """Replace one Keyman slice without rebuilding away event and source-actor KG rows."""
    graph = {
        "nodes": [
            {"id": "kg:document:DOC-1", "type": "document", "document_no": "DOC-1", "label": "Fixture"},
            {"id": "kg:event:old", "type": "event", "label": "Opened", "document_nos": ["DOC-1"]},
            {"id": "kg:person:old", "type": "person", "label": "Old", "identity_source": "llm", "document_nos": ["DOC-1"]},
            {"id": "kg:org:old", "type": "organization", "label": "Old Org", "identity_source": "llm", "document_nos": ["DOC-1"]},
        ],
        "edges": [
            {"source": "kg:document:DOC-1", "target": "kg:event:old", "relation": "document_event", "evidence_id": "ROW-1"},
            {"source": "kg:document:DOC-1", "target": "kg:person:old", "relation": "keyman_our_side", "evidence_id": "DOC-1"},
            {"source": "kg:person:old", "target": "kg:org:old", "relation": "member_of", "evidence_id": "DOC-1"},
        ],
    }
    refreshed = lw.refresh_document_keyman_knowledge_graph(
        graph,
        {
            "type": "document",
            "document_no": "DOC-1",
            "title_sample": "Fixture",
            "keyman_our_side": [{"person_name": "New", "org_name": "New Org"}],
            "keyman_counterpart_side": [],
        },
    )
    labels = {node.get("label") for node in refreshed["nodes"]}
    assert {"Opened", "New", "New Org"} <= labels
    assert "Old" not in labels and "Old Org" not in labels
    assert any(edge["target"] == "kg:event:old" for edge in refreshed["edges"])
    assert any(edge["relation"] == "keyman_our_side" for edge in refreshed["edges"])


def test_load_persisted_snapshot_overrides_and_outbox_contract(monkeypatch) -> None:
    """Rehydrate JSON payloads, apply database overrides, and keep durable outbox writes scoped."""
    def query(_connection, sql: str, _params: tuple[object, ...] = ()):  # noqa: ANN001
        if "to_regclass" in sql:
            return [{"table_name": "public.fixture"}]
        if lw.ANALYSIS_RUN_TABLE in sql:
            return [{"row_count": 3, "document_count": 1, "thread_count": 1, "metadata_payload": json.dumps({"run": "fixture"})}]
        if lw.ANALYSIS_DOCUMENT_TABLE in sql:
            return [{
                "document_no": "DOC-1", "acthguid": "THREAD-1", "title_sample": "Fixture", "corp_code": "CORP_A", "owner_pu": "PU_A", "entity_role": "시장", "visibility_code": "private", "korean_summary": "summary", "keyman_source": "llm", "keyman_status": "ready", "keyman_our_side": json.dumps([{ "person_name": "A" }]), "keyman_counterpart_side": "[]", "first_event": "opened", "first_stage": "open", "first_status": "active", "roles_and_responsibilities": json.dumps([{ "role": "owner" }]), "issue_tickets": "[]", "document_events": json.dumps([{ "guid": "row-1", "event": "opened" }]),
            }]
        if lw.ANALYSIS_EDGE_TABLE in sql:
            return [{"source_node": "doc:DOC-1", "target_node": "row:1", "relation_name": "observed", "evidence_status": lw.EVIDENCE_OBSERVED, "acthguid": "THREAD-1"}]
        if lw.ANALYSIS_AFFILIATE_TABLE in sql:
            return [{"parent_label": "Corp A", "child_label": "Corp A PU A", "relation_name": "corp_pu"}]
        if lw.ANALYSIS_KG_NODE_TABLE in sql:
            return [{"node_id": "kg:document:DOC-1", "node_type": "document", "label": "Fixture", "document_no": "DOC-1", "metadata_payload": json.dumps({"document_nos": ["DOC-1"]})}]
        if lw.ANALYSIS_KG_EDGE_TABLE in sql:
            return [{"source_node": "kg:document:DOC-1", "target_node": "kg:document:DOC-1", "relation_name": "observed", "evidence_id": "row-1"}]
        if lw.ANALYSIS_OVERRIDE_TABLE in sql:
            return [{"document_no": "DOC-1", "visibility_code": "public", "keyman_our_side": json.dumps([{ "person_name": "Override" }]), "keyman_counterpart_side": "[]"}]
        if lw.ANALYSIS_TICKET_TABLE in sql:
            return [{"ticket_id": "ticket-1", "document_no": "DOC-1", "title": "Follow up", "status": "open", "assignee": None, "created_by": "account-1"}]
        if lw.ANALYSIS_EVENT_OUTBOX_TABLE in sql:
            return [{"event_id": "pending-1", "event_type": "visibility", "document_no": "DOC-1", "actor_id": "account-1", "payload": {}}]
        return []

    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(lw, "_database_query", query)
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    payload = lw.load_persisted_analysis_payload(
        object(),
        {"corp_code": "CORP_A", "pu_code": "PU_A", "roles": ["reader"]},
        include_knowledge_graph=True,
    )
    assert payload["metadata"]["run"] == "fixture"
    assert payload["nodes"][0]["document_events"][0]["guid"] == "row-1"
    assert payload["knowledge_graph"]["nodes"][0]["document_nos"] == ["DOC-1"]
    updated = lw.load_database_overrides(object(), payload)
    assert updated["nodes"][0]["visibility"] == "public"
    assert updated["nodes"][0]["issue_tickets"][0]["ticket_id"] == "ticket-1"
    event_id = lw.enqueue_event_outbox(object(), "visibility", "DOC-1", "account-1", {"visibility": "public"})
    assert len(event_id) == 32
    assert lw.pending_event_outbox(object(), limit=500)[0]["event_id"] == "pending-1"
    lw.mark_event_published(object(), event_id)
    assert any("published_at" in sql for sql, _ in statements)


def test_load_persisted_payload_is_empty_before_snapshot_schema(monkeypatch) -> None:
    """A fresh direct PostgreSQL database must not enter an aborted transaction while loading."""
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: False)
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected query")),
    )

    payload = lw.load_persisted_analysis_payload(object(), include_knowledge_graph=True)

    assert payload["nodes"] == []
    assert payload["knowledge_graph"] == {"nodes": [], "edges": []}
    assert payload["metadata"]["document_count"] == 0


def test_workspace_surface_and_period_filter_stay_off_the_graph(monkeypatch) -> None:
    """Workspace recapture reads run metadata and reports, not document or KG tables."""
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)

    def query(_connection, sql: str, params: tuple[object, ...] = ()):  # noqa: ANN001
        if lw.ANALYSIS_RUN_TABLE in sql:
            return [{"row_count": 43814, "document_count": 43707, "thread_count": 42467, "metadata_payload": {}}]
        if lw.ANALYSIS_PERIOD_REPORT_TABLE in sql:
            return [{
                "report_id": "weekly-pu-D02",
                "period_kind": "weekly",
                "period_start": "2026-08-03",
                "period_end": "2026-08-09",
                "slice_kind": "pu",
                "slice_key": "D02",
                "document_count": 10,
                "judge_verdict": "pass",
                "judge_source": "live_http",
                "report_payload": {"judge": {"verdict": "pass"}, "linked_scores": []},
            }]
        if lw.ANALYSIS_LINKED_SCORE_TABLE in sql:
            return [{
                "score_id": "score-1",
                "report_id": "weekly-pu-D02",
                "person_or_group": "D02",
                "factor_id": "gm-pos-delivery",
                "theta": 0.2,
                "standard_error": 0.1,
                "linking_method": "fipc",
                "calibration_source": "fast_mlsirm",
            }]
        if lw.ANALYSIS_CUSTOMER_TABLE in sql:
            return [{"account_name": "삼성전자", "parent_name": None, "tier_name": "group", "entity_role": "고객", "content_source": "llm"}]
        if lw.ANALYSIS_CUSTOMER_AFFILIATE_TABLE in sql:
            return [{"parent_label": "삼성전자", "child_label": "삼성전자 평택사업장", "relation_name": "customer_affiliate", "content_source": "llm"}]
        if lw.ANALYSIS_CUSTOMER_DOCUMENT_TABLE in sql:
            return [{"account_name": "삼성전자", "document_no": "DOC-1"}]
        if lw.ANALYSIS_AFFILIATE_TABLE in sql:
            return []
        if lw.ANALYSIS_DOCUMENT_TABLE in sql or lw.ANALYSIS_KG_NODE_TABLE in sql:
            raise AssertionError(sql)
        return []

    monkeypatch.setattr(lw, "_database_query", query)
    surface = lw.load_workspace_surface(object())
    assert surface["analytics"]["total_rows"] == 43814
    parent_of = surface["customer_master"]["parent_of"]
    assert parent_of["삼성전자 한국"] == "삼성전자"
    assert parent_of["삼성전자 본사"] == "삼성전자 한국"
    assert parent_of["삼성전자 평택사업장"] == "삼성전자 본사"
    assert surface["period_reports"][0]["linked_scores"][0]["calibration_source"] == "fast_mlsirm"
    assert surface["period_reports"][0]["linked_scores"][0]["factor_family"] == "general_management"
    filtered = lw.filter_period_reports_for_actor(surface["period_reports"], {"pu_code": "D02"})
    assert [item["slice_key"] for item in filtered] == ["D02"]


def test_persist_operational_surfaces_deletes_customer_child_before_parent(monkeypatch) -> None:
    """Replace customer rows without an AccessExclusive parent-table lock."""
    statements: list[str] = []
    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append(sql),
    )
    connection = _RecordingConnection()
    payload = {
        "customer_master": {
            "source": "llm",
            "accounts": [{"account_name": "Acme", "parent_name": None, "tier": "hq", "document_nos": ["DOC-1"]}],
            "edges": [],
        }
    }
    lw.persist_operational_surfaces(connection, payload, [])
    joined = "\n".join(statements)
    assert "DELETE FROM analysis_customer_document_links" in joined
    assert "DELETE FROM analysis_customer_accounts" in joined


def test_persist_operational_surfaces_writes_llm_work_appointments_and_customer_evidence(monkeypatch) -> None:
    """Persist each popup operational surface in its normalized table with source evidence."""
    statements: list[str] = []
    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)
    monkeypatch.setattr(lw, "_database_exec", lambda _connection, sql, params=(): statements.append(sql))
    monkeypatch.setattr(lw, "persist_period_reports", lambda _connection, reports, **_kwargs: len(reports))
    connection = _RecordingConnection()
    documents = [
        {
            "document_no": "DOC-1",
            "todo_items": [{"todo_id": "todo-1", "ticket_id": "ticket-1", "title": "Follow up", "body": "Call customer"}],
            "calendar_items": [{"calendar_id": "calendar-1", "ticket_id": "ticket-1", "title": "Follow up", "body": "Call customer", "occurred_on": "2026-09-01"}],
            "appointments": [{"appointment_id": "appointment-1", "occurred_on": "2026-09-02", "label": "고객 약속", "excerpt": "Review meeting", "source": "llm"}],
        }
    ]
    payload = {
        "customer_master": {
            "source": "llm",
            "accounts": [
                {"account_name": "Acme Group", "tier": "group", "document_nos": ["DOC-1"]},
                {"account_name": "Acme Division", "tier": "hq", "parent_name": "Acme Group", "document_nos": ["DOC-1"]},
            ],
            "edges": [{"parent": "Acme Group", "child": "Acme Division", "relation": "customer_affiliate", "source": "llm"}],
        },
        "period_reports": [{"report_id": "report-1"}],
    }

    persisted = lw.persist_operational_surfaces(connection, payload, documents)
    lw.persist_operational_surfaces(
        connection, payload, documents, ensure_schema=False
    )

    assert persisted == {
        "ticket_rows": 1,
        "todo_rows": 1,
        "calendar_rows": 1,
        "appointment_rows": 1,
        "customer_account_rows": 2,
        "customer_document_rows": 2,
        "report_rows": 1,
    }
    batch_sql = "\n".join(sql for sql, _values in connection.recording_cursor.executemany_calls)
    assert lw.ANALYSIS_TICKET_TABLE in batch_sql
    assert lw.ANALYSIS_TODO_TABLE in batch_sql
    assert lw.ANALYSIS_CALENDAR_TABLE in batch_sql
    assert lw.ANALYSIS_APPOINTMENT_TABLE in batch_sql
    assert lw.ANALYSIS_CUSTOMER_TABLE in batch_sql
    assert lw.ANALYSIS_CUSTOMER_DOCUMENT_TABLE in batch_sql
    assert lw.ANALYSIS_CUSTOMER_AFFILIATE_TABLE in batch_sql
    assert any("DELETE FROM analysis_todo_items" in statement for statement in statements)


def test_persist_issue_work_items_creates_the_parent_ticket_before_work(monkeypatch) -> None:
    """Keep automatic work in 3NF even when it is persisted outside a full snapshot."""
    statements: list[str] = []
    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append(sql),
    )

    lw.persist_issue_work_items(
        object(),
        {
            "todo_id": "todo-1",
            "ticket_id": "ticket-1",
            "document_no": "DOC-1",
            "title": "Follow up",
            "body": "Call customer",
            "status": "open",
        },
        {
            "calendar_id": "calendar-1",
            "ticket_id": "ticket-1",
            "document_no": "DOC-1",
            "title": "Follow up",
            "body": "Call customer",
            "occurred_on": "2026-09-01",
        },
    )

    assert lw.ANALYSIS_TICKET_TABLE in statements[0]
    assert lw.ANALYSIS_TODO_TABLE in statements[1]
    assert lw.ANALYSIS_CALENDAR_TABLE in statements[2]


def test_operational_calendar_schema_keeps_only_evidence_backed_dates(monkeypatch) -> None:
    """Migrate legacy pending rows to an explicit unscheduled calendar state."""
    statements: list[str] = []
    monkeypatch.setattr(lw, "_database_exec", lambda _connection, sql, params=(): statements.append(sql))
    monkeypatch.setattr(lw, "default_factor_definitions", lambda: [])
    monkeypatch.setattr(lw, "default_factor_items", lambda: [])
    monkeypatch.setattr(lw, "default_evaluation_metrics", lambda: [])

    lw._ensure_operational_tables(object())

    assert any(
        f"ALTER TABLE {lw.ANALYSIS_CALENDAR_TABLE} ALTER COLUMN occurred_on DROP NOT NULL" in sql
        for sql in statements
    )
    assert any(
        f"UPDATE {lw.ANALYSIS_CALENDAR_TABLE}" in sql
        and "content_source = 'pending_llm'" in sql
        and "occurred_on IS NOT NULL" in sql
        for sql in statements
    )


def test_persist_period_reports_upserts_on_score_id(monkeypatch) -> None:
    """Re-running the shipped report persist updates the same score_id instead of inserting twice."""
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)
    connection = _RecordingConnection()
    report = {
        "report_id": "rpt-fixture",
        "period_kind": "weekly",
        "period_start": "2026-08-10",
        "period_end": "2026-08-16",
        "slice_kind": "pu",
        "slice_key": "PU01",
        "document_count": 2,
        "judge": {"verdict": "pass", "source": "llm_judge"},
        "linked_scores": [
            {
                "score_id": "scr-fixture-1",
                "person_or_group": "PU01",
                "factor_id": "gm-pos-delivery",
                "theta": 0.2,
                "standard_error": 0.4,
                "linking_method": "fipc",
                "calibration_source": "fast_mlsirm",
            }
        ],
        "calibration_rows": [
            {
                "calibration_run_id": "cal-fixture",
                "item_id": "item-gm-pos-1",
                "factor_id": "gm-pos-delivery",
                "discrimination": 1.1,
                "difficulty": -0.2,
                "report_count": 2,
                "engine_name": "fast_mlsirm_rust",
                "estimator_name": "mmle_fipc",
                "calibration_status": "calibrated",
            }
        ],
    }
    assert lw.persist_period_reports(connection, [report]) == 1
    assert lw.persist_period_reports(connection, [report]) == 1
    assert lw.persist_period_reports(connection, [report, {"period_kind": "weekly"}]) == 2
    sql_text = "\n".join(sql for sql, _ in connection.recording_cursor.executemany_calls)
    assert "ON CONFLICT (report_id) DO UPDATE" in sql_text
    assert "ON CONFLICT (score_id) DO UPDATE" in sql_text
    assert "ON CONFLICT (calibration_run_id, item_id) DO UPDATE" in sql_text
    assert any("DELETE FROM" in sql and "report_id" in sql for sql, _ in connection.recording_cursor.execute_calls)
    assert any(
        f"DELETE FROM {lw.ANALYSIS_LINKED_SCORE_TABLE}" in sql and "NOT EXISTS" in sql
        for sql, _ in connection.recording_cursor.execute_calls
    )
    assert "TRUNCATE" not in sql_text
    assert all("TRUNCATE" not in sql for sql, _ in statements)


def test_persist_period_reports_normalizes_longitudinal_state_3nf(monkeypatch) -> None:
    """Persist state specification, run metrics, and observations separately from report JSON."""
    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)
    connection = _RecordingConnection()
    state = {
        "status": "computed",
        "state_kind": "random_intercept_slope",
        "state_spec_fingerprint": "a" * 64,
        "design_fingerprint": "b" * 64,
        "schema_version": "1.0",
        "include_lagged_response_dependence": False,
        "ar_coefficient": 0.0,
        "engine": "rust_cpu_multithreaded",
        "rmse": 0.1,
        "observed_count": 2,
        "transition_count": 0,
        "respondent_ids": ["report_group_fixture"],
        "occasion_records": [
            {
                "respondent_id": "report_group_fixture",
                "occasion_id": "occasion_fixture_0",
                "sequence_index": 20260801,
                "time_offset_milliseconds": 1,
            },
            {
                "respondent_id": "report_group_fixture",
                "occasion_id": "occasion_fixture_1",
                "sequence_index": 20260802,
                "time_offset_milliseconds": 86_401_000,
            },
        ],
        "state": [0.2, 0.3],
        "intercepts": [0.2],
        "slopes": [0.1],
        "observed_values": [0.2, 0.3],
    }
    report = {
        "report_id": "rpt-state-fixture",
        "period_kind": "weekly",
        "period_start": "2026-08-01",
        "period_end": "2026-08-07",
        "slice_kind": "pu",
        "slice_key": "PU01",
        "document_count": 2,
        "judge": {"verdict": "pass", "source": "llm_judge"},
        "longitudinal_state": state,
        "linked_scores": [],
    }
    assert lw.persist_period_reports(connection, [report]) == 1
    sql_text = "\n".join(sql for sql, _ in connection.recording_cursor.executemany_calls)
    assert lw.ANALYSIS_LONGITUDINAL_SPEC_TABLE in sql_text
    assert lw.ANALYSIS_LONGITUDINAL_RUN_TABLE in sql_text
    assert lw.ANALYSIS_LONGITUDINAL_OBSERVATION_TABLE in sql_text
    assert any(lw.ANALYSIS_LONGITUDINAL_OBSERVATION_TABLE in sql for sql, _ in connection.recording_cursor.execute_calls)


def test_longitudinal_state_rows_fail_closed_for_untrusted_connector_payload() -> None:
    """Reject malformed state metadata instead of creating partial calibration rows."""
    assert lw._longitudinal_state_rows([{"longitudinal_state": {"status": "unavailable"}}]) == ([], [], [], [])
    assert lw._longitudinal_state_rows(
        [{
            "report_id": "bad-state",
            "longitudinal_state": {
                "status": "computed",
                "state_spec_fingerprint": "short",
                "design_fingerprint": "short",
                "occasion_records": [],
                "state": [],
            },
        }]
    ) == ([], [], [], [])


def test_longitudinal_state_rows_cover_connector_boundary_cases() -> None:
    """Exercise every state-payload rejection and optional-observation branch."""
    def report(state: dict) -> dict:
        return {"report_id": "state-boundary", "longitudinal_state": state}

    def state(**updates: object) -> dict:
        value = {
            "status": "computed",
            "state_spec_fingerprint": "c" * 64,
            "design_fingerprint": "d" * 64,
            "state_kind": "random_intercept_slope",
            "rmse": 0.0,
            "observed_count": 1,
            "transition_count": 0,
            "respondent_ids": ["report_group_boundary"],
            "occasion_records": [{
                "respondent_id": "report_group_boundary",
                "occasion_id": "occasion_boundary",
                "sequence_index": 1,
                "time_offset_milliseconds": 1,
            }],
            "state": [0.2],
            "intercepts": [0.2],
            "slopes": [0.0],
            "observed_values": [0.2],
        }
        value.update(updates)
        return value

    assert lw._longitudinal_state_rows([report(state(rmse="bad"))]) == ([], [], [], [])
    assert lw._longitudinal_state_rows([report(state(observed_count=-1))]) == ([], [], [], [])
    assert lw._longitudinal_state_rows([report(state(occasion_records="bad"))]) == ([], [], [], [])
    assert lw._longitudinal_state_rows([report(state(occasion_records=[None], state=[]))]) == ([], [], [], [])
    assert lw._longitudinal_state_rows([report(state(occasion_records=[{}], state=[]))])[2] == []
    assert lw._longitudinal_state_rows([report(state(occasion_records=[{}], state=[0.2]))])[2] == []
    assert lw._longitudinal_state_rows([report(state(occasion_records=[{"respondent_id": "", "occasion_id": "occasion_boundary"}], state=[0.2]))])[2] == []
    assert lw._longitudinal_state_rows([report(state(occasion_records=[{"respondent_id": "report_group_boundary", "occasion_id": ""}], state=[0.2]))])[2] == []
    assert lw._longitudinal_state_rows([report(state(occasion_records=[{"respondent_id": "report_group_boundary", "occasion_id": "occasion_boundary", "sequence_index": "bad", "time_offset_milliseconds": 1}], state=[0.2]))])[2] == []
    assert lw._longitudinal_state_rows([report(state(state=[float("nan")]))])[2] == []
    assert lw._longitudinal_state_rows([report(state(observed_values=[]))])[2][0][5] is None
    assert lw._longitudinal_state_rows([report(state(observed_values=["bad"]))])[2][0][5] is None


def test_report_document_loader_and_actor_filter_fail_closed(monkeypatch) -> None:
    """Keep reports behind the same source-document ABAC boundary as the document API."""
    rows = [
        {
            "document_no": "DOC-PUBLIC",
            "acthguid": "THREAD-1",
            "title_sample": "Public",
            "corp_code": "CORP-1",
            "owner_pu": "PU-2",
            "entity_role": "customer",
            "visibility_code": lw.VISIBILITY_PUBLIC,
            "korean_summary": "summary",
        },
        {
            "document_no": "DOC-PRIVATE",
            "acthguid": "THREAD-2",
            "title_sample": "Private",
            "corp_code": "CORP-1",
            "owner_pu": "PU-2",
            "entity_role": "customer",
            "visibility_code": lw.VISIBILITY_PRIVATE,
            "korean_summary": "summary",
        },
        {
            "document_no": "DOC-OTHER-CORP",
            "acthguid": "THREAD-3",
            "title_sample": "Other",
            "corp_code": "CORP-2",
            "owner_pu": "PU-1",
            "entity_role": "customer",
            "visibility_code": lw.VISIBILITY_PUBLIC,
            "korean_summary": "summary",
        },
    ]
    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: True)
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: rows)
    documents = lw.load_report_document_nodes(object())
    assert documents[0]["visibility"] == lw.VISIBILITY_PUBLIC
    assert lw.load_authorized_report_document_numbers(
        object(), {"corp_code": "CORP-1", "pu_code": "PU-1", "roles": ["reader"]}
    ) == {"DOC-PUBLIC"}
    assert lw.load_authorized_report_document_numbers(object(), None) == {
        "DOC-PUBLIC",
        "DOC-PRIVATE",
        "DOC-OTHER-CORP",
    }

    reports = [
        {"report_id": "visible", "slice_kind": "team", "document_nos": ["DOC-PUBLIC"]},
        {"report_id": "hidden", "slice_kind": "team", "document_nos": ["DOC-PRIVATE"]},
        {"report_id": "missing-evidence", "slice_kind": "team", "document_nos": []},
    ]
    assert [
        report["report_id"]
        for report in lw.filter_period_reports_for_actor(
            reports,
            {"pu_code": "PU-1"},
            visible_document_numbers={"DOC-PUBLIC"},
        )
    ] == ["visible"]

    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: False)
    assert lw.load_report_document_nodes(object()) == []
    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: True)
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    assert lw.load_report_document_nodes(object()) == []


def test_valkey_resp_and_stream_contract(monkeypatch) -> None:
    """Use the Redis-compatible protocol directly for health and Stream append operations."""
    real_open_connection = lw._open_valkey_connection
    assert lw._valkey_read_reply(_BytesSocket(b"+PONG\r\n")) == "PONG"
    assert lw._valkey_read_reply(_BytesSocket(b"$3\r\nabc\r\n")) == b"abc"
    with pytest.raises(RuntimeError, match="valkey_error"):
        lw._valkey_read_reply(_BytesSocket(b"-NOAUTH\r\n"))

    ping_socket = _BytesSocket(b"+PONG\r\n")
    monkeypatch.setattr(lw, "_open_valkey_connection", lambda *_args, **_kwargs: ping_socket)
    assert lw.valkey_ping("redis://fixture") is True
    assert ping_socket.closed is True

    stream_socket = _BytesSocket(b"$3\r\n1-0\r\n")
    monkeypatch.setattr(lw, "_open_valkey_connection", lambda *_args, **_kwargs: stream_socket)
    assert lw.publish_valkey_event({"event_id": "event-1", "document_no": "DOC-1"}, url="redis://fixture") == "1-0"
    assert b"XADD" in stream_socket.sent
    assert stream_socket.closed is True

    opened = _BytesSocket(b"")
    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr(lw, "_open_valkey_connection", real_open_connection)
    monkeypatch.setattr(lw.socket, "create_connection", lambda *_args, **_kwargs: opened)
    monkeypatch.setattr(lw, "_valkey_command", lambda _connection, *parts: commands.append(parts) or "OK")
    assert lw._open_valkey_connection("redis://user:secret@cache.example:6380/2") is opened
    assert commands == [("AUTH", "user", "secret"), ("SELECT", "2")]
    with pytest.raises(ValueError, match="redis://"):
        lw._open_valkey_connection("http://cache.example")


def test_persisted_document_detail_rehydrates_product_surfaces_and_predicted_kg_links(monkeypatch) -> None:
    """Rehydrate one direct-PostgreSQL document with managed fields and bounded KG context."""
    document = {
        "document_no": "DOC-1",
        "acthguid": "THREAD-1",
        "title_sample": "Fixture customer milestone",
        "corp_code": "CORP-1",
        "owner_pu": "PU-1",
        "entity_role": "고객",
        "visibility_code": lw.VISIBILITY_PRIVATE,
        "korean_summary": "fixture summary",
        "keyman_source": "llm",
        "keyman_status": "derived",
        "keyman_our_side": json.dumps([{"person_name": "A", "org_name": "Org A"}]),
        "keyman_counterpart_side": json.dumps([{"person_name": "B", "org_name": "Org B"}]),
        "first_event": "milestone",
        "first_stage": "proposal",
        "first_status": "open",
        "roles_and_responsibilities": json.dumps([{"role": "owner", "name": "A"}]),
        "issue_tickets": json.dumps([{"ticket_id": "derived-ticket"}]),
        "document_events": json.dumps([{"event": "milestone", "guid": "ROW-1"}]),
    }
    tables = {
        lw.ANALYSIS_DOCUMENT_TABLE,
        lw.ANALYSIS_OVERRIDE_TABLE,
        lw.ANALYSIS_TICKET_TABLE,
        lw.ANALYSIS_TODO_TABLE,
        lw.ANALYSIS_CALENDAR_TABLE,
        lw.ANALYSIS_APPOINTMENT_TABLE,
        lw.ANALYSIS_EDGE_TABLE,
        lw.ANALYSIS_KG_NODE_TABLE,
        lw.ANALYSIS_KG_EDGE_TABLE,
    }
    persisted_predicted: list[dict] = []
    candidate_title = "Fixture customer follow-up"

    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if lw.ANALYSIS_OVERRIDE_TABLE in sql:
            return [{
                "visibility_code": lw.VISIBILITY_PUBLIC,
                "keyman_our_side": json.dumps([{"person_name": "Override", "org_name": "Org A"}]),
                "keyman_counterpart_side": json.dumps([{"person_name": "B", "org_name": "Org B"}]),
            }]
        if lw.ANALYSIS_TICKET_TABLE in sql:
            return [{"ticket_id": "ticket-1", "document_no": "DOC-1", "title": "Follow up", "status": "open", "assignee": "A", "created_by": "actor"}]
        if lw.ANALYSIS_TODO_TABLE in sql:
            return [{"todo_id": "todo-1", "ticket_id": "ticket-1", "document_no": "DOC-1", "title": "Follow up", "body": "", "status": "open", "content_source": "llm"}]
        if lw.ANALYSIS_CALENDAR_TABLE in sql:
            return [{"calendar_id": "calendar-1", "ticket_id": "ticket-1", "document_no": "DOC-1", "title": "Follow up", "body": "", "occurred_on": "2026-08-13", "content_source": "llm"}]
        if lw.ANALYSIS_APPOINTMENT_TABLE in sql:
            return [{"appointment_id": "appointment-1", "document_no": "DOC-1", "occurred_on": "2026-08-13", "label": "review", "excerpt": "", "content_source": "llm"}]
        if lw.ANALYSIS_KG_NODE_TABLE in sql:
            return [{"node_id": "kg:document:DOC-1", "node_type": "document", "label": "Fixture", "document_no": "DOC-1", "metadata_payload": json.dumps({"entity_role": "고객"})}]
        if lw.ANALYSIS_KG_EDGE_TABLE in sql:
            return [{"source_node": "kg:document:DOC-1", "target_node": "kg:topic:customer", "relation_name": "about", "evidence_id": "ROW-1", "evidence_status": lw.EVIDENCE_INFERRED, "reason": "fixture"}]
        if lw.ANALYSIS_EDGE_TABLE in sql:
            return []
        if lw.ANALYSIS_DOCUMENT_TABLE in sql and "WHERE corp_code" in sql:
            return [{"document_no": "DOC-2", "acthguid": "THREAD-2", "entity_role": "고객", "title_sample": candidate_title}]
        if lw.ANALYSIS_DOCUMENT_TABLE in sql:
            return [document]
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, table: table in tables)
    monkeypatch.setattr(lw, "_database_query", query)
    monkeypatch.setattr(lw, "ensure_lineage_edge_reason_column", lambda _connection: None)
    monkeypatch.setattr(lw, "ensure_knowledge_graph_edge_evidence_columns", lambda _connection: None)
    monkeypatch.setattr(lw, "persist_lineage_relatedness_edges", lambda _connection, edges: persisted_predicted.extend(edges))

    detail = lw.load_persisted_document_detail(object(), "DOC-1")

    assert detail is not None
    assert detail["document"]["visibility"] == lw.VISIBILITY_PUBLIC
    assert detail["document"]["keyman_source"] == "user_override"
    assert detail["document"]["keyman_status"] == "managed"
    assert detail["document"]["keyman_our_side"][0]["person_name"] == "Override"
    assert detail["document"]["issue_tickets"] == [{"ticket_id": "ticket-1", "document_no": "DOC-1", "title": "Follow up", "status": "open", "assignee": "A", "created_by": "actor"}]
    assert detail["document"]["todo_items"][0]["source"] == "llm"
    assert detail["document"]["calendar_items"][0]["source"] == "llm"
    assert detail["document"]["appointments"][0]["source"] == "llm"
    assert persisted_predicted == []
    assert detail["knowledge_graph"]["edges"][0]["reason"] == "fixture"
    assert detail["event_lineage"]["beads"]
    materialized_detail = lw.load_persisted_document_detail(
        object(),
        "DOC-1",
        persist_predicted_relatedness=True,
    )
    assert materialized_detail is not None
    assert persisted_predicted[0]["evidence_status"] == lw.EVIDENCE_PREDICTED
    candidate_title = "Unrelated market outlook"
    persisted_predicted.clear()
    lw.load_persisted_document_detail(object(), "DOC-1")
    assert persisted_predicted == []


def test_persisted_document_detail_returns_none_without_document_table(monkeypatch) -> None:
    """Fail closed when the PostgreSQL snapshot table has not been materialized."""
    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: False)
    assert lw.load_persisted_document_detail(object(), "DOC-1") is None


def test_persisted_document_detail_handles_absent_rows_and_optional_surface_tables(monkeypatch) -> None:
    """Keep a document detail usable while optional operational tables are still absent."""
    monkeypatch.setattr(
        lw,
        "_database_table_exists",
        lambda _connection, table: table == lw.ANALYSIS_DOCUMENT_TABLE,
    )
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    assert lw.load_persisted_document_detail(object(), "DOC-404") is None

    document = {
        "document_no": "DOC-1",
        "acthguid": "THREAD-1",
        "title_sample": "Fixture",
        "corp_code": "CORP-1",
        "owner_pu": "PU-1",
        "entity_role": "시장",
        "visibility_code": lw.VISIBILITY_PUBLIC,
        "korean_summary": "fixture summary",
        "keyman_source": "heuristic",
        "keyman_status": "not_requested",
    }
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [document])
    detail = lw.load_persisted_document_detail(object(), "DOC-1")
    assert detail is not None
    assert "todo_items" not in detail["document"]
    assert detail["event_lineage"]["beads"][0]["kind"] == "event"


def test_visible_document_index_enforces_postgres_abac_and_pagination_bounds(monkeypatch) -> None:
    """Query only the actor's direct-PostgreSQL scope with stable list metadata."""
    actor = {"corp_code": "CORP-1", "pu_code": "PU-1", "roles": ["reader"]}
    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: False)
    assert lw.load_visible_document_index(object(), actor, 0, -4) == {
        "items": [],
        "total": 0,
        "limit": 1,
        "offset": 0,
    }

    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: True)
    assert lw.load_visible_document_index(object(), {}, 999, 2) == {
        "items": [],
        "total": 0,
        "limit": 500,
        "offset": 2,
    }

    calls: list[tuple[str, tuple[object, ...]]] = []

    def query(_connection, sql: str, params=()):  # noqa: ANN001
        calls.append((sql, tuple(params)))
        if "COUNT(*)" in sql:
            return [{"total": 2}]
        return [{
            "document_no": "DOC-1",
            "acthguid": "THREAD-1",
            "title_sample": "Fixture",
            "corp_code": "CORP-1",
            "owner_pu": "PU-1",
            "entity_role": "고객",
            "visibility_code": lw.VISIBILITY_PUBLIC,
        }]

    monkeypatch.setattr(lw, "_database_query", query)
    reader_index = lw.load_visible_document_index(object(), actor, 999, 3)
    assert reader_index == {
        "items": [{
            "document_no": "DOC-1",
            "acthguid": "THREAD-1",
            "title": "Fixture",
            "corp_code": "CORP-1",
            "owner_pu": "PU-1",
            "row_count": 0,
            "first_row_ts": None,
            "last_row_ts": None,
            "entity_role": "고객",
            "visibility": lw.VISIBILITY_PUBLIC,
        }],
        "total": 2,
        "limit": 500,
        "offset": 3,
    }
    assert all("visibility_code = %s OR owner_pu = %s" in sql for sql, _ in calls)
    assert calls[0][1] == ("CORP-1", lw.VISIBILITY_PUBLIC, "PU-1")
    assert calls[1][1] == ("CORP-1", lw.VISIBILITY_PUBLIC, "PU-1", 500, 3)

    calls.clear()
    lw.load_visible_document_index(object(), actor, 10, 0, "  fixture  ")
    assert all("document_no ILIKE %s" in sql for sql, _ in calls)
    assert calls[0][1] == (
        "CORP-1",
        lw.VISIBILITY_PUBLIC,
        "PU-1",
        "%fixture%",
        "%fixture%",
        "%fixture%",
        "%fixture%",
    )
    assert calls[1][1][-2:] == (10, 0)

    calls.clear()
    admin_index = lw.load_visible_document_index(
        object(), {"corp_code": "CORP-1", "roles": ["admin"]}, 4, 0
    )
    assert admin_index["total"] == 2
    assert all("visibility_code = %s OR owner_pu = %s" not in sql for sql, _ in calls)
    assert calls[0][1] == ("CORP-1",)
    assert calls[1][1] == ("CORP-1", 4, 0)


def test_lineage_query_indexes_cover_inferred_document_ordering(monkeypatch) -> None:
    """Install the two partial indexes used by the document-list priority lookup."""
    statements: list[str] = []
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: False)
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, _params=(): statements.append(sql),
    )
    lw.ensure_lineage_query_indexes(object())
    assert statements == []

    monkeypatch.setattr(
        lw,
        "_database_table_exists",
        lambda _connection, table_name: table_name == lw.ANALYSIS_EDGE_TABLE,
    )
    lw.ensure_lineage_query_indexes(object())

    assert any("analysis_lineage_edges_inferred_source_index" in sql for sql in statements)
    assert any("analysis_lineage_edges_inferred_target_index" in sql for sql in statements)
    assert all("evidence_status IN ('inferred', 'predicted')" in sql for sql in statements)


def test_legacy_shared_thread_edges_are_demoted_in_lineage_and_knowledge_graph(monkeypatch) -> None:
    """Keep a historical shared identifier from being presented as an observed transition."""
    calls: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: False)
    assert lw.demote_legacy_shared_thread_edges(object()) == {
        "lineage_edges": 0,
        "knowledge_graph_edges": 0,
    }

    def query(_connection, statement, params=()):  # noqa: ANN001
        calls.append((statement, tuple(params)))
        return [{"migrated": 1}] * (2 if lw.ANALYSIS_EDGE_TABLE in statement else 3)

    monkeypatch.setattr(
        lw,
        "_database_table_exists",
        lambda _connection, table_name: table_name in {lw.ANALYSIS_EDGE_TABLE, lw.ANALYSIS_KG_EDGE_TABLE},
    )
    monkeypatch.setattr(lw, "ensure_lineage_edge_reason_column", lambda _connection: None)
    monkeypatch.setattr(lw, "ensure_knowledge_graph_edge_evidence_columns", lambda _connection: None)
    monkeypatch.setattr(lw, "_database_query", query)

    assert lw.demote_legacy_shared_thread_edges(object()) == {
        "lineage_edges": 2,
        "knowledge_graph_edges": 3,
    }
    assert {lw.ANALYSIS_EDGE_TABLE, lw.ANALYSIS_KG_EDGE_TABLE} == {
        table_name
        for statement, _params in calls
        for table_name in (lw.ANALYSIS_EDGE_TABLE, lw.ANALYSIS_KG_EDGE_TABLE)
        if table_name in statement
    }
    assert all(
        params == (
            lw.SHARED_THREAD_RELATION,
            lw.EVIDENCE_INFERRED,
            lw.SHARED_THREAD_REASON,
            lw.LEGACY_THREAD_TRANSITION_RELATION,
            lw.EVIDENCE_OBSERVED,
            lw.LEGACY_THREAD_TRANSITION_REASON,
        )
        for _statement, params in calls
    )


def test_inference_verification_run_persists_normalized_candidates_and_evidence(monkeypatch) -> None:
    """Store a bounded verifier run in direct-PostgreSQL 3NF relations."""
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    rows = [
        {
            "candidate": {
                "candidate_id": "candidate-1",
                "source_node": "doc:DOC-1",
                "target_node": "doc:DOC-2",
                "relation_name": "topic_affinity",
                "evidence_status": lw.EVIDENCE_INFERRED,
            },
            "verification": {
                "decision": "insufficient",
                "confidence": 0.25,
                "rationale": "Need more evidence",
                "model": "fixture-model",
            },
            "evidence": [
                {
                    "evidence_kind": "internal",
                    "evidence_id": "ROW-1",
                    "title": "Observed row",
                    "excerpt": "bounded",
                    "source_rank": 2,
                },
                {
                    "evidence_kind": "external",
                    "evidence_id": "external-1",
                    "source_uri": "https://example.test/evidence",
                    "title": "External result",
                    "excerpt": "external bounded",
                },
            ],
        }
    ]

    persisted = lw.persist_inference_verification_run(
        object(),
        document_no="DOC-1",
        requested_by="actor-1",
        external_search_mode="searxng",
        verification_rows=rows,
    )

    assert persisted["run_id"].startswith("inference:")
    assert persisted["candidate_count"] == 1
    assert persisted["evidence_count"] == 2
    assert "pg_advisory_xact_lock" in statements[0][0]
    sql = "\n".join(statement for statement, _ in statements)
    assert "CREATE TABLE IF NOT EXISTS analysis_inference_runs" in sql
    assert "CREATE TABLE IF NOT EXISTS analysis_inference_candidates" in sql
    assert "CREATE TABLE IF NOT EXISTS analysis_inference_evidence" in sql
    assert "FOREIGN KEY (run_id, candidate_id)" in sql
    inserts = [(statement, params) for statement, params in statements if "INSERT INTO" in statement]
    assert len(inserts) == 4
    assert inserts[0][1][1:] == ("DOC-1", "actor-1", "searxng", "fixture-model", 1)
    assert inserts[1][1][4:6] == (None, None)
    assert inserts[1][1][8:12] == ("insufficient", 0.25, "Need more evidence", "fixture-model")
    assert inserts[2][1][3:] == ("internal", "ROW-1", None, "Observed row", "bounded", 2)
    assert inserts[3][1][3:] == (
        "external",
        "external-1",
        "https://example.test/evidence",
        "External result",
        "external bounded",
        2,
    )


def test_database_overrides_rehydrate_operational_product_fields(monkeypatch) -> None:
    """Apply persisted edits and LLM work products without a file-store fallback."""
    payload = {
        "nodes": [
            {
                "type": "document",
                "document_no": "DOC-1",
                "visibility": lw.VISIBILITY_PRIVATE,
                "issue_tickets": [{"ticket_id": "derived"}],
            },
            {
                "type": "document",
                "document_no": "DOC-2",
                "visibility": lw.VISIBILITY_PUBLIC,
                "issue_tickets": [{"ticket_id": "preserved"}],
            },
        ],
    }

    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if lw.ANALYSIS_OVERRIDE_TABLE in sql:
            return [
                {
                    "document_no": "DOC-1",
                    "visibility_code": lw.VISIBILITY_PUBLIC,
                    "keyman_our_side": json.dumps([{"person_name": "A", "org_name": "Org A"}]),
                    "keyman_counterpart_side": [{"person_name": "B", "org_name": "Org B"}],
                },
                {"document_no": "DOC-hidden", "visibility_code": lw.VISIBILITY_PUBLIC},
            ]
        if lw.ANALYSIS_TICKET_TABLE in sql:
            return [{"ticket_id": "ticket-1", "document_no": "DOC-1", "title": "Follow up"}]
        if lw.ANALYSIS_TODO_TABLE in sql:
            return [{"todo_id": "todo-1", "document_no": "DOC-1", "content_source": "llm"}]
        if lw.ANALYSIS_CALENDAR_TABLE in sql:
            return [{"calendar_id": "calendar-1", "document_no": "DOC-1", "content_source": "llm"}]
        if lw.ANALYSIS_APPOINTMENT_TABLE in sql:
            return [{"appointment_id": "appointment-1", "document_no": "DOC-1", "content_source": "llm"}]
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_query", query)
    monkeypatch.setattr(lw, "load_customer_master", lambda _connection: {"source": "fixture"})
    monkeypatch.setattr(lw, "load_period_reports", lambda _connection: [{"report_id": "report-1"}])
    result = lw.load_database_overrides(object(), payload)

    first, second = result["nodes"]
    assert first["visibility"] == lw.VISIBILITY_PUBLIC
    assert first["keymen"] == ["A", "B"]
    assert first["keyman_source"] == "user_override"
    assert first["keyman_status"] == "managed"
    assert first["issue_tickets"] == [{"ticket_id": "ticket-1", "document_no": "DOC-1", "title": "Follow up"}]
    assert first["todo_items"][0]["source"] == "llm"
    assert first["calendar_items"][0]["source"] == "llm"
    assert first["appointments"][0]["source"] == "llm"
    assert second["issue_tickets"] == [{"ticket_id": "preserved"}]
    assert result["customer_master"] == {"source": "fixture"}
    assert result["period_reports"] == [{"report_id": "report-1"}]
    assert result["factor_definitions"]


def test_database_overrides_tolerates_unavailable_optional_operational_tables(monkeypatch) -> None:
    """Keep the persisted document scope readable when optional tables are not yet migrated."""
    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if lw.ANALYSIS_OVERRIDE_TABLE in sql or lw.ANALYSIS_TICKET_TABLE in sql:
            return []
        raise RuntimeError("optional tables unavailable")

    monkeypatch.setattr(lw, "_database_query", query)
    payload = {
        "nodes": [{"type": "document", "document_no": "DOC-1"}],
        "customer_master": {"source": "existing"},
        "period_reports": [{"report_id": "existing"}],
    }
    result = lw.load_database_overrides(object(), payload)
    assert result["nodes"][0]["issue_tickets"] == []


def test_direct_postgresql_persistence_rejects_unknown_document_and_skips_empty_surfaces(monkeypatch) -> None:
    """Fail closed before writing an unscoped content profile and avoid empty bulk writes."""
    with pytest.raises(ValueError, match="requires a document number"):
        lw.persist_document_content_structure(_RecordingConnection(), "", {"blocks": [], "assets": []})

    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)
    connection = _RecordingConnection()
    assert lw.persist_affiliate_tree(connection, {"edges": []}) == 0
    assert lw.persist_period_reports(connection, []) == 0
    assert lw.persist_affiliate_tree(connection, {"edges": []}, ensure_schema=False) == 0
    assert lw.persist_period_reports(connection, [], ensure_schema=False) == 0
    assert any(lw.ANALYSIS_AFFILIATE_TABLE in sql for sql, _ in statements)
    assert connection.recording_cursor.executemany_calls == []


def test_direct_postgresql_operational_readers_fail_closed_when_tables_or_queries_are_unavailable(monkeypatch) -> None:
    """Keep optional report, customer, and affiliate surfaces empty rather than partly trusted."""
    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: False)
    assert lw.load_period_reports(object()) == []
    assert lw.load_workspace_surface(object())["metadata"]["row_count"] == 0
    assert lw.load_affiliate_tree(object()) == {"nodes": [], "edges": [], "parent_of": {}}

    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: True)
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("direct database unavailable")),
    )
    assert lw.load_period_reports(object()) == []
    assert lw.load_affiliate_tree(object()) == {"nodes": [], "edges": [], "parent_of": {}}

    def table_exists(_connection, table: str) -> bool:
        return table != lw.ANALYSIS_CUSTOMER_DOCUMENT_TABLE

    def customer_query(_connection, sql: str, _params=()):  # noqa: ANN001
        if lw.ANALYSIS_CUSTOMER_TABLE in sql:
            return [{"account_name": "Northwind", "parent_name": "", "tier_name": "group", "entity_role": "고객"}]
        if lw.ANALYSIS_CUSTOMER_AFFILIATE_TABLE in sql:
            return []
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_table_exists", table_exists)
    monkeypatch.setattr(lw, "_database_query", customer_query)
    customer_master = lw.load_customer_master(object())
    assert customer_master["accounts"][0]["document_nos"] == []


def test_direct_postgresql_operational_readers_normalize_persisted_json_and_linked_scores(monkeypatch) -> None:
    """Restore valid report metadata while dropping malformed JSON-like rows safely."""
    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: True)

    def report_query(_connection, sql: str, _params=()):  # noqa: ANN001
        if lw.ANALYSIS_PERIOD_REPORT_TABLE in sql:
            return [
                {
                    "report_id": "report-json",
                    "period_kind": "weekly",
                    "slice_kind": "pu",
                    "slice_key": "PU-A",
                    "judge_verdict": "pass",
                    "judge_source": "live",
                    "report_payload": json.dumps({"title": "Weekly report"}),
                },
                {
                    "report_id": "report-malformed",
                    "period_kind": "monthly",
                    "slice_kind": "team",
                    "slice_key": "Sales",
                    "judge_verdict": "fail",
                    "judge_source": "live",
                    "report_payload": ["malformed"],
                },
            ]
        if lw.ANALYSIS_LINKED_SCORE_TABLE in sql:
            return [{"report_id": "report-json", "factor_id": "gm-pos-delivery", "theta": 0.3}]
        raise AssertionError(sql)

    monkeypatch.setattr(lw, "_database_query", report_query)
    reports = lw.load_period_reports(object())
    assert reports[0]["title"] == "Weekly report"
    assert reports[0]["linked_scores"][0]["factor_family"] == "general_management"
    assert reports[1]["report_id"] == "report-malformed"

    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda *_args, **_kwargs: [{"row_count": 2, "document_count": 1, "thread_count": 1, "metadata_payload": json.dumps({"source": "persisted"})}],
    )
    monkeypatch.setattr(lw, "load_customer_master", lambda _connection, actor=None: {"edges": []})
    monkeypatch.setattr(lw, "load_affiliate_tree", lambda _connection: {"nodes": [], "edges": [], "parent_of": {}})
    monkeypatch.setattr(lw, "load_period_reports", lambda _connection: [{"report_id": "report-json"}])
    surface = lw.load_workspace_surface(object())
    assert surface["metadata"] == {"source": "persisted", "row_count": 2, "document_count": 1, "thread_count": 1}

    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda *_args, **_kwargs: [{"row_count": 0, "document_count": 0, "thread_count": 0, "metadata_payload": ["malformed"]}],
    )
    assert lw.load_workspace_surface(object())["metadata"] == {"row_count": 0, "document_count": 0, "thread_count": 0}


def test_knowledge_evidence_merge_and_valkey_transport_cover_recovery_paths(monkeypatch) -> None:
    """Preserve evidence on existing and new KG edges and validate secure Valkey setup."""
    graph = {
        "nodes": [
            {"id": "kg:document:one", "type": "document", "document_no": "DOC-1"},
            {"id": "kg:document:two", "type": "document", "document_no": "DOC-2"},
        ],
        "edges": [{"source": "kg:document:one", "target": "kg:document:two", "relation": "shared_thread"}],
    }
    merged, changed = lw.merge_lineage_evidence_into_knowledge_graph(
        graph,
        [
            {
                "source": "doc:DOC-1",
                "target": "doc:DOC-2",
                "relation": "shared_thread",
                "evidence_status": lw.EVIDENCE_OBSERVED,
                "acthguid": "THREAD-1",
                "reason": "observed together",
            },
            {
                "source": "doc:DOC-2",
                "target": "doc:DOC-1",
                "relation": "precedes",
                "evidence_status": lw.EVIDENCE_OBSERVED,
                "acthguid": "THREAD-1",
                "reason": "ordered evidence",
            },
        ],
    )
    assert changed == 4
    assert merged["edges"][0]["evidence_id"] == "THREAD-1"
    assert merged["edges"][0]["reason"] == "observed together"
    assert merged["edges"][1]["evidence_id"] == "THREAD-1"
    assert lw.load_knowledge_semantic_context(object(), []) == {"node_terms": [], "edge_assertions": []}

    class _ClosedSocket:
        def recv(self, _size: int) -> bytes:
            return b""

    class _InvalidLineSocket:
        def __init__(self) -> None:
            self.values = iter((b"+", b"o", b"k", b"\r", b"x"))

        def recv(self, _size: int) -> bytes:
            return next(self.values, b"")

    with pytest.raises(RuntimeError, match="connection_closed"):
        lw._valkey_read_exact(_ClosedSocket(), 1)
    with pytest.raises(RuntimeError, match="invalid_response"):
        lw._valkey_read_reply(_InvalidLineSocket())

    raw_connection = object()
    secure_connection = object()
    commands: list[tuple[object, ...]] = []

    class _TlsContext:
        def wrap_socket(self, connection, server_hostname: str):  # noqa: ANN001
            assert connection is raw_connection
            assert server_hostname == "valkey.example"
            return secure_connection

    monkeypatch.setattr(lw.socket, "create_connection", lambda *_args, **_kwargs: raw_connection)
    monkeypatch.setattr(lw.ssl, "create_default_context", lambda: _TlsContext())
    monkeypatch.setattr(lw, "_valkey_command", lambda connection, *parts: commands.append((connection, *parts)) or "OK")
    assert lw._open_valkey_connection("rediss://:secret@valkey.example:6380/2") is secure_connection
    assert commands == [(secure_connection, "AUTH", "secret"), (secure_connection, "SELECT", "2")]
    commands.clear()
    assert lw._open_valkey_connection("redis://valkey.example") is raw_connection
    assert commands == []
