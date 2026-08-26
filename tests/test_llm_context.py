from __future__ import annotations

import lineageweave.http_client as http_client
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata


def test_post_metadata_is_stable_and_post_specific() -> None:
    values = {
        "source_process_unit_code": "PU-01",
        "author_account_id": "author-1",
        "corporate_entity_code": "CORP-01",
        "visibility_code": "public",
    }
    first = build_post_llm_metadata("post-1", values)
    second = build_post_llm_metadata("post-1", values)
    other = build_post_llm_metadata("post-2", values)

    assert first == second
    assert first["lineageweave_post_session_id"] != other["lineageweave_post_session_id"]
    assert first["lineageweave_pu"] == "PU-01"
    assert first["lineageweave_author_id"] == "author-1"
    assert first["lineageweave_corp_code"] == "CORP-01"
    assert first["lineageweave_visibility"] == "public"


def test_http_transport_merges_context_metadata_without_mutating_payload(monkeypatch) -> None:
    seen = {}

    def fake_request(method, url, *, body, headers, timeout):
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
