"""TEPP HTTP config and fail-closed accepted envelope (ADR 0014)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "lineageweave" / "tepp_client.py"


def _load():
    pkg = sys.modules.setdefault("lineageweave", types.ModuleType("lineageweave"))
    pkg.__path__ = [str(_PATH.parent)]
    http = types.ModuleType("lineageweave.http_client")

    class HttpClientError(RuntimeError):
        def __init__(self, message: str, status: int | None = None) -> None:
            super().__init__(message)
            self.status = status

    http.HttpClientError = HttpClientError
    sys.modules["lineageweave.http_client"] = http
    spec = importlib.util.spec_from_file_location("lineageweave.tepp_client", _PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["lineageweave.tepp_client"] = module
    spec.loader.exec_module(module)
    return module


tepp = _load()


def _request(**overrides):
    payload = {
        "idempotency_key": "demo-run-1",
        "tenant_workspace_id": "demo-workspace",
        "snapshot_id": "demo-snapshot-1",
        "knowledge_cutoff": "2026-01-01",
        "model_contract_version": "v1",
        "output_profile": "graphml",
    }
    payload.update(overrides)
    return tepp.AnalysisRunRequest(**payload)


def test_config_requires_https_unless_dev_mode() -> None:
    try:
        tepp.tepp_http_config({})
    except tepp.TeppConfigError as exc:
        assert exc.error_code == "tepp_service_unavailable"
    else:
        raise AssertionError("expected unavailable")
    try:
        tepp.tepp_http_config({"TEPP_BASE_URL": "not-a-url", "TEPP_API_TOKEN": "secret"})
    except tepp.TeppConfigError as exc:
        assert exc.error_code == "tepp_base_url_invalid"
    else:
        raise AssertionError("expected invalid url")
    try:
        tepp.tepp_http_config({"TEPP_BASE_URL": "http://tepp.example", "TEPP_API_TOKEN": "secret"})
    except tepp.TeppConfigError as exc:
        assert exc.error_code == "tepp_https_required"
    else:
        raise AssertionError("expected https")
    assert tepp.tepp_http_config(
        {
            "TEPP_BASE_URL": "http://tepp.example",
            "TEPP_API_TOKEN": "secret",
            "LINEAGEWEAVE_DEV_MODE": "1",
        }
    ) == ("http://tepp.example", "secret")
    assert tepp.tepp_http_config(
        {"TEPP_BASE_URL": "https://tepp.example/", "TEPP_API_TOKEN": "secret"}
    ) == ("https://tepp.example", "secret")


def test_accepted_envelope_keeps_lifecycle_only() -> None:
    accepted = tepp.normalize_tepp_accepted(
        {"analysis_run_id": "run-1", "status": "queued", "theta": 1.23}
    )
    assert accepted == {
        "run_id": "run-1",
        "state": "queued",
        "request_id": None,
        "retryable": False,
    }
    assert "theta" not in accepted
    try:
        tepp.normalize_tepp_accepted({"status": "queued"})
    except tepp.TeppEnvelopeError as exc:
        assert exc.error_code == "missing_run_id"
    else:
        raise AssertionError("expected missing_run_id")
    try:
        tepp.normalize_tepp_accepted({"run_id": "run-1", "status": "unknown"})
    except tepp.TeppEnvelopeError as exc:
        assert exc.error_code == "invalid_state"
    else:
        raise AssertionError("expected invalid_state")
    try:
        tepp.normalize_tepp_accepted(
            {"error_code": "temporal_evidence_unavailable", "message": "cutoff"}
        )
    except tepp.TeppEnvelopeError as exc:
        assert exc.error_code == "temporal_evidence_unavailable"
    else:
        raise AssertionError("expected error envelope")


def test_http_transport_posts_published_shape() -> None:
    captured: dict[str, object] = {}

    def fake_post(url, payload, *, headers, timeout):
        captured.update({"url": url, "payload": payload, "headers": headers, "timeout": timeout})
        return {"run_id": "run-1", "state": "accepted", "request_id": "req-1"}

    send = tepp.http_transport("https://tepp.example", "token", post=fake_post)
    result = send(_request().to_json())
    assert result["run_id"] == "run-1"
    assert captured["url"] == "https://tepp.example/v1/analysis-runs"
    assert captured["payload"]["contract_version"] == 1
    assert "theta" not in captured["payload"]
    assert captured["timeout"] == 180


def test_http_transport_maps_conflict_and_client_from_env_stays_closed() -> None:
    http = sys.modules["lineageweave.http_client"]

    def conflict(_url, _payload, **_kwargs):
        raise http.HttpClientError("HTTP 409 from tepp.example", status=409)

    send = tepp.http_transport("https://tepp.example", "token", post=conflict)
    try:
        send(_request().to_json())
    except tepp.TeppEnvelopeError as exc:
        assert exc.error_code == "idempotency_conflict"
    else:
        raise AssertionError("expected idempotency_conflict")

    client = tepp.tepp_client_from_env({})
    try:
        client.submit_analysis_run(_request())
    except tepp.TeppNotAvailable:
        pass
    else:
        raise AssertionError("unset TEPP must stay TeppNotAvailable")
