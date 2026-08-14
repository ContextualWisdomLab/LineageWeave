"""Contracts for evidence-bound DOM semantic embeddings."""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from types import SimpleNamespace

import pytest

import lineageweave as lw
import lineageweave_embeddings as lwe
import lineageweave_server as server


class _Response:
    """Supply the narrow context-managed HTTP response protocol used by discovery."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _Cursor:
    """Record vector inserts without requiring a database writer in unit contracts."""

    def __init__(self, calls: list[tuple[str, object]]) -> None:
        self.calls = calls

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def executemany(self, sql: str, params: object) -> None:
        self.calls.append((sql, list(params)))


class _Connection:
    """Expose only the cursor interface needed for embedding persistence."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def cursor(self) -> _Cursor:
        return _Cursor(self.calls)


class _ContextConnection:
    """Stand in for a direct psycopg context manager used by application methods."""

    def __enter__(self) -> _Connection:
        return _Connection()

    def __exit__(self, *_args: object) -> bool:
        return False


def test_chunking_uses_dom_text_and_keeps_source_location() -> None:
    """Never feed markup or inline bytes to the embedding transport."""
    structure = {
        "blocks": [
            None,
            {"block_index": "invalid", "text_content": "ignored", "source_evidence_id": ""},
            {
                "block_index": 4,
                "source_evidence_id": "evidence-1",
                "source_position": "invalid",
                "text_content": "Alpha. Beta gamma delta",
            },
        ]
    }
    chunks = lwe.build_embedding_chunks("DOC-1", structure, maximum_chars=10, maximum_chunks=8)

    assert [item["chunk_text"] for item in chunks] == ["Alpha.", "Beta gamma", "delta"]
    assert {item["block_index"] for item in chunks} == {4}
    assert {item["source_evidence_id"] for item in chunks} == {"evidence-1"}
    assert {item["source_position"] for item in chunks} == {0}
    assert all("data:image" not in item["chunk_text"] for item in chunks)
    assert lwe._split_text("", 10) == []
    assert lwe._split_text("abcdefghij", 4) == ["abcd", "efgh", "ij"]
    assert lwe._split_text("abcde。", 5) == ["abcde", "。"]
    assert len(lwe.build_embedding_chunks("DOC-1", structure, maximum_chars=10, maximum_chunks=1)) == 1
    with pytest.raises(ValueError, match="document number"):
        lwe.build_embedding_chunks("", structure)
    with pytest.raises(ValueError, match="chunk count"):
        lwe.build_embedding_chunks("DOC-1", structure, maximum_chunks=0)
    with pytest.raises(ValueError, match="chunk size"):
        lwe._split_text("text", 0)


def test_embedding_response_validates_order_vectors_and_dimensions() -> None:
    """Map provider indexes back to caller order and reject unsafe provider bodies."""
    parsed = lwe._embedding_response(
        {"model": "embedding-test", "data": [{"index": 1, "embedding": [0, 1]}, {"index": 0, "embedding": [1, 0]}]},
        2,
        "fallback",
    )
    assert parsed["vectors"] == [[1.0, 0.0], [0.0, 1.0]]
    assert parsed["vector_dimensions"] == 2
    assert lwe._vector_values("[1, 2]") == [1.0, 2.0]
    for payload, expected in (
        ({"data": []}, "count"),
        ({"data": ["bad", {"index": 1, "embedding": [1]}]}, "item"),
        ({"data": [{"index": 0, "embedding": [1]}]}, "count"),
        ({"data": [{"index": "bad", "embedding": [1]}, {"index": 1, "embedding": [1]}]}, "index"),
        ({"data": [{"index": 2, "embedding": [1]}, {"index": 1, "embedding": [1]}]}, "index"),
        ({"data": [{"index": 0, "embedding": [1]}, {"index": 0, "embedding": [1]}]}, "index"),
        ({"data": [{"index": 0, "embedding": [1]}, {"index": 1, "embedding": [1, 2]}]}, "dimensions"),
    ):
        with pytest.raises(RuntimeError, match=expected):
            lwe._embedding_response(payload, 2, "fallback")
    for value, expected in (([], "missing"), (["bad"], "non-numeric"), ([float("nan")], "non-finite")):
        with pytest.raises(ValueError, match=expected):
            lwe._vector_values(value)


