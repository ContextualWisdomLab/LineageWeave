"""Exercise the shipped HTTP adapter through real loopback requests."""

from __future__ import annotations

import json
import http.client
import http.server as stdlib_http_server
import io
import runpy
import threading
import urllib.error
import urllib.request
from http import HTTPStatus

import pytest

import lineageweave as lw
import lineageweave_server as server


ACTOR = {
    "account_id": "fixture-account",
    "corp_code": "CORP_A",
    "pu_code": "PU_A",
    "roles": ["admin"],
}


class _HealthyConnection:
    """Provide the minimal context-manager boundary used by the health route."""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Application:
    """Small application double that preserves every public HTTP method shape."""

    dsn = "postgresql://fixture"

    def __init__(self) -> None:
        self.logged_out: list[str] = []

    def actor_for_request(self, _handler):
        """Supply one already-verified actor for contract-route coverage."""
        return ACTOR

    def event_queue_health(self):
        """Return the queue health shape without an external broker."""
        return {"stream": "lineageweave_events", "ready": True, "pending_outbox": 0}

    def keyverse_admin_accounts(self, _actor, *, query, limit):
        """Return one sanitized account-management payload for the admin route."""
        assert (query, limit) == ("fixture", 3)
        return {
            "corp_code": "CORP_A",
            "client_id": "lineageweave-web",
            "available_roles": [{"id": "role-admin", "name": "admin", "description": ""}],
            "accounts": [{"account_id": "account-1", "org": "CORP_A", "workspace": "PU_A", "roles": ["admin"]}],
        }

    def lineage_review_edges(self, _actor, *, query, limit):
        """Return one inferred edge for the administrator review route."""
        assert (query, limit) == ("fixture", 5)
        return {"items": [{"source_document": "DOC-1", "target_document": "DOC-2", "override_status": "pending"}], "total": 1}

    def customer_surface(self, _actor, *, query, limit):
        """Return one evidence-linked customer tree for the customer route."""
        assert (query, limit) == ("fixture", 4)
        return {
            "source": "llm",
            "accounts": [{"account_name": "Fixture customer", "document_nos": ["DOC-1"]}],
            "nodes": ["Fixture customer"],
            "edges": [],
            "parent_of": {},
        }

    def enrichment_status(self, _actor):
        """Return bounded pending LLM work for the administrator status route."""
        return {"pending": {"keyman": 2, "product": 3, "appointments": 4}, "active_runs": [], "last_run": None}

    def run_enrichment(self, _actor, body):
        """Return one queued bounded enrichment run for the administrator route."""
        return {"status": "queued", "run_id": "enrichment-1", "task": body["task"], "requested": body["limit"]}

    def lineage_review_edges(self, _actor, *, query, limit):
        """Return one safe inferred-edge review candidate."""
        assert (query, limit) == ("fixture", 3)
        return {"items": [{"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation": "similar"}], "total": 1, "limit": 3}

    def update_lineage_edge_override(self, _actor, body):
        """Return the reviewed decision without exposing an internal graph snapshot."""
        assert body["override_status"] == "suppressed"
        return {"source_node": body["source_node"], "target_node": body["target_node"], "relation": body["relation"], "override_status": "suppressed"}

    def update_keyverse_account(self, _actor, account_id, body):
        """Return one persisted account-claims update for the admin route."""
        assert account_id == "account-1"
        return {"account_id": account_id, "org": body["org"], "workspace": body["workspace"], "roles": body["roles"]}

    def update_lineage_edge_override(self, _actor, body):
        """Return one normalized administrator edge decision."""
        return {"source_node": body["source_node"], "target_node": body["target_node"], "relation": body["relation"], "override_status": body["override_status"]}

    def begin_keyverse_login(self, _request_headers=None, *, email_address):
        """Return an externally owned authorization redirect and state token."""
        assert email_address == "member@example.com"
        return "https://identity.example/authorize", "state-token"

    def complete_keyverse_login(self, code, state, cookie_state, _request_headers=None):
        """Validate callback arguments enough to prove handler argument order."""
        assert (code, state, cookie_state) == ("code", "state", "state")
        return "session-token", ACTOR, 60

    def logout(self, token):
        """Record deletion of the opaque local-session token."""
        self.logged_out.append(token)

    def filtered_payload(self, _actor):
        """Return a small visible graph used by analytics and thread routes."""
        return {
            "metadata": {"authorization_boundary": "filtered_for_verified_actor"},
            "analytics": {"total_documents": 5},
            "affiliate_tree": {"nodes": ["CORP_A"], "edges": []},
            "nodes": [
                {
                    "id": "doc:DOC-1",
                    "type": "document",
                    "document_no": "DOC-1",
                    "acthguid": "THREAD-1",
                    "title_sample": "Fixture document",
                    "row_count": 1,
                },
                {
                    "id": "doc:DOC-2",
                    "type": "document",
                    "document_no": "DOC-2",
                    "acthguid": "THREAD-1",
                    "title_sample": "Follow-up fixture",
                    "row_count": 2,
                },
                {
                    "id": "doc:DOC-3",
                    "type": "document",
                    "document_no": "DOC-3",
                    "acthguid": "THREAD-2",
                    "title_sample": "Second fixture thread",
                    "row_count": 1,
                },
                {
                    "id": "doc:DOC-4",
                    "type": "document",
                    "document_no": "DOC-4",
                    "acthguid": "THREAD-2",
                    "title_sample": "Second fixture follow-up",
                    "row_count": 1,
                },
                {
                    "id": "doc:DOC-SINGLE",
                    "type": "document",
                    "document_no": "DOC-SINGLE",
                    "acthguid": "THREAD-SINGLE",
                    "title_sample": "Standalone fixture document",
                    "row_count": 1,
                },
                {"id": "row:ROW-1", "type": "row", "document_no": "DOC-1"},
            ],
            "edges": [{"source": "doc:DOC-1", "target": "row:ROW-1", "relation": "observed"}],
        }

    def image_search(self, _actor, query, limit):
        """Echo bounded search arguments for route verification."""
        return {"query": query, "limit": limit, "items": []}

    def document_index(self, _actor, limit, offset, search):
        """Return one paged document index item."""
        return {
            "items": [{"document_no": "DOC-1"}],
            "total": 1,
            "limit": limit,
            "offset": offset,
            "search": search,
        }

    def document(self, _actor, document_no):
        """Return a document detail with an empty relationship set."""
        if document_no != "DOC-1":
            raise KeyError(document_no)
        return {"document": {"document_no": document_no}, "rows": [], "edges": [], "knowledge_graph": {}}

    def content_manifest(self, _actor, document_no):
        """Return an empty authorized content manifest."""
        return {"document_no": document_no, "assets": [], "asset_count": 0, "inspections": []}

    def source_evidence(self, _actor, document_no, guid):
        """Return bounded source-evidence metadata."""
        return {"document_no": document_no, "evidence_id": guid, "content_preview": "fixture"}

    def knowledge(self, _actor, document_no, query):
        """Return the requested graph scope without reading a database."""
        return {"document_no": document_no, "query": query, "nodes": [], "edges": []}

    def asset_bytes(self, _actor, document_no, asset_index):
        """Return one authorized binary asset response."""
        assert (document_no, asset_index) == ("DOC-1", 0)
        return "image/png", b"fixture-image"

    def set_visibility(self, _actor, document_no, visibility):
        """Return the persisted visibility representation."""
        return {"document_no": document_no, "visibility": visibility}

    def set_keymen(self, _actor, document_no, body):
        """Return the normalized Keyman mutation shape."""
        return {"document_no": document_no, "our_side": body.get("our_side", []), "counterpart_side": body.get("counterpart_side", [])}

    def derive_keymen(self, _actor, document_no):
        """Return a completed Keyman derivation response."""
        return {"document": {"document_no": document_no, "keyman_status": "derived"}}

    def inspect_content_asset(self, _actor, document_no, asset_index):
        """Return an inspection result for one authorized asset."""
        return {"asset": {"asset_index": asset_index}, "inspection": {"document_no": document_no}}

    def create_ticket(self, _actor, document_no, body):
        """Return a created issue ticket."""
        return {"document_no": document_no, "ticket_id": "ticket-1", "title": body.get("title")}

    def update_ticket(self, _actor, document_no, ticket_id, body):
        """Return an authorized persisted ticket-status transition."""
        assert (document_no, ticket_id, body["status"]) == ("DOC-1", "ticket-1", "resolved")
        return {"document_no": document_no, "ticket_id": ticket_id, "status": body["status"]}

    def workspace_surface(self, _actor):
        """Return the slim analytics surface used by the workspace recapture path."""
        return {
            "metadata": {"authorization_boundary": "filtered_for_verified_actor"},
            "analytics": {"total_documents": 1, "total_rows": 1},
            "affiliate_tree": {"nodes": ["CORP_A"], "edges": []},
            "period_reports": [],
            "customer_master": {"accounts": [], "edges": [], "source": "empty"},
        }

    def reports(self, _actor):
        """Return one weekly PU report slice for the route contract."""
        return {"reports": [{"period_kind": "weekly", "slice_kind": "pu", "slice_key": "PU_A"}], "source": "fixture"}

    def chat(self, _actor, document_no, message):
        """Return a bounded event-lineage chat response."""
        return {"document_no": document_no, "answer": message, "evidence_ids": []}

    def verify_lineage_inferences(self, _actor, document_no):
        """Return one persisted inference-verification run."""
        return {"document_no": document_no, "run_id": "run-1", "items": []}

    def resolve_organization_alias(self, _actor, document_no, alias_name):
        """Return one directional organization-alias verification."""
        return {"document_no": document_no, "alias_name": alias_name, "decision": "verified"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Expose product redirects as inspectable HTTP responses in the test."""

    def redirect_request(self, *_args, **_kwargs):
        """Disable automatic redirect handling."""
        return None


def _request(origin: str, path: str, *, method: str = "GET", body: dict | None = None, cookie: str = ""):
    """Send one real local HTTP request and return status, headers, and bytes."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(origin + path, data=data, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    if cookie:
        request.add_header("Cookie", cookie)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=5) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def test_http_handler_contract_routes(monkeypatch, tmp_path) -> None:
    """Cover health, authenticated reads, mutations, and OIDC redirects together."""
    application = _Application()
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _HealthyConnection())
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [{"healthy": 1}])
    monkeypatch.setattr(server.LineageHandler, "application", application, raising=False)
    monkeypatch.setattr(server, "FRONTEND_ROOT", tmp_path)
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.LineageHandler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    origin = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        status, _headers, payload = _request(origin, "/")
        assert (status, json.loads(payload)["error"]) == (
            HTTPStatus.SERVICE_UNAVAILABLE,
            "frontend_not_built_run_npm_build",
        )
        (tmp_path / "index.html").write_text("<main>fixture workspace</main>")
        (tmp_path / "app.js").write_text("export default 'fixture';")
        status, headers, payload = _request(origin, "/")
        assert (status, headers["Content-Type"], payload) == (
            HTTPStatus.OK,
            "text/html; charset=utf-8",
            b"<main>fixture workspace</main>",
        )
        status, headers, _payload = _request(origin, "/app.js")
        assert (status, headers["Content-Type"]) == (HTTPStatus.OK, "application/javascript; charset=utf-8")
        status, headers, payload = _request(origin, "/workspace/does-not-exist.css")
        assert (status, headers["Content-Type"], payload) == (
            HTTPStatus.OK,
            "text/html; charset=utf-8",
            b"<main>fixture workspace</main>",
        )
        for path, method, body in (
            ("/.well-known/openid-configuration", "GET", None),
            ("/authorize", "GET", None),
            ("/token", "POST", {}),
            ("/introspect", "POST", {}),
            ("/introspection", "POST", {}),
            ("/protocol/openid-connect/auth", "GET", None),
            ("/protocol/openid-connect/token", "POST", {}),
            ("/protocol/openid-connect/token/introspect", "POST", {}),
        ):
            status, _headers, payload = _request(origin, path, method=method, body=body)
            assert (status, json.loads(payload)) == (HTTPStatus.NOT_FOUND, {"error": "not_found"})
        connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
        connection.request("GET", "/../outside.txt")
        response = connection.getresponse()
        assert (response.status, json.loads(response.read())["error"]) == (HTTPStatus.NOT_FOUND, "not_found")
        connection.close()

        status, _headers, payload = _request(origin, "/api/health")
        assert (status, json.loads(payload)) == (HTTPStatus.OK, {"status": "ok", "database": "ok"})

        for path in (
            "/api/session",
            "/api/queue/health",
            "/api/analytics",
            "/api/reports",
            "/api/customers?q=fixture&limit=4",
            "/api/admin/keyverse/accounts?q=fixture&limit=3",
            "/api/admin/lineage/edges?q=fixture&limit=3",
            "/api/admin/enrichment/status",
            "/api/images/search?q=tag&limit=3",
            "/api/documents?limit=2&offset=1&q=fixture",
            "/api/documents/DOC-1",
            "/api/documents/DOC-1/content",
            "/api/documents/DOC-1/evidence/EVIDENCE-1",
            "/api/documents/DOC-1/knowledge?depth=2",
        ):
            status, _headers, _payload = _request(origin, path)
            assert status == HTTPStatus.OK

        status, _headers, payload = _request(origin, "/api/threads?limit=1")
        assert json.loads(payload) == {
            "items": [
                {
                    "thread_id": "THREAD-1",
                    "doc_count": 2,
                    "documents": [
                        {"document_no": "DOC-1", "title": "Fixture document", "row_count": 1},
                        {"document_no": "DOC-2", "title": "Follow-up fixture", "row_count": 2},
                    ],
                }
            ]
        }
        status, _headers, payload = _request(origin, "/api/threads?limit=3")
        assert [item["thread_id"] for item in json.loads(payload)["items"]] == ["THREAD-1", "THREAD-2"]
        status, _headers, payload = _request(origin, "/api/threads/THREAD-1")
        assert len(json.loads(payload)["documents"]) == 2
        status, _headers, payload = _request(origin, "/api/threads/MISSING")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.NOT_FOUND, "thread_not_found")
        status, _headers, payload = _request(origin, "/api/documents/MISSING")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.NOT_FOUND, "not_found")

        status, headers, _payload = _request(origin, "/api/login?email_address=member%40example.com")
        assert status == HTTPStatus.FOUND
        assert headers["Location"] == "https://identity.example/authorize"
        assert "lw_oidc_state=state-token" in headers["Set-Cookie"]

        status, headers, payload = _request(
            origin,
            "/api/login",
            method="POST",
            body={"email_address": "member@example.com"},
        )
        assert (status, json.loads(payload)) == (
            HTTPStatus.OK,
            {"authorization_url": "https://identity.example/authorize"},
        )
        assert "lw_oidc_state=state-token" in headers["Set-Cookie"]

        status, headers, _payload = _request(origin, "/api/oidc/callback?code=code&state=state", cookie="lw_oidc_state=state")
        assert status == HTTPStatus.FOUND
        assert headers["Location"] == "/"
        assert "lw_session=session-token" in headers.get_all("Set-Cookie")[0]
        monkeypatch.setattr(
            application,
            "complete_keyverse_login",
            lambda *_args: (_ for _ in ()).throw(RuntimeError("rejected")),
        )
        status, _headers, payload = _request(
            origin, "/api/oidc/callback?code=code&state=state", cookie="lw_oidc_state=state"
        )
        assert (status, json.loads(payload)["error"]) == (
            HTTPStatus.UNAUTHORIZED,
            "keyverse_oidc_callback_failed",
        )

        status, _headers, _payload = _request(origin, "/api/logout", cookie="lw_session=session-token")
        assert status == HTTPStatus.FOUND
        assert application.logged_out == ["session-token"]

        status, headers, payload = _request(origin, "/api/documents/DOC-1/assets/0")
        assert status == HTTPStatus.OK
        assert headers["Content-Type"] == "image/png"
        assert payload == b"fixture-image"

        writes = (
            ("/api/documents/DOC-1/visibility", {"visibility": "private"}, HTTPStatus.OK),
            ("/api/documents/DOC-1/keymen", {"our_side": [], "counterpart_side": []}, HTTPStatus.OK),
            ("/api/documents/DOC-1/keymen/derive", {}, HTTPStatus.OK),
            ("/api/documents/DOC-1/assets/0/inspect", {}, HTTPStatus.OK),
            ("/api/documents/DOC-1/tickets", {"title": "Fixture ticket"}, HTTPStatus.CREATED),
            ("/api/documents/DOC-1/tickets/ticket-1", {"status": "resolved"}, HTTPStatus.OK),
            ("/api/documents/DOC-1/chat", {"message": "What changed?"}, HTTPStatus.OK),
            ("/api/documents/DOC-1/lineage/verify", {}, HTTPStatus.OK),
            ("/api/documents/DOC-1/organizations/resolve", {"alias_name": "Alias"}, HTTPStatus.OK),
            ("/api/admin/keyverse/accounts/account-1/claims", {"org": "CORP_A", "workspace": "PU_A", "roles": ["admin"]}, HTTPStatus.OK),
            ("/api/admin/lineage/edges/override", {"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation": "topic_affinity", "override_status": "suppressed"}, HTTPStatus.OK),
            ("/api/admin/lineage/edges/override", {"source_node": "doc:DOC-1", "target_node": "doc:DOC-2", "relation": "similar", "override_status": "suppressed"}, HTTPStatus.OK),
            ("/api/admin/enrichment/run", {"task": "keyman", "limit": 2}, HTTPStatus.ACCEPTED),
        )
        for path, body, expected in writes:
            status, _headers, _payload = _request(origin, path, method="POST", body=body)
            assert status == expected

        for path in ("/api/register", "/api/register/complete"):
            for method in ("GET", "POST"):
                status, _headers, payload = _request(origin, path, method=method, body={} if method == "POST" else None)
                assert (status, json.loads(payload)["error"]) == (HTTPStatus.NOT_FOUND, "not_found")
        status, _headers, payload = _request(origin, "/api/session", method="POST", body={})
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.METHOD_NOT_ALLOWED, "keyverse_oidc_redirect_required")
        status, _headers, payload = _request(origin, "/api/unknown")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.NOT_FOUND, "not_found")
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_server_main_requires_runtime_settings_and_constructs_one_server(monkeypatch, capsys) -> None:
    """Fail before binding without direct-DB settings and bind the supplied listener once configured."""
    monkeypatch.delenv("LINEAGEWEAVE_DSN", raising=False)
    monkeypatch.delenv("LINEAGE_SOURCE_TABLE", raising=False)
    with pytest.raises(RuntimeError, match="LINEAGEWEAVE_DSN is required"):
        server.main()
    monkeypatch.setenv("LINEAGEWEAVE_DSN", "postgresql://fixture")
    with pytest.raises(RuntimeError, match="LINEAGE_SOURCE_TABLE is required"):
        server.main()

    started: dict[str, object] = {}

    class _Server:
        def __init__(self, address, handler) -> None:
            started["address"] = address
            started["handler"] = handler

        def serve_forever(self) -> None:
            started["served"] = True

    class _Thread:
        def __init__(self, *, target, args, daemon, name) -> None:  # noqa: ANN001
            started["refresh_target"] = target
            started["refresh_args"] = args
            started["refresh_daemon"] = daemon
            started["refresh_name"] = name

        def start(self) -> None:
            started["refresh_started"] = True

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    migrated: list[object] = []

    monkeypatch.setenv("LINEAGE_SOURCE_TABLE", "schema.table")
    monkeypatch.setenv("LINEAGEWEAVE_HOST", "127.0.0.1")
    monkeypatch.setenv("LINEAGEWEAVE_PORT", "8123")
    monkeypatch.setattr(server, "ThreadingHTTPServer", _Server)
    monkeypatch.setattr(server.threading, "Thread", _Thread)
    monkeypatch.setattr(server.psycopg, "connect", lambda _dsn: _Connection())
    monkeypatch.setattr(server.lw, "demote_legacy_shared_thread_edges", lambda connection: migrated.append(connection))
    server.main()
    assert started == {
        "address": ("127.0.0.1", 8123),
        "handler": server.LineageHandler,
        "refresh_target": server._run_report_refresh_in_background,
        "refresh_args": (server.LineageHandler.application,),
        "refresh_daemon": True,
        "refresh_name": "lineageweave-report-refresh",
        "refresh_started": True,
        "served": True,
    }
    assert len(migrated) == 1
    assert "LineageWeave listening" in capsys.readouterr().out


