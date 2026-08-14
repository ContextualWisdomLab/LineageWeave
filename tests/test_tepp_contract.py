"""Contract tests for the separate TEPP HTTP port and persisted run registry."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

import lineageweave as lw
import lineageweave_server as server


REQUEST = {
    "contract_version": "v1",
    "idempotency_key": "lw-run-1",
    "snapshot_id": "snapshot-current",
    "knowledge_cutoff": "2026-08-15T00:00:00Z",
    "model_contract": {"name": "trsl-tm", "version": "v0.4"},
    "configuration": {"source": "lineageweave"},
    "output_profile": {"format": "json", "include": ["events", "relations"]},
}
ACTOR = {"account_id": "admin-1", "corp_code": "CORP-A", "pu_code": "PU-1", "roles": ["admin"]}


class _Connection:
    """Provide the context-manager shape used by the server's PostgreSQL calls."""

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _http_error(code: int) -> urllib.error.HTTPError:
    """Build one bounded external-service error."""
    return urllib.error.HTTPError("https://tepp.example", code, "fixture", {}, io.BytesIO(b"{}"))


def test_tepp_config_requires_explicit_service_and_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing, malformed, insecure, and development TEPP configurations are distinct."""
    monkeypatch.delenv("TEPP_BASE_URL", raising=False)
    monkeypatch.delenv("TEPP_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="tepp_service_unavailable"):
        lw.tepp_http_config()
    monkeypatch.setenv("TEPP_BASE_URL", "not-a-url")
    monkeypatch.setenv("TEPP_API_TOKEN", "secret")
    with pytest.raises(RuntimeError, match="tepp_base_url_invalid"):
        lw.tepp_http_config()
    monkeypatch.setenv("TEPP_BASE_URL", "http://tepp.example")
    monkeypatch.delenv("LINEAGEWEAVE_DEV_MODE", raising=False)
    with pytest.raises(RuntimeError, match="tepp_https_required"):
        lw.tepp_http_config()
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    assert lw.tepp_http_config() == ("http://tepp.example", "secret")
    monkeypatch.setenv("TEPP_BASE_URL", "https://tepp.example/")
    assert lw.tepp_http_config() == ("https://tepp.example", "secret")


def test_normalize_tepp_request_is_versioned_bounded_and_idempotent() -> None:
    """The target request rejects unknown fields and malformed contract objects."""
    with pytest.raises(ValueError, match="object_required"):
        lw.normalize_tepp_analysis_request(None)  # type: ignore[arg-type]
    normalized = lw.normalize_tepp_analysis_request(REQUEST)
    assert normalized["request_sha256"]
    assert json.loads(json.dumps({key: value for key, value in normalized.items() if key != "request_sha256"})) == REQUEST
    with pytest.raises(ValueError, match="unknown_field"):
        lw.normalize_tepp_analysis_request({**REQUEST, "extra": True})
    with pytest.raises(ValueError, match="unsupported"):
        lw.normalize_tepp_analysis_request({**REQUEST, "contract_version": "v2"})
    for field, value in (("idempotency_key", ""), ("snapshot_id", ""), ("knowledge_cutoff", "")):
        with pytest.raises(ValueError, match=field):
            lw.normalize_tepp_analysis_request({**REQUEST, field: value})
    with pytest.raises(ValueError, match="model_contract"):
        lw.normalize_tepp_analysis_request({**REQUEST, "model_contract": []})
    with pytest.raises(ValueError, match="configuration"):
        lw.normalize_tepp_analysis_request({**REQUEST, "configuration": []})
    with pytest.raises(ValueError, match="output_profile"):
        lw.normalize_tepp_analysis_request({**REQUEST, "output_profile": []})
    with pytest.raises(ValueError, match="too_large"):
        lw.normalize_tepp_analysis_request({**REQUEST, "configuration": {"blob": "x" * 70_000}})


def test_tepp_response_and_http_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST/GET preserve only lifecycle metadata and map external failures explicitly."""
    assert lw._normalize_tepp_response({"analysis_run_id": "run-1", "status": "queued"})["run_id"] == "run-1"
    with pytest.raises(RuntimeError, match="missing_run_id"):
        lw._normalize_tepp_response({"status": "queued"})
    with pytest.raises(RuntimeError, match="invalid_state"):
        lw._normalize_tepp_response({"run_id": "run-1", "status": "unknown"})
    with pytest.raises(RuntimeError, match="invalid"):
        lw._normalize_tepp_response([])

    captured: dict[str, object] = {}

    def response(request, *, timeout, context):  # noqa: ANN001
        captured.update({"url": request.full_url, "method": request.get_method(), "body": json.loads(request.data) if request.data else None, "timeout": timeout, "context": context})
        return {"run_id": "run-1", "state": "accepted", "request_id": "req-1"}

    monkeypatch.setattr(lw, "_post_json_from_request", response)
    posted = lw.post_tepp_analysis_run(REQUEST, base_url="https://tepp.example", token="token", timeout=999)
    assert posted["run_id"] == "run-1"
    assert captured["url"] == "https://tepp.example/v1/analysis-runs"
    assert captured["method"] == "POST"
    assert "request_sha256" not in captured["body"]
    assert captured["timeout"] == 180
    assert captured["context"] is not None
    refreshed = lw.get_tepp_analysis_run("run:1", base_url="https://tepp.example", token="token")
    assert refreshed["state"] == "accepted"
    assert captured["url"] == "https://tepp.example/v1/analysis-runs/run%3A1"
    with pytest.raises(ValueError, match="run_id_invalid"):
        lw.get_tepp_analysis_run("run/1", base_url="https://tepp.example", token="token")

    for code, message in ((409, "idempotency_conflict"), (429, "rate_limited"), (500, "http_500")):
        monkeypatch.setattr(lw, "_post_json_from_request", lambda *_args, code=code, **_kwargs: (_ for _ in ()).throw(_http_error(code)))
        with pytest.raises(RuntimeError, match=message):
            lw.post_tepp_analysis_run(REQUEST, base_url="https://tepp.example", token="token")
    monkeypatch.setattr(lw, "_post_json_from_request", lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")))
    with pytest.raises(RuntimeError, match="unreachable"):
        lw.post_tepp_analysis_run(REQUEST, base_url="https://tepp.example", token="token")
    monkeypatch.setattr(lw, "_post_json_from_request", lambda *_args, **_kwargs: (_ for _ in ()).throw(json.JSONDecodeError("bad", "", 0)))
    with pytest.raises(RuntimeError, match="unreachable"):
        lw.post_tepp_analysis_run(REQUEST, base_url="https://tepp.example", token="token")


def test_tepp_run_registry_is_same_corp_and_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Persisted TEPP metadata is scoped, repeatable, and cannot mutate an idempotency key."""
    ddl: list[str] = []
    monkeypatch.setattr(lw, "_database_exec", lambda _connection, sql, _params=(): ddl.append(sql))
    lw.ensure_tepp_run_table(_Connection())
    assert "CREATE TABLE IF NOT EXISTS analysis_tepp_run_records" in ddl[0]
    monkeypatch.setattr(lw, "ensure_tepp_run_table", lambda _connection: None)
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)
    executions: list[tuple[str, tuple[object, ...]]] = []
    existing: list[dict[str, object]] = []
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: list(existing))
    monkeypatch.setattr(lw, "_database_exec", lambda _connection, sql, params=(): executions.append((sql, tuple(params))))
    response = {"run_id": "run-1", "state": "queued", "request_id": "req-1", "retryable": False}
    saved = lw.persist_tepp_run_record(_Connection(), ACTOR, REQUEST, response)
    assert saved["run_id"] == "run-1"
    assert executions
    existing[:] = [{**saved, "tepp_run_id": "run-1", "created_at": "now", "updated_at": "now"}]
    assert lw.persist_tepp_run_record(_Connection(), ACTOR, REQUEST, response)["run_id"] == "run-1"
    with pytest.raises(ValueError, match="idempotency_conflict"):
        lw.persist_tepp_run_record(_Connection(), ACTOR, {**REQUEST, "snapshot_id": "different"}, response)
    with pytest.raises(ValueError, match="response_invalid"):
        lw.persist_tepp_run_record(_Connection(), ACTOR, REQUEST, {"run_id": "", "state": "queued"})

    existing.clear()
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: False)
    assert lw.load_tepp_run_records(_Connection(), ACTOR) == []
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)
    existing[:] = [{**saved, "tepp_run_id": "run-1", "created_at": "now", "updated_at": "now"}]
    assert lw.load_tepp_run_records(_Connection(), ACTOR)[0]["run_id"] == "run-1"
    assert lw.load_tepp_run_by_idempotency(_Connection(), ACTOR, "lw-run-1")["run_id"] == "run-1"
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: False)
    assert lw.load_tepp_run_by_idempotency(_Connection(), ACTOR, "lw-run-1") is None


def test_tepp_run_state_update_and_server_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refresh and administrator service methods preserve the same external boundary."""
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)
    row = {
        "tepp_run_id": "run-1", "idempotency_key": "lw-run-1", "snapshot_id": "snapshot-current",
        "knowledge_cutoff": "cutoff", "request_sha256": "hash", "remote_state": "queued",
        "request_id": "req-1", "retryable": False, "created_at": "now", "updated_at": "now",
    }
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [dict(row)])
    executions: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(lw, "_database_exec", lambda _connection, sql, params=(): executions.append((sql, tuple(params))))
    updated = lw.update_tepp_run_state(_Connection(), ACTOR, "run-1", {"run_id": "run-1", "state": "completed"})
    assert updated["remote_state"] == "completed"
    assert executions
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: False)
    with pytest.raises(KeyError, match="not_found"):
        lw.update_tepp_run_state(_Connection(), ACTOR, "run-1", {"run_id": "run-1", "state": "completed"})
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    with pytest.raises(KeyError, match="not_found"):
        lw.update_tepp_run_state(_Connection(), ACTOR, "run-absent", {"run_id": "run-absent", "state": "completed"})

    app = object.__new__(server.LineageApplication)
    app.dsn = "postgresql://fixture"
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "load_tepp_run_records", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(lw, "tepp_http_config", lambda: ("https://tepp.example", "token"))
    assert app.tepp_status(ACTOR)["configured"] is True
    monkeypatch.setattr(lw, "tepp_http_config", lambda: (_ for _ in ()).throw(RuntimeError("tepp_service_unavailable")))
    assert app.tepp_status(ACTOR)["status"] == "unavailable"
    monkeypatch.setattr(lw, "tepp_http_config", lambda: ("https://tepp.example", "token"))
    monkeypatch.setattr(lw, "load_tepp_run_by_idempotency", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "post_tepp_analysis_run", lambda *_args, **_kwargs: {"run_id": "run-2", "state": "accepted"})
    monkeypatch.setattr(lw, "persist_tepp_run_record", lambda *_args, **_kwargs: {"run_id": "run-2", "remote_state": "accepted"})
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda *_args, **_kwargs: None)
    app._flush_event_outbox = lambda: 0
    assert app.submit_tepp_analysis(ACTOR, REQUEST)["status"] == "accepted"
    monkeypatch.setattr(lw, "load_tepp_run_by_idempotency", lambda *_args, **_kwargs: {"request_sha256": "different", "run_id": "run-1"})
    with pytest.raises(ValueError, match="idempotency_conflict"):
        app.submit_tepp_analysis(ACTOR, REQUEST)
    same_hash = lw.normalize_tepp_analysis_request(REQUEST)["request_sha256"]
    monkeypatch.setattr(lw, "load_tepp_run_by_idempotency", lambda *_args, **_kwargs: {"request_sha256": same_hash, "run_id": "run-1"})
    assert app.submit_tepp_analysis(ACTOR, REQUEST)["status"] == "existing"
    monkeypatch.setattr(lw, "get_tepp_analysis_run", lambda *_args, **_kwargs: {"run_id": "run-2", "state": "completed"})
    monkeypatch.setattr(lw, "update_tepp_run_state", lambda *_args, **_kwargs: {"run_id": "run-2", "remote_state": "completed"})
    assert app.refresh_tepp_analysis(ACTOR, "run-2")["remote_state"] == "completed"