def test_live_transport_discovers_models_and_bounds_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the verified gateway only after resolving one embedding-capable model."""
    monkeypatch.setattr(lwe.lw, "live_http_config", lambda: ("https://gateway.example", "token", "chat"))
    monkeypatch.delenv("LINEAGEWEAVE_EMBEDDING_MODEL", raising=False)
    monkeypatch.setattr(lwe, "_discover_embedding_model", lambda *_args: "embedding-model")
    monkeypatch.setattr(lwe.lw, "resolve_llm_timeout", lambda *_args, **_kwargs: 7)
    captured: dict[str, object] = {}

    def fake_post(request, *, timeout, context):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        assert context.verify_mode
        return {"model": "embedding-model", "data": [{"index": 0, "embedding": [1, 0]}]}

    monkeypatch.setattr(lwe.lw, "_post_json_from_request", fake_post)
    transport = lwe.make_live_embedding_transport()
    assert transport(["Alpha"]) ["vectors"] == [[1.0, 0.0]]
    assert captured == {"payload": {"model": "embedding-model", "input": ["Alpha"]}, "timeout": 7}
    with pytest.raises(ValueError, match="inputs"):
        lwe.post_live_embeddings([], base_url="https://gateway.example", token="token", model_name="model", timeout=1)
    with pytest.raises(ValueError, match="semantic chunk"):
        lwe.post_live_embeddings(["x" * (lwe.MAX_EMBEDDING_CHUNK_CHARS + 1)], base_url="https://gateway.example", token="token", model_name="model", timeout=1)
    monkeypatch.setattr(lwe.lw, "_post_json_from_request", lambda *_args, **_kwargs: [])
    with pytest.raises(RuntimeError, match="response_invalid"):
        lwe.post_live_embeddings(["Alpha"], base_url="https://gateway.example", token="token", model_name="model", timeout=1)
    monkeypatch.setenv("LINEAGEWEAVE_EMBEDDING_MODEL", "configured-model")
    monkeypatch.setattr(lwe, "_discover_embedding_model", lambda *_args: (_ for _ in ()).throw(AssertionError("should not discover")))
    monkeypatch.setattr(lwe.lw, "_post_json_from_request", fake_post)
    assert lwe.make_live_embedding_transport()(["Beta"])["model_name"] == "embedding-model"


def test_model_discovery_and_http_failures_are_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not guess a model or treat gateway transport failure as a vector."""
    monkeypatch.setattr(lwe.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response({"data": [{"id": "chat"}, {"id": "embed-b"}, {"id": "embed-a"}]}))
    assert lwe._discover_embedding_model("https://gateway.example", "token") == "embed-a"
    monkeypatch.setattr(lwe.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response({"data": []}))
    with pytest.raises(RuntimeError, match="model_unavailable"):
        lwe._discover_embedding_model("https://gateway.example", "token")
    monkeypatch.setattr(lwe.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")))
    with pytest.raises(RuntimeError, match="discovery_unavailable"):
        lwe._discover_embedding_model("https://gateway.example", "token")
    monkeypatch.setattr(lwe.lw, "_post_json_from_request", lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.HTTPError("https://gateway.example", 503, "down", None, None)))
    with pytest.raises(RuntimeError, match="http_503"):
        lwe.post_live_embeddings(["Alpha"], base_url="https://gateway.example", token="token", model_name="model", timeout=1)
    monkeypatch.setattr(lwe.lw, "_post_json_from_request", lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")))
    with pytest.raises(RuntimeError, match="unavailable"):
        lwe.post_live_embeddings(["Alpha"], base_url="https://gateway.example", token="token", model_name="model", timeout=1)


def test_derivation_persistence_loading_and_ranking_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Persist vectors in normalized tables and return only inferred relatedness metadata."""
    chunks = lwe.build_embedding_chunks(
        "DOC-1",
        {"blocks": [{"block_index": 0, "source_evidence_id": "ev-1", "source_position": 0, "text_content": "Alpha"}]},
    )
    derived = lwe.derive_document_embeddings(
        chunks,
        transport=lambda values: {"model_name": "model-a", "provider_kind": "fixture", "vector_dimensions": 2, "vectors": [[1, 0]]},
    )
    assert derived["rows"][0]["vector_values"] == [1.0, 0.0]
    assert derived["rows"][0]["model_name"] == "model-a"
    assert "chunk_text" not in derived["rows"][0]
    assert lwe.derive_document_embeddings([], transport=lambda _values: {})["rows"] == []
    with pytest.raises(RuntimeError, match="count"):
        lwe.derive_document_embeddings(chunks, transport=lambda _values: {"vectors": []})
    with pytest.raises(RuntimeError, match="dimensions"):
        lwe.derive_document_embeddings(chunks, transport=lambda _values: {"vectors": [[1]], "vector_dimensions": 2})
    with pytest.raises(RuntimeError, match="dimensions"):
        lwe.derive_document_embeddings(chunks, transport=lambda _values: {"vectors": [[1, 0]], "vector_dimensions": 0})
    with pytest.raises(RuntimeError, match="model_missing"):
        lwe.derive_document_embeddings(chunks, transport=lambda _values: {"vectors": [[1, 0]], "vector_dimensions": 2})

    connection = _Connection()
    statements: list[tuple[str, object]] = []
    monkeypatch.setattr(lwe.lw, "ensure_content_structure_tables", lambda _connection: None)
    monkeypatch.setattr(lwe.lw, "_database_exec", lambda _connection, sql, params=(): statements.append((sql, params)))
    assert lwe.persist_document_embeddings(connection, "DOC-1", derived) == 1
    assert any(lwe.ANALYSIS_EMBEDDING_MODEL_TABLE in sql for sql, _params in statements)
    assert any(lwe.ANALYSIS_CONTENT_EMBEDDING_TABLE in sql for sql, _params in connection.calls)
    assert lwe.persist_document_embeddings(connection, "DOC-1", {"rows": []}) == 0
    with pytest.raises(ValueError, match="metadata"):
        lwe.persist_document_embeddings(connection, "DOC-1", {"rows": [{}]})

    stored = [{"document_no": "DOC-2", "block_index": 1, "chunk_index": 0, "model_name": "model-a", "chunk_sha256": "x", "vector_values": [1, 0], "source_evidence_id": "ev-2", "source_position": 5}, {"document_no": "DOC-3", "block_index": 1, "chunk_index": 0, "model_name": "model-a", "chunk_sha256": "x", "vector_values": "not-json", "source_evidence_id": "ev-3", "source_position": 2}]
    monkeypatch.setattr(lwe.lw, "_database_table_exists", lambda *_args: True)
    monkeypatch.setattr(lwe.lw, "_database_query", lambda *_args, **_kwargs: stored)
    assert lwe.load_document_embeddings(connection, "DOC-2")[0]["vector_values"] == [1.0, 0.0]
    assert lwe.load_visible_embeddings(connection, ["DOC-2"], "model-a")[0]["document_no"] == "DOC-2"
    assert lwe.load_visible_embeddings(connection, [], "model-a") == []
    monkeypatch.setattr(lwe.lw, "_database_table_exists", lambda *_args: False)
    assert lwe.load_document_embeddings(connection, "DOC-2") == []

    related = lwe.rank_related_documents(
        "DOC-1",
        [{"model_name": "model-a", "vector_values": [1.0, 0.0]}],
        [
            {"document_no": "DOC-1", "model_name": "model-a", "vector_values": [1, 0]},
            {"document_no": "DOC-2", "model_name": "other", "vector_values": [1, 0]},
            {"document_no": "DOC-2", "model_name": "model-a", "vector_values": [0.8, 0.2], "source_evidence_id": "ev-2", "source_position": 3},
            {"document_no": "DOC-2", "model_name": "model-a", "vector_values": [0.5, 0.5], "source_evidence_id": "ev-2", "source_position": 3},
            {"document_no": "DOC-3", "model_name": "model-a", "vector_values": [0, 0]},
            {"document_no": "DOC-4", "model_name": "model-a", "vector_values": [0.1, 1]},
        ],
    )
    assert related == [{"document_no": "DOC-2", "similarity": pytest.approx(0.970143, abs=1e-6), "relation": "semantic_related", "evidence_status": lw.EVIDENCE_INFERRED, "source_evidence_id": "ev-2", "source_position": 3, "model_name": "model-a"}]
    calibrated = lwe.rank_related_documents(
        "",
        [{"model_name": "model-a", "vector_values": [1.0, 0.0]}],
        [
            {
                "document_no": "DOC-MULTILINGUAL",
                "model_name": "model-a",
                "vector_values": [0.44, 0.8979978],
                "source_evidence_id": "ev-multilingual",
                "source_position": 8,
            },
            {
                "document_no": "DOC-LOW",
                "model_name": "model-a",
                "vector_values": [0.25, 0.9682458],
                "source_evidence_id": "ev-low",
                "source_position": 9,
            },
        ],
    )
    assert [item["document_no"] for item in calibrated] == ["DOC-MULTILINGUAL"]
    assert calibrated[0]["similarity"] == pytest.approx(0.44, abs=1e-6)
    with pytest.raises(ValueError, match="dimensions"):
        lwe.cosine_similarity([1], [1, 2])
    with pytest.raises(ValueError, match="magnitude"):
        lwe.cosine_similarity([0], [0])


def test_authorized_embedding_candidates_stay_direct_and_actor_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Join only readable document embeddings and report the bounded in-process ceiling."""
    connection = _Connection()
    row = {
        "document_no": "DOC-2",
        "block_index": 0,
        "chunk_index": 0,
        "model_name": "model-a",
        "chunk_sha256": "a",
        "vector_values": [1, 0],
        "source_evidence_id": "ev-2",
        "source_position": 4,
        "title": "Fixture title",
        "visibility": "public",
    }
    monkeypatch.setattr(lwe.lw, "_database_table_exists", lambda *_args: True)
    captured: list[tuple[str, tuple[object, ...]]] = []

    def query(_connection, sql, params=()):
        captured.append((sql, params))
        return [row]

    monkeypatch.setattr(lwe.lw, "_database_query", query)
    reader = {"corp_code": "C1", "pu_code": "P1", "roles": ["reader"]}
    candidates, truncated = lwe.load_authorized_embedding_candidates(connection, reader, "model-a")
    assert candidates == [row]
    assert truncated is False
    assert "JOIN analysis_document_nodes AS document" in captured[-1][0]
    assert captured[-1][1] == (
        "model-a",
        "C1",
        lwe.lw.VISIBILITY_PUBLIC,
        "P1",
        lwe.MAX_SEMANTIC_CANDIDATE_ROWS + 1,
    )

    admin = {"corp_code": "C1", "pu_code": "P1", "roles": ["admin"]}
    assert lwe.load_authorized_embedding_candidates(connection, admin, "model-a")[1] is False
    assert captured[-1][1] == ("model-a", "C1", lwe.MAX_SEMANTIC_CANDIDATE_ROWS + 1)
    monkeypatch.setattr(lwe.lw, "_database_table_exists", lambda *_args: False)
    assert lwe.load_authorized_embedding_candidates(connection, reader, "model-a") == ([], False)
    monkeypatch.setattr(lwe.lw, "_database_table_exists", lambda *_args: True)
    assert lwe.load_authorized_embedding_candidates(connection, {"corp_code": ""}, "model-a") == ([], False)
    monkeypatch.setattr(lwe.lw, "_database_query", lambda *_args, **_kwargs: [row] * (lwe.MAX_SEMANTIC_CANDIDATE_ROWS + 1))
    candidates, truncated = lwe.load_authorized_embedding_candidates(connection, reader, "model-a")
    assert len(candidates) == lwe.MAX_SEMANTIC_CANDIDATE_ROWS
    assert truncated is True


def test_direct_postgres_embedding_round_trip_uses_only_temp_analysis_tables() -> None:
    """Exercise normalized vector persistence without touching the runtime schema."""
    document_no = "embedding-contract-document"
    structure = {
        "blocks": [
            {
                "block_index": 0,
                "source_evidence_id": "embedding-contract-evidence",
                "source_position": 0,
                "source_row_number": "1",
                "block_kind": "paragraph",
                "text_content": "Semantic contract text",
                "text_sha256": "a" * 64,
            }
        ],
        "assets": [],
    }
    chunks = lwe.build_embedding_chunks(document_no, structure)
    result = lwe.derive_document_embeddings(
        chunks,
        transport=lambda _values: {
            "model_name": "embedding-contract-model",
            "provider_kind": "fixture",
            "vector_dimensions": 2,
            "vectors": [[0.6, 0.8]],
        },
    )
    dsn = os.environ.get("LINEAGEWEAVE_TEST_DSN", "postgresql://localhost/postgres")
    with lw.psycopg.connect(dsn, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TEMP TABLE embedding_contract_anchor (id integer)")
            cursor.execute("SET LOCAL search_path TO pg_temp")
        assert lw.persist_document_content_structure(connection, document_no, structure)["content_block_rows"] == 1
        assert lwe.persist_document_embeddings(connection, document_no, result) == 1
        loaded = lwe.load_document_embeddings(connection, document_no)
        assert loaded == [
            {
                "document_no": document_no,
                "block_index": 0,
                "chunk_index": 0,
                "model_name": "embedding-contract-model",
                "chunk_sha256": chunks[0]["chunk_sha256"],
                "vector_values": [0.6, 0.8],
                "source_evidence_id": "embedding-contract-evidence",
                "source_position": 0,
            }
        ]
        assert lw.persist_document_content_structure(connection, document_no, structure)["content_block_rows"] == 1
        assert lwe.load_document_embeddings(connection, document_no) == loaded
        assert lwe.load_visible_embeddings(connection, [document_no], "embedding-contract-model") == loaded
        changed_structure = {
            "blocks": [{**structure["blocks"][0], "text_content": "Changed", "text_sha256": "changed"}],
            "assets": [],
        }
        assert lw.persist_document_content_structure(connection, document_no, changed_structure)["content_block_rows"] == 1
        assert lwe.load_document_embeddings(connection, document_no) == []
        assert lw.persist_document_content_structure(
            connection,
            document_no,
            {"blocks": [], "assets": []},
        ) == {
            "content_block_rows": 0,
            "content_format_hint_rows": 0,
            "content_asset_rows": 0,
        }


def test_application_and_http_routes_apply_authorization_and_hide_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expose only server-authorized semantic index metadata and relatedness records."""
    actor = {"account_id": "user-1", "corp_code": "C1", "pu_code": "P1", "roles": ["admin"]}
    document = {"document_no": "DOC-1", "corp_code": "C1", "owner_pu": "P1", "visibility": "public"}
    app = object.__new__(server.LineageApplication)
    app.dsn = "postgresql://fixture"
    app.document = lambda _actor, _document_no: {"document": document}
    app._materialize_document_content = lambda _document_no: {"blocks": [{"block_index": 0, "source_evidence_id": "ev-1", "source_position": 0, "text_content": "Alpha"}]}
    app._flush_event_outbox = lambda: None
    app.filtered_payload = lambda _actor: pytest.fail("semantic relatedness must not materialize the full graph")
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _ContextConnection())
    monkeypatch.setattr(lwe, "build_embedding_chunks", lambda *_args: [{"block_index": 0, "chunk_index": 0, "chunk_text": "Alpha", "chunk_sha256": "a"}])
    monkeypatch.setattr(lwe, "make_live_embedding_transport", lambda: object())
    monkeypatch.setattr(lwe, "derive_document_embeddings", lambda *_args, **_kwargs: {"model_name": "model-a", "provider_kind": "live_gateway", "vector_dimensions": 2, "rows": [{"block_index": 0, "chunk_index": 0, "chunk_sha256": "a", "vector_values": [1, 0]}]})
    monkeypatch.setattr(lwe, "persist_document_embeddings", lambda *_args: 1)
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda *_args, **_kwargs: None)
    assert app.index_document_embeddings(actor, "DOC-1") == {"document_no": "DOC-1", "chunk_count": 1, "model_name": "model-a", "vector_dimensions": 2, "source": "live_gateway"}
    monkeypatch.setattr(lwe, "load_document_embeddings", lambda *_args: [{"model_name": "model-a", "vector_values": [1, 0]}])
    monkeypatch.setattr(lwe, "load_authorized_embedding_candidates", lambda *_args: ([{"document_no": "DOC-2", "model_name": "model-a", "vector_values": [1, 0], "source_evidence_id": "ev-2", "source_position": 4, "title": "Beta", "visibility": "private"}], False))
    related = app.semantic_related_documents(actor, "DOC-1")
    assert related["items"] == [{"document_no": "DOC-2", "similarity": 1.0, "relation": "semantic_related", "evidence_status": "inferred", "source_evidence_id": "ev-2", "source_position": 4, "model_name": "model-a", "title": "Beta", "visibility": "private"}]
    monkeypatch.setattr(lwe, "load_document_embeddings", lambda *_args: [])
    assert app.semantic_related_documents(actor, "DOC-1")["status"] == "index_required"
    monkeypatch.setattr(lwe, "build_embedding_chunks", lambda *_args, **_kwargs: [{"chunk_text": "Alpha"}])
    monkeypatch.setattr(lwe, "make_live_embedding_transport", lambda: object())
    monkeypatch.setattr(
        lwe,
        "derive_document_embeddings",
        lambda *_args, **_kwargs: {"model_name": "model-a", "rows": [{"model_name": "model-a", "vector_values": [1, 0]}]},
    )
    monkeypatch.setattr(
        lwe,
        "load_authorized_embedding_candidates",
        lambda *_args: ([{"document_no": "DOC-2", "model_name": "model-a", "vector_values": [1, 0], "source_evidence_id": "ev-2", "source_position": 4, "title": "Beta", "visibility": "private"}], False),
    )
    monkeypatch.setattr(app, "filtered_payload", lambda *_args: (_ for _ in ()).throw(AssertionError("semantic search must use direct PostgreSQL candidates")))
    assert app.semantic_search_documents(actor, "alpha") == {
        "query": "alpha",
        "status": "ready",
        "items": [{"document_no": "DOC-2", "similarity": 1.0, "relation": "semantic_related", "evidence_status": "inferred", "source_evidence_id": "ev-2", "source_position": 4, "model_name": "model-a", "title": "Beta", "visibility": "private"}],
    }
    monkeypatch.setattr(lwe, "rank_related_documents", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        lw,
        "load_visible_document_index",
        lambda *_args, **_kwargs: {
            "items": [{"document_no": "DOC-2", "title": "Beta", "entity_role": "market", "visibility": "private"}],
            "total": 1,
        },
    )
    assert app.semantic_search_documents(actor, "alpha") == {
        "query": "alpha",
        "status": "keyword_fallback",
        "items": [{"document_no": "DOC-2", "title": "Beta", "entity_role": "market", "visibility": "private"}],
    }
    monkeypatch.setattr(lw, "load_visible_document_index", lambda *_args, **_kwargs: {"items": [], "total": 0})
    assert app.semantic_search_documents(actor, "alpha") == {
        "query": "alpha",
        "status": "ready",
        "items": [],
    }
    monkeypatch.setattr(lwe, "load_authorized_embedding_candidates", lambda *_args: ([], False))
    assert app.semantic_search_documents(actor, "alpha") == {"query": "alpha", "status": "index_required", "items": []}
    with pytest.raises(ValueError, match="at least two"):
        app.semantic_search_documents(actor, "x")
    with pytest.raises(ValueError, match="too long"):
        app.semantic_search_documents(actor, "x" * 201)

    class _RouteApplication:
        def actor_for_request(self, _handler):
            return actor

        def semantic_related_documents(self, _actor, document_no, limit):
            return {"document_no": document_no, "limit": limit, "items": []}

        def index_document_embeddings(self, _actor, document_no):
            return {"document_no": document_no, "chunk_count": 1}

        def semantic_search_documents(self, _actor, query, limit):
            return {"query": query, "limit": limit, "status": "ready", "items": []}

    monkeypatch.setattr(server.LineageHandler, "application", _RouteApplication(), raising=False)
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.LineageHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        with urllib.request.urlopen(origin + "/api/documents/DOC-1/semantic-related?limit=3", timeout=5) as response:
            assert json.loads(response.read()) == {"document_no": "DOC-1", "limit": 3, "items": []}
        with urllib.request.urlopen(origin + "/api/documents/semantic-search?q=alpha&limit=3", timeout=5) as response:
            assert json.loads(response.read()) == {"query": "alpha", "limit": 3, "status": "ready", "items": []}
        request = urllib.request.Request(origin + "/api/documents/DOC-1/semantic-index", data=b"{}", method="POST", headers={"content-type": "application/json"})
        with urllib.request.urlopen(request, timeout=5) as response:
            assert json.loads(response.read()) == {"document_no": "DOC-1", "chunk_count": 1}
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_embedding_index_rejects_foreign_and_empty_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enforce document authorization before the gateway and reject empty semantic input."""
    app = object.__new__(server.LineageApplication)
    app.dsn = "postgresql://fixture"
    document = {"document_no": "DOC-1", "corp_code": "C1", "owner_pu": "P1", "visibility": "private"}
    app.document = lambda _actor, _document_no: {"document": document}
    with pytest.raises(PermissionError, match="corp"):
        app.index_document_embeddings(
            {"account_id": "user-2", "corp_code": "C2", "pu_code": "P2", "roles": ["reader"]},
            "DOC-1",
        )

    actor = {"account_id": "user-1", "corp_code": "C1", "pu_code": "P1", "roles": ["admin"]}
    app._materialize_document_content = lambda _document_no: {"blocks": [], "assets": []}
    with pytest.raises(ValueError, match="no embeddable"):
        app.index_document_embeddings(actor, "DOC-1")