def test_background_report_refresh_handles_operator_outages() -> None:
    """Keep a failed maintenance refresh out of the HTTP server's exception stream."""
    events: list[str] = []

    class _Application:
        def refresh_persisted_reports(self) -> None:
            events.append("called")

    server._run_report_refresh_in_background(_Application())
    assert events == ["called"]

    class _FailingApplication:
        def refresh_persisted_reports(self) -> None:
            raise RuntimeError("operator gateway unavailable")

    server._run_report_refresh_in_background(_FailingApplication())


def test_server_module_entrypoint_and_text_response_preserve_http_contract(monkeypatch, capsys) -> None:
    """Exercise the executable entrypoint and UTF-8/cookie response branch without a live listener."""
    captured: list[tuple[str, object]] = []
    handler = object.__new__(server.LineageHandler)
    handler.wfile = io.BytesIO()
    handler.send_response = lambda status: captured.append(("status", status))
    handler.send_header = lambda name, value: captured.append((name, value))
    handler.end_headers = lambda: captured.append(("end", ""))
    handler._send(
        HTTPStatus.OK,
        "한글 응답",
        "text/plain; charset=utf-8",
        ["fixture=1; HttpOnly"],
    )
    assert handler.wfile.getvalue() == "한글 응답".encode("utf-8")
    assert ("Set-Cookie", "fixture=1; HttpOnly") in captured


    started: dict[str, object] = {}

    class _Server:
        def __init__(self, address, handler_type) -> None:
            started["address"] = address
            started["handler_name"] = handler_type.__name__

        def serve_forever(self) -> None:
            started["served"] = True

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setenv("LINEAGEWEAVE_DSN", "postgresql://fixture")
    monkeypatch.setenv("LINEAGE_SOURCE_TABLE", "schema.table")
    monkeypatch.setenv("LINEAGEWEAVE_HOST", "127.0.0.1")
    monkeypatch.setenv("LINEAGEWEAVE_PORT", "8130")
    monkeypatch.setattr(stdlib_http_server, "ThreadingHTTPServer", _Server)
    monkeypatch.setattr(server.psycopg, "connect", lambda _dsn: _Connection())
    monkeypatch.setattr(lw, "demote_legacy_shared_thread_edges", lambda _connection: None)
    runpy.run_path(server.__file__, run_name="__main__")
    assert started == {
        "address": ("127.0.0.1", 8130),
        "handler_name": "LineageHandler",
        "served": True,
    }
    assert "LineageWeave listening" in capsys.readouterr().out