def test_tepp_http_routes_dispatch_to_admin_application_methods() -> None:
    """The new GET and POST routes remain server-side administrator dispatches."""
    class Application:
        """Expose only the TEPP methods needed by this route fixture."""

        def tepp_status(self, _actor):
            return {"status": "ready"}

        def refresh_tepp_analysis(self, _actor, run_id):
            return {"run_id": run_id, "remote_state": "completed"}

        def submit_tepp_analysis(self, _actor, body):
            return {"status": "accepted", "snapshot_id": body["snapshot_id"]}

    handler = object.__new__(server.LineageHandler)
    handler.application = Application()
    handler._actor = lambda: ACTOR
    sent: list[tuple[object, object]] = []
    handler._send = lambda status, payload: sent.append((status, payload))
    handler._error = lambda *_args: None
    handler._path_parts = lambda: ["api", "admin", "tepp", "status"]
    handler.do_GET()
    assert sent[-1][1] == {"status": "ready"}
    handler._path_parts = lambda: ["api", "admin", "tepp", "analysis-runs", "run-1"]
    handler.do_GET()
    assert sent[-1][1]["run_id"] == "run-1"
    handler._path_parts = lambda: ["api", "admin", "tepp", "analysis-runs"]
    handler._body = lambda: {"snapshot_id": "snapshot-current"}
    handler.do_POST()
    assert sent[-1][1]["status"] == "accepted"
