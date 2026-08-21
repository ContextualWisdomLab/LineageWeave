"""Contracts for contextual metadata on open and closed HTTP payloads."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, HTTPServer

from lineageweave import tepp_project_history as tepp_transport_module
from lineageweave.http_client import post_json
from lineageweave.llm_context import use_llm_metadata
from lineageweave.tepp_project_history import TeppProjectHistoryClient


class _EchoHandler(BaseHTTPRequestHandler):
    """Echo one JSON request for shared-client contract tests."""

    def do_POST(self) -> None:  # noqa: N802 -- stdlib callback name
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        body = json.dumps({"echo": payload}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Suppress test HTTP access logs."""


def _serve() -> tuple[HTTPServer, str]:
    """Start one local JSON echo server."""

    server = HTTPServer(("127.0.0.1", 0), _EchoHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"


def _request() -> dict[str, object]:
    """Return one minimal exact TEPP project-history request."""

    return {
        "contract_version": 1,
        "idempotency_key": "strict-http-metadata",
        "tenant_workspace_id": "tenant-a",
        "project_key": "P-100",
        "project_name": "Synthetic renewal",
        "knowledge_cutoff": "2026-08-20T12:00:00Z",
        "focus_event_id": "event-1",
        "events": [
            {
                "event_id": "event-1",
                "event_type_code": "voc_received",
                "event_title": "Synthetic VOC received",
                "occurred_at": "2026-08-20T10:00:00Z",
                "available_at": "2026-08-20T10:00:00Z",
                "source_post_id": "post-1",
                "evidence_text": "Synthetic VOC received",
                "actor_ids": ["lw-actor-1"],
            }
        ],
    }


def _response(request: dict[str, object]) -> dict[str, object]:
    """Return the exact successful response for ``request``."""

    events = deepcopy(request["events"])
    return {
        "contract_version": 1,
        "project_key": request["project_key"],
        "project_name": request["project_name"],
        "focus_event_id": request["focus_event_id"],
        "knowledge_cutoff": request["knowledge_cutoff"],
        "history_span_start": events[0]["occurred_at"],
        "history_span_end": events[-1]["occurred_at"],
        "participant_count": 1,
        "inference_status": "temporal_association_only",
        "events": events,
        "findings": [],
    }


def test_post_json_includes_llm_metadata_by_default() -> None:
    """Existing LLM clients retain contextual metadata enrichment."""

    server, base = _serve()
    try:
        with use_llm_metadata({"lineageweave_post_id": "post-1"}):
            body = post_json(
                f"{base}/v1/chat/completions",
                {"messages": []},
                headers={},
                timeout=2.0,
            )
    finally:
        server.shutdown()

    assert body["echo"] == {
        "messages": [],
        "metadata": {"lineageweave_post_id": "post-1"},
    }


def test_post_json_can_disable_metadata_for_a_closed_contract() -> None:
    """Closed contracts remain byte-shape compatible inside an LLM context."""

    server, base = _serve()
    try:
        with use_llm_metadata({"lineageweave_post_id": "post-1"}):
            body = post_json(
                f"{base}/v1/project-histories",
                {"contract_version": 1},
                headers={},
                timeout=2.0,
                include_llm_metadata=False,
            )
    finally:
        server.shutdown()

    assert body["echo"] == {"contract_version": 1}


def test_default_tepp_transport_disables_context_metadata(monkeypatch) -> None:
    """The strict TEPP adapter opts out even when Ask sets LLM metadata."""

    request = _request()
    captured: dict[str, object] = {}

    def fake_post_json(url, payload, *, headers, timeout, include_llm_metadata):
        captured.update(
            url=url,
            payload=deepcopy(payload),
            headers=headers,
            timeout=timeout,
            include_llm_metadata=include_llm_metadata,
        )
        return _response(payload)

    monkeypatch.setattr(tepp_transport_module, "post_json", fake_post_json)
    with use_llm_metadata({"lineageweave_post_id": "must-not-cross"}):
        result = TeppProjectHistoryClient("https://tepp.example").project(request)

    assert result["inference_status"] == "temporal_association_only"
    assert captured["include_llm_metadata"] is False
    assert captured["payload"] == request
    assert "metadata" not in captured["payload"]
