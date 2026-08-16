"""LineageWeave delegates product-default LLM execution to auto policy."""

from __future__ import annotations

from pathlib import Path

from lineageweave import post_evaluation


def test_post_evaluation_adapter_defaults_to_auto(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_post_json(url, payload, *, headers, timeout):
        observed.update(
            url=url,
            payload=payload,
            headers=headers,
            timeout=timeout,
        )
        return {"choices": [{"message": {"content": "{}"}}]}

    monkeypatch.setattr(post_evaluation, "post_json", fake_post_json)
    adapter = post_evaluation._OrchestratorCompleteAdapter(
        "https://orchestrator.example.test", "inference_token"
    )
    adapter.complete([{"role": "user", "content": "Evaluate this evidence."}])

    assert observed["payload"]["mode"] == "auto"


def test_post_evaluation_judge_uses_auto_by_default() -> None:
    client = post_evaluation.ContextualOrchestratorPostEvaluationClient(
        "https://orchestrator.example.test", "inference_token"
    )
    assert client._judge.mode == "auto"


def test_runtime_clients_do_not_force_single_model_route() -> None:
    package_root = Path(__file__).resolve().parents[1] / "lineageweave"
    violations: list[str] = []
    for path in sorted(package_root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if '"mode": "route"' in text or "'mode': 'route'" in text:
            violations.append(f"{path.name}: request payload")
        if 'mode="route"' in text or "mode='route'" in text:
            violations.append(f"{path.name}: constructor/call default")
        if 'mode: str = "route"' in text or "mode: str = 'route'" in text:
            violations.append(f"{path.name}: typed default")
    assert violations == []