def test_http_response_ignores_client_disconnect() -> None:
    """A cancelled browser response must not trigger a second error write."""
    handler = object.__new__(server.LineageHandler)

    class _ClosedWriter:
        def write(self, _body) -> None:
            raise BrokenPipeError("client disconnected")

    handler.wfile = _ClosedWriter()
    handler.send_response = lambda _status: None
    handler.send_header = lambda _name, _value: None
    handler.end_headers = lambda: None
    handler._send(HTTPStatus.OK, {"ok": True})


def test_http_handler_failure_contracts(monkeypatch) -> None:
    """Fail closed on database, identity, callback, validation, and unknown-route failures."""
    application = _Application()
    monkeypatch.setattr(server.LineageHandler, "application", application, raising=False)
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.LineageHandler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    origin = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
        status, _headers, payload = _request(origin, "/api/health")
        assert (status, json.loads(payload)["reason"]) == (HTTPStatus.SERVICE_UNAVAILABLE, "database_unavailable")

        monkeypatch.setattr(application, "actor_for_request", lambda _handler: None)
        status, _headers, payload = _request(origin, "/api/analytics")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.UNAUTHORIZED, "keyverse_session_required")
        status, _headers, payload = _request(origin, "/api/session")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.UNAUTHORIZED, "keyverse_session_required")
        status, _headers, payload = _request(origin, "/api/queue/health")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.UNAUTHORIZED, "keyverse_session_required")

        status, _headers, payload = _request(origin, "/api/login")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.BAD_REQUEST, "invalid_email_address")
        status, _headers, payload = _request(origin, "/api/login?email_address=not-an-email")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.BAD_REQUEST, "invalid_email_address")
        status, _headers, payload = _request(
            origin,
            "/api/login",
            method="POST",
            body={"email_address": "not-an-email"},
        )
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.BAD_REQUEST, "invalid_email_address")

        monkeypatch.setattr(application, "begin_keyverse_login", lambda _request_headers=None, *, email_address: (_ for _ in ()).throw(RuntimeError("unavailable")))
        status, _headers, payload = _request(origin, "/api/login?email_address=member%40example.com")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.SERVICE_UNAVAILABLE, "keyverse_oidc_unavailable")
        status, _headers, payload = _request(
            origin,
            "/api/login",
            method="POST",
            body={"email_address": "member@example.com"},
        )
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.SERVICE_UNAVAILABLE, "keyverse_oidc_unavailable")
        status, _headers, payload = _request(origin, "/api/oidc/callback")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.UNAUTHORIZED, "keyverse_oidc_denied")

        monkeypatch.setattr(application, "actor_for_request", lambda _handler: ACTOR)
        monkeypatch.setattr(
            application,
            "keyverse_admin_accounts",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("keyverse_admin_required")),
        )
        status, _headers, payload = _request(origin, "/api/admin/keyverse/accounts")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.FORBIDDEN, "keyverse_admin_required")
        monkeypatch.setattr(
            application,
            "keyverse_admin_accounts",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("keyverse_admin_unavailable")),
        )
        status, _headers, payload = _request(origin, "/api/admin/keyverse/accounts")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.SERVICE_UNAVAILABLE, "keyverse_admin_unavailable")
        original_body = server.LineageHandler._body

        def invalid_login_body(_handler):
            """Force the login route's bounded JSON parser to report a client error."""
            raise ValueError("invalid fixture body")

        monkeypatch.setattr(server.LineageHandler, "_body", invalid_login_body)
        status, _headers, payload = _request(
            origin,
            "/api/login",
            method="POST",
            body={"email_address": "member@example.com"},
        )
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.BAD_REQUEST, "invalid_request")
        monkeypatch.setattr(server.LineageHandler, "_body", original_body)
        monkeypatch.setattr(application, "document", lambda *_args: (_ for _ in ()).throw(ValueError("bad_document")))
        status, _headers, payload = _request(origin, "/api/documents/DOC-1")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.BAD_REQUEST, "bad_document")
        status, _headers, payload = _request(origin, "/api/documents/DOC-1/unknown")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.NOT_FOUND, "not_found")
        status, _headers, payload = _request(origin, "/api/documents/DOC-1/visibility", method="POST", body=[])
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.BAD_REQUEST, "JSON object required")
        connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
        connection.putrequest("POST", "/api/documents/DOC-1/chat")
        connection.putheader("Content-Length", "1000001")
        connection.endheaders()
        response = connection.getresponse()
        assert (response.status, json.loads(response.read())["error"]) == (
            HTTPStatus.BAD_REQUEST,
            "request body too large",
        )
        connection.close()

        monkeypatch.setattr(
            application,
            "set_visibility",
            lambda *_args: (_ for _ in ()).throw(PermissionError("visibility_forbidden")),
        )
        status, _headers, payload = _request(
            origin, "/api/documents/DOC-1/visibility", method="POST", body={"visibility": "public"}
        )
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.FORBIDDEN, "visibility_forbidden")

        monkeypatch.setattr(
            application,
            "create_ticket",
            lambda *_args: (_ for _ in ()).throw(RuntimeError("worker_unavailable")),
        )
        status, _headers, payload = _request(
            origin, "/api/documents/DOC-1/tickets", method="POST", body={"title": "follow up"}
        )
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.SERVICE_UNAVAILABLE, "live_model_unavailable")

        monkeypatch.setattr(
            application,
            "create_ticket",
            lambda *_args: (_ for _ in ()).throw(Exception("unexpected")),
        )
        status, _headers, payload = _request(
            origin, "/api/documents/DOC-1/tickets", method="POST", body={"title": "follow up"}
        )
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.INTERNAL_SERVER_ERROR, "request_failed")

        monkeypatch.setattr(
            application,
            "document",
            lambda *_args: (_ for _ in ()).throw(RuntimeError("model_unavailable")),
        )
        status, _headers, payload = _request(origin, "/api/documents/DOC-1")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.SERVICE_UNAVAILABLE, "live_model_unavailable")

        monkeypatch.setattr(
            application,
            "document",
            lambda *_args: (_ for _ in ()).throw(Exception("unexpected")),
        )
        status, _headers, payload = _request(origin, "/api/documents/DOC-1")
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.INTERNAL_SERVER_ERROR, "request_failed")

        monkeypatch.setattr(
            application,
            "create_ticket",
            lambda *_args: (_ for _ in ()).throw(KeyError("missing")),
        )
        status, _headers, payload = _request(
            origin, "/api/documents/DOC-1/tickets", method="POST", body={"title": "follow up"}
        )
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.NOT_FOUND, "not_found")
        status, _headers, payload = _request(origin, "/api/unknown", method="POST", body={})
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.NOT_FOUND, "not_found")

        monkeypatch.setattr(application, "actor_for_request", lambda _handler: None)
        status, _headers, payload = _request(origin, "/api/documents/DOC-1/chat", method="POST", body={})
        assert (status, json.loads(payload)["error"]) == (HTTPStatus.UNAUTHORIZED, "keyverse_session_required")
    finally:
        httpd.shutdown()
        httpd.server_close()
