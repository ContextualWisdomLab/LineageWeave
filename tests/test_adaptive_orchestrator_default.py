"""LineageWeave delegates product-default LLM execution to auto policy."""

from __future__ import annotations

from pathlib import Path

from lineageweave import adjudication_client, post_chat, post_evaluation
from lineageweave.post_chat import ChatSourceDocument, ContextualOrchestratorPostChatClient


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


def test_post_chat_requests_verify_mode(monkeypatch) -> None:
    """Citation chat must send verify on the wire, not a docstring mention of auto."""

    observed: dict[str, object] = {}

    def fake_post_json(url, payload, *, headers, timeout):
        observed["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"answer_text": "The follow-up names the same bid.",'
                            ' "cited_source_numbers": [1]}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(post_chat, "post_json", fake_post_json)
    client = ContextualOrchestratorPostChatClient(
        "https://orchestrator.example.test", "inference_token"
    )
    answer = client.answer(
        "What happened between these events?",
        [
            ChatSourceDocument(
                post_id="post-bid-follow-up",
                post_title="Bid follow-up",
                post_body="Northridge asked to confirm the bid date.",
            )
        ],
    )

    assert answer.cited_post_ids == ("post-bid-follow-up",)
    assert observed["payload"]["mode"] == "verify"


def test_adjudication_requests_verify_mode(monkeypatch) -> None:
    """Lineage adjudication must send verify on the wire, not a source substring."""

    observed: dict[str, object] = {}

    def fake_post_json(url, payload, *, headers, timeout):
        observed["payload"] = payload
        return {"choices": [{"message": {"content": "0.91"}}]}

    monkeypatch.setattr(adjudication_client, "post_json", fake_post_json)
    client = adjudication_client.ContextualOrchestratorAdjudicationClient(
        "https://orchestrator.example.test", "inference_token"
    )
    confidence = client.judge(
        "Quarterly budget review meeting notes",
        "Budget review follow-up: revised quarterly numbers",
    )

    assert confidence == 0.91
    assert observed["payload"]["mode"] == "verify"


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
