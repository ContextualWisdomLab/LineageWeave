from __future__ import annotations

import json

import pytest

import lineageweave.http_client as http_client
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata


def test_post_metadata_is_stable_and_post_specific() -> None:
    values = {
        "source_process_unit_code": "PU-01",
        "author_account_id": "author-1",
        "corporate_entity_code": "CORP-01",
    }
    first = build_post_llm_metadata("post-1", values)
    second = build_post_llm_metadata("post-1", values)
    other = build_post_llm_metadata("post-2", values)

    assert first == second
    assert first["lineageweave_post_session_id"] != other["lineageweave_post_session_id"]
    assert first["lineageweave_pu"] == "PU-01"
    assert first["lineageweave_author_id"] == "author-1"
    assert first["lineageweave_corp_code"] == "CORP-01"


def test_http_transport_merges_context_metadata_without_mutating_payload(monkeypatch) -> None:
    seen = {}

    def fake_request(method, url, *, body, headers, timeout, **kwargs):
        del kwargs
        seen["payload"] = body
        return 200, b"{}"

    monkeypatch.setattr(http_client, "_request", fake_request)
    payload = {"messages": [], "metadata": {"channel": "summary"}}
    metadata = build_post_llm_metadata("post-1", {"source_process_unit_code": "PU-01"})

    with use_llm_metadata(metadata):
        http_client.post_json("http://orchestrator/v1/chat/completions", payload, headers={}, timeout=1)

    assert payload["metadata"] == {"channel": "summary"}
    assert seen["payload"]
    assert "lineageweave_post_session_id" in seen["payload"].decode("utf-8")
    assert "lineageweave_pu" in seen["payload"].decode("utf-8")


def test_orchestrator_session_is_stable_across_modalities_and_retries(monkeypatch) -> None:
    """One post uses one payload session for chat, VISION, and embeddings."""
    requests: list[tuple[str, dict[str, object], dict[str, str]]] = []

    def fake_request(method, url, *, body, headers, timeout, **kwargs):
        del kwargs
        del method, timeout
        requests.append((url, json.loads(body), headers))
        return 200, b'{"choices": []}'

    monkeypatch.setattr(http_client, "_request", fake_request)
    response_payload = {"choices": []}
    first = build_post_llm_metadata("synthetic-post-1", {})
    second = build_post_llm_metadata("synthetic-post-2", {})

    with use_llm_metadata(first):
        for path in (
            "/v1/chat/completions",
            "/v1/vision/structured",
            "/v1/batch/embeddings",
            "/v1/chat/completions",
        ):
            assert http_client.post_json(
                f"https://orchestrator.example{path}",
                {"input": []},
                headers={},
                timeout=1,
            ) == response_payload
    with use_llm_metadata(second):
        http_client.post_json(
            "https://orchestrator.example/v1/chat/completions",
            {"input": []},
            headers={},
            timeout=1,
        )

    first_session = first["lineageweave_post_session_id"]
    assert {request[1]["session_id"] for request in requests[:4]} == {first_session}
    assert {request[2]["x-lineageweave-session-id"] for request in requests[:4]} == {
        first_session
    }
    assert all(
        request[1]["metadata"]["lineageweave_post_id"] == "synthetic-post-1"
        for request in requests[:4]
    )
    assert requests[4][1]["session_id"] == second["lineageweave_post_session_id"]
    assert requests[4][1]["session_id"] != first_session


def test_orchestrator_session_is_not_invented_or_sent_to_other_peers(monkeypatch) -> None:
    """Missing post context and non-orchestrator calls retain their payloads."""
    bodies: list[dict[str, object]] = []

    def fake_request(method, url, *, body, headers, timeout, **kwargs):
        del kwargs
        del method, url, headers, timeout
        bodies.append(json.loads(body))
        return 200, b"{}"

    monkeypatch.setattr(http_client, "_request", fake_request)
    http_client.post_json(
        "https://orchestrator.example/v1/chat/completions",
        {"messages": []},
        headers={},
        timeout=1,
    )
    with use_llm_metadata(build_post_llm_metadata("synthetic-post", {})):
        http_client.post_json(
            "https://tepp.example/v1/measurements",
            {"observations": []},
            headers={},
            timeout=1,
            service_peer_name="tepp",
        )

    assert "session_id" not in bodies[0]
    assert "session_id" not in bodies[1]


def test_orchestrator_rejects_a_caller_session_that_conflicts_with_post_context(
    monkeypatch,
) -> None:
    """A caller cannot silently split one post across orchestrator sessions."""
    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, b"{}"))
    metadata = build_post_llm_metadata("synthetic-post", {})

    with use_llm_metadata(metadata), pytest.raises(
        ValueError, match="does not match the active post session"
    ):
        http_client.post_json(
            "https://orchestrator.example/v1/chat/completions",
            {"messages": [], "session_id": "different-session"},
            headers={},
            timeout=1,
        )
