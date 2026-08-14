"""Verify the Compose live-model worker without granting it identity behavior."""

from __future__ import annotations

import importlib
import json
import runpy
import ssl
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest


def _worker_module():
    """Load a fresh worker module so tests do not share process state."""
    return importlib.reload(importlib.import_module("compose.http_standin"))


class _Response:
    """Provide the narrow urllib response protocol used by the worker."""

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_worker_gateway_configuration_and_tls(monkeypatch) -> None:
    """Require a live gateway credential and retain verified TLS defaults."""
    worker = _worker_module()
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    monkeypatch.delenv("LLM_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    assert worker._gateway_configured() is False
    with pytest.raises(RuntimeError, match="live_model_gateway_required"):
        worker._gateway()

    monkeypatch.setenv("LLM_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("NVIDIA_NIM_API_KEY", "fixture-token")
    monkeypatch.setenv("KEYMAN_MODEL", "fixture-model")
    assert worker._gateway() == ("https://gateway.example", "fixture-token", "fixture-model")
    assert worker._gateway_configured() is True
    context = worker._verified_gateway_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True

    monkeypatch.setenv("LLM_GATEWAY_CA_BUNDLE", "/missing/fixture-ca.pem")
    with pytest.raises(RuntimeError, match="CA_BUNDLE"):
        worker._verified_gateway_context()


def test_worker_gateway_transport_normalizes_http_failures(monkeypatch) -> None:
    """Treat only explicit unsupported paths as fallbacks and fail closed otherwise."""
    worker = _worker_module()
    monkeypatch.setattr(worker, "_gateway", lambda: ("https://gateway.example", "token", "model"))
    captured = {}

    def ok_urlopen(request, timeout, context):
        captured["request"] = request
        captured["timeout"] = timeout
        captured["context"] = context
        return _Response({"ok": True})

    monkeypatch.setattr(worker.urllib.request, "urlopen", ok_urlopen)
    assert worker._post_gateway("/v1/task", {"task": "fixture"}) == {"ok": True}
    assert captured["request"].get_header("Authorization") == "Bearer token"
    assert captured["context"].verify_mode == ssl.CERT_REQUIRED

    monkeypatch.setattr(worker.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response([]))
    assert worker._post_gateway("/v1/task", {"task": "fixture"}) is None

    def unsupported(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://gateway.example", 404, "not found", None, None)

    monkeypatch.setattr(worker.urllib.request, "urlopen", unsupported)
    assert worker._post_gateway("/v1/task", {}) is None

    def rejected(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://gateway.example", 503, "unavailable", None, None)

    monkeypatch.setattr(worker.urllib.request, "urlopen", rejected)
    with pytest.raises(RuntimeError, match="live_model_http_503"):
        worker._post_gateway("/v1/task", {})

    monkeypatch.setattr(
        worker.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")),
    )
    with pytest.raises(RuntimeError, match="live_model_unreachable"):
        worker._post_gateway("/v1/task", {})


def test_worker_falls_back_only_for_incomplete_gateway_results(monkeypatch) -> None:
    """Use the live model when a direct task endpoint supplies no usable answer."""
    worker = _worker_module()
    monkeypatch.setattr(worker, "_gateway", lambda: ("https://gateway.example", "token", "fixture-model"))

    def incomplete(path, _payload):
        if path == "/api/v1/keyman_extract":
            return {}
        if path == "/api/v1/lineageweave_chat":
            return {"answer": ""}
        if path == "/api/v1/content_inspection":
            return {"ocr_text": None, "object_labels": None}
        return {
            "choices": [{"message": {"content": json.dumps({"answer": "fixture", "evidence_ids": []})}}],
            "model": "fixture-model",
        }

    monkeypatch.setattr(worker, "_post_gateway", incomplete)
    assert worker._forward_task({"task": "keyman_extract"})["answer"] == "fixture"
    assert worker._forward_task({"task": "event_lineage_chat"})["answer"] == "fixture"
    assert worker._forward_task({"task": "content_inspection", "image_data_uri": "data:image/png;base64,Zm9v"})["answer"] == "fixture"

    monkeypatch.setattr(
        worker,
        "_post_gateway",
        lambda _path, _payload: {"ocr_text": "", "object_labels": []},
    )
    assert worker._forward_task({"task": "content_inspection", "image_data_uri": "data:image/png;base64,Zm9v"}) == {
        "ocr_text": "",
        "object_labels": [],
    }

    monkeypatch.setattr(worker, "_post_gateway", lambda _path, _payload: None)
    with pytest.raises(RuntimeError, match="live_model_empty_response"):
        worker._forward_task({"task": "keyman_extract"})


def test_worker_task_contracts_and_model_json(monkeypatch) -> None:
    """Accept supported model work only and preserve image prompt isolation."""
    worker = _worker_module()
    assert worker._json_content({"choices": [{"message": {"content": "{}"}}], "model": "fixture"}) == {"model": "fixture"}
    with pytest.raises(RuntimeError, match="invalid_json"):
        worker._json_content({"choices": [{"message": {"content": "not-json"}}]})
    with pytest.raises(RuntimeError, match="invalid_object"):
        worker._json_content({"choices": [{"message": {"content": "[]"}}]})

    monkeypatch.setattr(worker, "_gateway", lambda: ("https://gateway.example", "token", "fixture-model"))
    calls = []

    def post(path, payload):
        calls.append((path, payload))
        if path == "/api/v1/keyman_extract":
            return {"keymen": []}
        if path == "/api/v1/lineageweave_chat":
            return {"answer": "fixture"}
        if path == "/api/v1/content_inspection":
            return None
        return {
            "choices": [{"message": {"content": json.dumps({"ocr_text": "fixture", "object_labels": []})}}],
            "model": "fixture-model",
        }

    monkeypatch.setattr(worker, "_post_gateway", post)
    assert worker._forward_task({"task": "keyman_extract"}) == {"keymen": []}
    assert worker._forward_task({"task": "event_lineage_chat"}) == {"answer": "fixture"}
    result = worker._forward_task({"task": "content_inspection", "image_data_uri": "data:image/png;base64,Zm9v"})
    assert result["ocr_text"] == "fixture"
    model_message = calls[-1][1]["messages"][1]["content"]
    assert model_message[1]["image_url"]["url"].startswith("data:image/png")
    assert "image_data_uri" not in model_message[0]["text"]
    with pytest.raises(RuntimeError, match="content_inspection_image_required"):
        worker._forward_task({"task": "content_inspection"})
    with pytest.raises(RuntimeError, match="unsupported_worker_task"):
        worker._forward_task({"task": "identity"})


def test_worker_http_routes_and_main(monkeypatch) -> None:
    """Expose health and model routes while rejecting all identity routes."""
    worker = _worker_module()
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    monkeypatch.delenv("LLM_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    httpd = worker.ThreadingHTTPServer(("127.0.0.1", 0), worker.StandinHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        with urllib.request.urlopen(origin + "/health", timeout=5) as response:
            assert json.loads(response.read()) == {
                "status": "ok",
                "model_gateway_configured": False,
            }
        for path, data in (
            ("/.well-known/openid-configuration", None),
            ("/protocol/openid-connect/auth", None),
            ("/protocol/openid-connect/token", b"{}"),
            ("/protocol/openid-connect/token/introspect", b"{}"),
            ("/unknown", None),
            ("/unknown", b"not-json"),
            ("/unknown", b"[]"),
            ("/api/v1/unknown", b"{}"),
        ):
            request = urllib.request.Request(origin + path, data=data, method="POST" if data is not None else "GET")
            with pytest.raises(urllib.error.HTTPError) as failure:
                urllib.request.urlopen(request, timeout=5)
            assert failure.value.code == 404

        request = urllib.request.Request(origin + "/api/v1/content_inspection", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as failure:
            urllib.request.urlopen(request, timeout=5)
        assert failure.value.code in {404, 503}

        forwarded = {}

        def forward(payload):
            forwarded.update(payload)
            return {"answer": "fixture"}

        monkeypatch.setattr(worker, "_forward_task", forward)
        request = urllib.request.Request(
            origin + "/api/v1/lineageweave_chat",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            assert json.loads(response.read()) == {"answer": "fixture"}
        assert forwarded == {"task": "event_lineage_chat"}
    finally:
        httpd.shutdown()
        httpd.server_close()

    started = {}

    class _Server:
        def __init__(self, address, handler):
            started["address"] = address
            started["handler"] = handler

        def serve_forever(self):
            started["served"] = True

    monkeypatch.setenv("STANDIN_PORT", "9090")
    monkeypatch.setattr(worker, "ThreadingHTTPServer", _Server)
    worker.main()
    assert started == {"address": ("0.0.0.0", 9090), "handler": worker.StandinHandler, "served": True}


def test_worker_cli_entrypoint_starts_the_server(monkeypatch) -> None:
    """Run the CLI guard with a real module load and a bounded fake server."""
    started = {}

    class _Server:
        def __init__(self, address, handler):
            started["address"] = address
            started["handler"] = handler

        def serve_forever(self):
            started["served"] = True

    monkeypatch.setenv("STANDIN_PORT", "9091")
    monkeypatch.setattr("http.server.ThreadingHTTPServer", _Server)
    runpy.run_path(str(Path("compose/http_standin.py").resolve()), run_name="__main__")
    assert started["address"] == ("0.0.0.0", 9091)
    assert started["served"] is True
