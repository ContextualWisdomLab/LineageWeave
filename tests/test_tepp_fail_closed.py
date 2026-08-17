"""Fail-closed TEPP envelope (ADR 0022). Numpy/stdlib only.

Loads modules from disk so this file does not import the package
``__init__``. The envelope must never carry a theta.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_ROOT = Path(__file__).resolve().parents[1] / "lineageweave"
_pkg = ModuleType("lineageweave")
_pkg.__path__ = [str(_ROOT)]
sys.modules.setdefault("lineageweave", _pkg)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"lineageweave.{name}", _ROOT / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"lineageweave.{name}"] = module
    spec.loader.exec_module(module)
    return module


fail_closed = _load("fail_closed")
tepp_client = _load("tepp_client")


def _request():
    return tepp_client.AnalysisRunRequest(
        idempotency_key="demo-run-1",
        tenant_workspace_id="demo-workspace",
        snapshot_id="process_unit:2026-W02",
        knowledge_cutoff="2026-W02",
        model_contract_version="v1",
        output_profile="graphml",
    )


def test_default_submit_is_tepp_not_available_without_a_theta() -> None:
    envelope = tepp_client.submit_fail_closed(tepp_client.TeppClient(), _request())
    payload = envelope.to_json()
    assert payload["channel_code"] == fail_closed.CHANNEL_TEPP
    assert payload["outcome_code"] == fail_closed.OUTCOME_TEPP_NOT_AVAILABLE
    assert "invented" in payload["next_action"].lower()
    assert "theta" not in payload
    assert "theta_eap" not in payload
    assert "mean_theta" not in payload
    assert payload["request"]["snapshot_id"] == "process_unit:2026-W02"


def test_accepted_envelope_strips_a_fabricated_theta() -> None:
    def transport(_payload: dict) -> dict:
        return {"status": "accepted", "run_id": "tepp-run-1", "theta": 1.23}

    envelope = tepp_client.submit_fail_closed(tepp_client.TeppClient(transport=transport), _request())
    payload = envelope.to_json()
    assert payload["outcome_code"] == fail_closed.OUTCOME_ACCEPTED
    assert payload["accepted"]["run_id"] == "tepp-run-1"
    assert "theta" not in payload["accepted"]
    assert "theta" not in payload


def test_http_transport_posts_the_published_path() -> None:
    seen: dict[str, object] = {}

    def fake_post(url: str, payload: dict, *, headers: dict, timeout: float) -> dict:
        seen["url"] = url
        seen["payload"] = payload
        return {"status": "accepted", "run_id": "tepp-http-1"}

    import types

    http_mod = types.ModuleType("lineageweave.http_client")
    http_mod.HttpClientError = RuntimeError
    http_mod.post_json = fake_post
    sys.modules["lineageweave.http_client"] = http_mod

    transport = tepp_client.http_tepp_transport("https://tepp.example")
    result = transport(_request().to_json())
    assert result["run_id"] == "tepp-http-1"
    assert seen["url"] == "https://tepp.example/v1/analysis-runs"
    assert seen["payload"]["contract_version"] == 1
