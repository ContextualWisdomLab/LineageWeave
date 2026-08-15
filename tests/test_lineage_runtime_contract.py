"""Exercise inline-content, live-gateway, and CLI runtime contracts without recorded answers."""

from __future__ import annotations

import base64
import io
import json
import runpy
import sys
from types import SimpleNamespace
import urllib.error

import pytest

import lineageweave as lw


class _Response:
    """Expose one JSON payload through the standard response context protocol."""

    def __init__(self, value: object) -> None:
        self.value = value

    def __enter__(self) -> "_Response":
        """Enter the response context."""
        return self

    def __exit__(self, *_args: object) -> bool:
        """Do not suppress a request error."""
        return False

    def read(self) -> bytes:
        """Return an encoded JSON model or gateway response."""
        return json.dumps(self.value).encode("utf-8")


class _Connection:
    """Supply the context-manager boundary used by the CLI path."""

    def __enter__(self) -> "_Connection":
        """Enter the fake direct-database connection."""
        return self

    def __exit__(self, *_args: object) -> bool:
        """Do not suppress database adapter errors."""
        return False


def _http_error(code: int) -> urllib.error.HTTPError:
    """Build a bounded HTTP error for fallback-path tests."""
    return urllib.error.HTTPError("https://gateway.example", code, "fixture", {}, io.BytesIO(b"fixture"))


def _sequence_urlopen(items: list[object]):
    """Return a request function that consumes explicit success/error responses."""
    def urlopen(_request, **_kwargs):  # noqa: ANN001
        item = items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return urlopen


def test_inline_content_parsing_and_vision_boundary() -> None:
    """Classify and validate real inline bytes without serializing them into public metadata."""
    png = b"\x89PNG\r\n\x1a\nfixture"
    encoded_png = base64.b64encode(png).decode("ascii")
    assets = lw.extract_inline_assets(
        f"before data:image/png;base64,{encoded_png}\n<svg><text>fixture</text></svg>"
    )
    assert [asset["content_kind"] for asset in assets] == [lw.CONTENT_INLINE_IMAGE, lw.CONTENT_INLINE_MARKUP]
    assert "data_uri" not in lw.public_asset_metadata({**assets[0], "asset_sha256": "private"})
    binary = "QUJD" * 100
    assert lw.extract_inline_assets(binary)[0]["content_kind"] == lw.CONTENT_INLINE_BINARY
    assert lw.classify_content_kind(None, artifact_reference=True) == lw.CONTENT_ARTIFACT_REFERENCE
    assert lw.classify_content_kind("{\"kind\":\"event\"}") == lw.CONTENT_STRUCTURED

    prepared = lw.prepare_content_inspection_asset({"mime_type": "image/png", "data_uri": f"data:image/png;base64,{encoded_png}"})
    assert prepared["asset_sha256"] == lw.content_asset_sha256({"data_uri": prepared["image_data_uri"]})
    normalized = lw.normalize_content_inspection_response(
        {"text": " caption ", "labels": [{"name": "Chart", "detail": "bar"}, "chart", "map"]}
    )
    assert normalized["object_labels"] == [{"label": "Chart", "description": "bar"}, {"label": "map", "description": ""}]
    inspected = lw.derive_content_inspection_via_llm(
        {"mime_type": "image/png", "data_uri": f"data:image/png;base64,{encoded_png}"},
        transport=lambda body: {"ocr_text": body["task"], "object_labels": ["diagram"], "model": "vision"},
    )
    assert inspected["ocr_text"] == "content_inspection"
    with pytest.raises(ValueError, match="declared type"):
        lw.prepare_content_inspection_asset({"mime_type": "image/png", "data_uri": "data:image/png;base64,Zm9v"})
    with pytest.raises(ValueError, match="unsupported"):
        lw.prepare_content_inspection_asset({"mime_type": "image/svg+xml", "data_uri": "data:image/svg+xml;base64,Zm9v"})


def test_malformed_source_rows_and_live_model_payloads_fail_closed(monkeypatch) -> None:
    """Keep corrupt exports and model bodies from becoming trusted product data."""
    assert lw._parse_datetime(None, "10:00") is None
    assert lw._parse_datetime("2026-04-01", None).isoformat() == "2026-04-01T00:00:00"
    assert lw._parse_datetime("2026-04-01", "10:00").isoformat() == "2026-04-01T10:00:00"
    assert lw._parse_datetime("not-a-date", "10:00") is None

    base = {
        "guid_field": "g-1",
        "docnosub_field": "DOC-1",
        "acthguid_field": "thread-1",
        "aedat_field": "not-a-date",
        "aezet_field": "10:00",
        "source_row_number": "not-an-int",
        "content_bytes": "not-a-size",
        "content_prefix": "data:image/png;base64,AAAA",
        "content_has_inline_image": "true",
        "artifact_reference": "false",
        "bukrs_field": "CORP-A",
        "pucode_field": "PU-A",
    }
    rows = lw._build_rows([{**base, "guid_field": ""}, base])
    assert len(rows) == 1
    assert rows[0].timestamp is None
    assert rows[0].source_row_number == 0
    assert rows[0].content_bytes == 0
    assert rows[0].content_kind == lw.CONTENT_INLINE_IMAGE

    assert lw._image_has_expected_signature("image/jpeg", b"\xff\xd8\xfffixture")
    assert lw._image_has_expected_signature("image/gif", b"GIF89afixture")
    assert lw._image_has_expected_signature("image/webp", b"RIFF....WEBPfixture")
    assert not lw._image_has_expected_signature("image/png", b"not-a-png")
    with pytest.raises(ValueError, match="invalid inline image data"):
        lw.prepare_content_inspection_asset({"mime_type": "image/png", "data_uri": "data:image/png;base64"})
    with pytest.raises(ValueError, match="invalid inline image base64"):
        lw.prepare_content_inspection_asset({"mime_type": "image/png", "data_uri": "data:image/png;base64,%%%"})
    monkeypatch.setattr(lw, "MAX_VISION_REQUEST_BYTES", 0)
    with pytest.raises(ValueError, match="exceeds"):
        lw.prepare_content_inspection_asset(
            {"mime_type": "image/png", "data_uri": "data:image/png;base64,iVBORw0KGgo="}
        )

    with pytest.raises(ValueError, match="must be an object"):
        lw.normalize_content_inspection_response([])
    assert lw.normalize_content_inspection_response({"labels": "  Chart  "})["object_labels"] == [
        {"label": "Chart", "description": ""}
    ]
    assert lw.normalize_content_inspection_response({"objects": 7})["object_labels"] == []
    monkeypatch.setattr(lw, "MAX_OBJECT_LABELS", 1)
    assert lw.normalize_content_inspection_response({"labels": ["one", "two"]})["object_labels"] == [
        {"label": "one", "description": ""}
    ]

    with pytest.raises(RuntimeError, match="empty answer"):
        lw.normalize_event_chat_response({}, [{"guid": "visible"}], "DOC-1")
    fallback = lw.normalize_event_chat_response(
        {"content": "observed", "citations": ["invalid", {"guid": "hidden"}, {"source_guid": "visible"}]},
        [{"guid": "visible", "event": "opened"}, "not-an-event"],
        "DOC-1",
    )
    assert fallback["evidence_ids"] == ["visible"]

    parsed = lw.parse_appointment_llm_response(
        {"appointments": ["2026-05-03 고객 미팅", None, {"excerpt": "2026-05-04 방문 약속"}, {}, {"date": "2026년 5월 5일"}]}
    )
    assert [item["occurred_on"] for item in parsed] == ["2026-05-03", "2026-05-04", "2026-05-05"]
    assert lw._normalize_appointment_date("no date", today=lw.datetime(2026, 5, 1, tzinfo=lw.timezone.utc)) == "2026-05-01"
    assert lw.unwrap_product_llm_object(None) == {}
    assert lw.unwrap_product_llm_object({"todo_body": "already structured"})["todo_body"] == "already structured"
    assert lw.unwrap_product_llm_object(
        {"choices": [{"message": {"content": "prefix {\"calendar_body\": \"review\"} suffix"}}]}
    ) == {"calendar_body": "review"}


def test_gateway_queue_and_evidence_adapters_preserve_failure_semantics(monkeypatch) -> None:
    """Exercise malformed live connectors without substituting synthetic decisions."""
    class _Socket:
        def __init__(self, payload: bytes) -> None:
            self.stream = io.BytesIO(payload)

        def recv(self, size: int) -> bytes:
            return self.stream.read(size)

    class _RawResponse:
        def __init__(self, value: object) -> None:
            self.value = value

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def read(self) -> bytes:
            return json.dumps(self.value).encode("utf-8")

    monkeypatch.delenv("LLM_GATEWAY_CA_BUNDLE", raising=False)
    context = lw.verified_gateway_ssl_context()
    assert context.verify_mode == lw.ssl.CERT_REQUIRED
    monkeypatch.setenv("LLM_GATEWAY_CA_BUNDLE", "/missing/operator-ca.pem")
    with pytest.raises(RuntimeError, match="not usable"):
        lw.verified_gateway_ssl_context()
    monkeypatch.delenv("LLM_GATEWAY_CA_BUNDLE")

    assert lw._valkey_read_reply(_Socket(b"+PONG\r\n")) == "PONG"
    assert lw._valkey_read_reply(_Socket(b":12\r\n")) == "12"
    assert lw._valkey_read_reply(_Socket(b"$3\r\nabc\r\n")) == b"abc"
    assert lw._valkey_read_reply(_Socket(b"$-1\r\n")) is None
    with pytest.raises(RuntimeError, match="valkey_error"):
        lw._valkey_read_reply(_Socket(b"-ERR denied\r\n"))
    with pytest.raises(RuntimeError, match="invalid_bulk"):
        lw._valkey_read_reply(_Socket(b"$1\r\naXX"))
    with pytest.raises(RuntimeError, match="unsupported"):
        lw._valkey_read_reply(_Socket(b"*1\r\n"))

    parsed = lw.parse_factor_item_responses(
        {"item_scores": {"i-yes": "yes", "i-no": 0, "ignored": "unclear"}},
        [{"item_id": "i-no"}, {"item_id": "i-yes"}, {"item_id": "missing"}],
    )
    assert parsed == [{"item_id": "i-no", "response": 0}, {"item_id": "i-yes", "response": 1}]
    assert lw.parse_factor_item_responses({"items": [None, {"item_id": "", "response": 1}]}, []) == []
    assert lw.parse_dichotomous_judge({"score": "YES", "reason": "grounded"})["verdict"] == "pass"
    with pytest.raises(ValueError, match="requires_pass"):
        lw.parse_dichotomous_judge({"verdict": "maybe"})
    with pytest.raises(ValueError, match="must_not_be_labeled_live"):
        lw.parse_dichotomous_judge({"verdict": "pass", "source": "recorded_same_path", "live": True})

    verification = lw.normalize_ontology_relationship_verification(
        {"decision": "verified", "confidence": "not-a-number", "evidence_ids": ["allowed", "allowed", "hidden"]},
        ["allowed"],
    )
    assert verification["decision"] == "verified"
    assert verification["confidence"] == 0.0
    assert verification["evidence_ids"] == ["allowed"]
    assert lw.normalize_ontology_relationship_verification({"decision": "verified"}, [])["decision"] == "insufficient"

    monkeypatch.delenv("LINEAGEWEAVE_SEARXNG_URL", raising=False)
    assert lw._searxng_search_url() == ""
    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "http://user:pass@localhost:18888")
    with pytest.raises(RuntimeError, match="invalid"):
        lw._searxng_search_url()
    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "http://localhost:18888")
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    assert lw._searxng_search_url() == "http://localhost:18888"
    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "http://searxng:8080")
    assert lw._searxng_search_url() == "http://searxng:8080"
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://localhost:23119/api")
    assert lw.zotero_local_api_url() == "http://localhost:23119/api"
    assert lw.probe_zotero_local_api(transport=lambda *_args: {"status_code": 204})["status"] == "reachable"
    assert lw.probe_zotero_local_api(transport=lambda *_args: {"status_code": 503})["status"] == "unreachable"
    assert lw.probe_zotero_local_api(transport=lambda *_args: (_ for _ in ()).throw(OSError("offline")))["status"] == "unreachable"

    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([_RawResponse({"choices": [{"message": {"content": "prefix {\"answer\": \"ok\"} suffix"}}]})]),
    )
    assert lw._post_chat_completion_json(
        {"task": "fixture"}, base_url="https://gateway.example", token="fixture", model="model", system_prompt="system", timeout=1
    ) == {"answer": "ok", "model": "model"}
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_http_error(429)]))
    assert lw._post_chat_completion_json(
        {"task": "fixture"}, base_url="https://gateway.example", token="fixture", model="model", system_prompt="system", timeout=1
    ) == {"model": "model", "abstention": "rate_limited"}
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_http_error(500)]))
    with pytest.raises(urllib.error.HTTPError):
        lw._post_chat_completion_json(
            {"task": "fixture"}, base_url="https://gateway.example", token="fixture", model="model", system_prompt="system", timeout=1
        )
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_http_error(500)]))
    with pytest.raises(RuntimeError, match="keyman HTTP 500"):
        lw.post_keyman_http({}, base_url="https://gateway.example", token="fixture")
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([
            _http_error(404),
            _RawResponse({"choices": [{"message": {"content": "{\"our_side\": [], \"counterpart_side\": []}"}}]}),
        ]),
    )
    assert lw.post_keyman_http({}, base_url="https://gateway.example", token="fixture") == {
        "our_side": [], "counterpart_side": [], "model": "gpt-4.1-mini"
    }
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([_http_error(429), _http_error(429)]),
    )
    assert lw.post_keyman_http({}, base_url="https://gateway.example", token="fixture") == {
        "model": "gpt-4.1-mini",
        "abstention": "rate_limited",
    }


def test_live_content_transport_uses_direct_gateway_and_never_a_compose_substitute(monkeypatch) -> None:
    """A configured image model adapter keeps its real endpoint and task envelope."""
    received: list[dict[str, object]] = []
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://gateway.example")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "fixture-key")
    monkeypatch.setenv("KEYMAN_MODEL", "fixture-vision")
    monkeypatch.setattr(lw, "load_runtime_env", lambda path=None: None)
    monkeypatch.setattr(
        lw,
        "post_content_inspection_http",
        lambda body, **kwargs: received.append({"body": body, **kwargs}) or {"ocr_text": "observed"},
    )
    transport = lw.make_live_content_inspection_transport()
    assert transport.__name__ == "live_content_inspection_http_transport"
    assert transport({"task": "content_inspection"}) == {"ocr_text": "observed"}
    assert received == [{
        "body": {"task": "content_inspection"},
        "base_url": "https://gateway.example",
        "token": "fixture-key",
        "model": "fixture-vision",
        "timeout": 120,
    }]


def test_corpus_content_inspection_sweep_covers_live_failure_and_offline_paths(monkeypatch) -> None:
    """Materialize ordered content and count every eligible corpus-inspection outcome."""
    queries: list[tuple[str, tuple[object, ...]]] = []

    def query(_connection, statement, params=()):  # noqa: ANN001
        queries.append((statement, tuple(params)))
        if "SELECT DISTINCT" in statement:
            return [{"document_no": "DOC-1"}, {"document_no": ""}]
        return [{"guid_field": "GUID-1", "source_row_number": "7", "voccts_field": "body"}]

    monkeypatch.setattr(lw, "_database_query", query)
    assert lw.resolve_content_document_numbers(object(), "schema.source_rows", document_limit=1) == ["DOC-1"]
    assert "LIMIT 1" in queries[-1][0]
    assert lw.resolve_content_document_numbers(object(), "schema.source_rows") == ["DOC-1"]
    assert "LIMIT" not in queries[-1][0]
    assert lw.resolve_content_document_records(object(), "schema.source_rows", "DOC-1")[0]["guid_field"] == "GUID-1"
    assert queries[-1][1] == ("DOC-1",)
    with pytest.raises(ValueError, match="invalid table"):
        lw.resolve_content_document_numbers(object(), "schema.source_rows;drop")

    structures = iter(
        [
            {
                "blocks": [{"block_kind": "text", "source_position": 1}],
                "assets": [{"mime_type": "image/png", "inspection_eligible": True}],
            },
            {
                "blocks": [],
                "assets": [{"mime_type": "text/plain", "inspection_eligible": False}],
            },
        ]
    )
    monkeypatch.setattr(lw, "extract_content_structure", lambda _value: next(structures))
    structure = lw.build_document_content_structure(
        [
            {"guid_field": "", "source_row_number": "7", "voccts_field": "first"},
            {"guid_field": "GUID-2", "source_row_number": "8", "voccts_field": "second"},
        ]
    )
    assert structure["blocks"][0]["source_evidence_id"] == "7"
    assert [asset["asset_index"] for asset in structure["assets"]] == [0, 1]
    assert structure["assets"][1]["source_evidence_id"] == "GUID-2"

    live_transport = lambda _body: {"ocr_text": "live"}
    monkeypatch.setattr(lw, "make_live_content_inspection_transport", lambda: live_transport)
    assert lw.resolve_content_inspection_transport() == (live_transport, "live_http")
    monkeypatch.setattr(
        lw,
        "make_live_content_inspection_transport",
        lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    monkeypatch.setattr(lw, "ensure_compose_standin", lambda: None)
    assert lw.resolve_content_inspection_transport() == (lw.compose_standin_transport, "compose_live_proxy")
    monkeypatch.setattr(
        lw,
        "ensure_compose_standin",
        lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert lw.resolve_content_inspection_transport() == (None, "unavailable")

    monkeypatch.setattr(lw, "resolve_content_document_numbers", lambda *_args, **_kwargs: ["DOC-1"])
    monkeypatch.setattr(lw, "resolve_content_document_records", lambda *_args, **_kwargs: [])
    sweep_structure = {
        "blocks": [{"block_index": 0}],
        "assets": [
            {"asset_index": 0, "inspection_eligible": False},
            {"asset_index": 1, "inspection_eligible": True, "source_evidence_id": "EV-1"},
            {"asset_index": 2, "inspection_eligible": True, "source_evidence_id": "EV-2"},
        ],
    }
    monkeypatch.setattr(lw, "build_document_content_structure", lambda _records: sweep_structure)
    persisted: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        lw,
        "persist_document_content_structure",
        lambda *args: persisted.append(("structure", *args[1:])),
    )
    monkeypatch.setattr(
        lw,
        "persist_content_inspection",
        lambda *args: persisted.append(("inspection", *args[1:])),
    )
    monkeypatch.setattr(
        lw,
        "derive_content_inspection_via_llm",
        lambda asset, transport: transport(asset),
    )

    def inspect(asset):  # noqa: ANN001
        if asset["asset_index"] == 2:
            raise RuntimeError("model failure")
        return {"ocr_text": "observed", "object_labels": []}

    summary = lw.sweep_content_inspections(
        object(),
        "schema.source_rows",
        document_limit=1,
        inspected_by="account-1",
        transport=inspect,
        transport_name="live_http",
    )
    assert summary == {
        "document_count": 1,
        "content_block_rows": 1,
        "content_asset_rows": 3,
        "inspection_candidates": 2,
        "inspected_asset_count": 1,
        "failed_inspection_count": 1,
        "skipped_inspection_count": 0,
        "transport": "live_http",
    }
    assert [row[0] for row in persisted] == ["structure", "inspection"]

    monkeypatch.setattr(lw, "resolve_content_inspection_transport", lambda: (None, "unavailable"))
    monkeypatch.setattr(
        lw,
        "build_document_content_structure",
        lambda _records: {"blocks": [], "assets": [{"asset_index": 0, "inspection_eligible": True}]},
    )
    offline = lw.sweep_content_inspections(object(), "schema.source_rows")
    assert offline["skipped_inspection_count"] == 1
    assert offline["transport"] == "unavailable"


def test_llm_timeout_and_optional_transport_contracts_fail_closed(monkeypatch) -> None:
    """Clamp operator timeouts and report unavailable live transports explicitly."""
    monkeypatch.delenv("LINEAGEWEAVE_TIMEOUT_FIXTURE", raising=False)
    assert lw.resolve_llm_timeout("LINEAGEWEAVE_TIMEOUT_FIXTURE", default=7) == 7
    monkeypatch.setenv("LINEAGEWEAVE_TIMEOUT_FIXTURE", "not-an-int")
    assert lw.resolve_llm_timeout("LINEAGEWEAVE_TIMEOUT_FIXTURE", default=7) == 7
    monkeypatch.setenv("LINEAGEWEAVE_TIMEOUT_FIXTURE", "0")
    assert lw.resolve_llm_timeout("LINEAGEWEAVE_TIMEOUT_FIXTURE", default=7, minimum=2) == 2
    monkeypatch.setenv("LINEAGEWEAVE_TIMEOUT_FIXTURE", "999")
    assert lw.resolve_llm_timeout("LINEAGEWEAVE_TIMEOUT_FIXTURE", default=7, maximum=11) == 11

    monkeypatch.delenv("LINEAGEWEAVE_RUNTIME_FIXTURE", raising=False)
    assert lw.resolve_runtime_int("LINEAGEWEAVE_RUNTIME_FIXTURE", default=7) == 7
    monkeypatch.setenv("LINEAGEWEAVE_RUNTIME_FIXTURE", "not-an-int")
    assert lw.resolve_runtime_int("LINEAGEWEAVE_RUNTIME_FIXTURE", default=7) == 7
    monkeypatch.setenv("LINEAGEWEAVE_RUNTIME_FIXTURE", "-1")
    assert lw.resolve_runtime_int("LINEAGEWEAVE_RUNTIME_FIXTURE", default=7, minimum=2) == 2
    monkeypatch.setenv("LINEAGEWEAVE_RUNTIME_FIXTURE", "999")
    assert lw.resolve_runtime_int("LINEAGEWEAVE_RUNTIME_FIXTURE", default=7, maximum=11) == 11

    def unavailable():
        """Raise the same boundary error as an unset live gateway."""
        raise RuntimeError("gateway unavailable")

    monkeypatch.setattr(lw, "make_live_keyman_transport", unavailable)
    monkeypatch.setattr(lw, "make_live_product_transport", unavailable)
    monkeypatch.setattr(lw, "ensure_compose_standin", lambda: "compose_started")
    assert lw.resolve_keyman_transport_optional() == (lw.compose_standin_transport, "compose_live_proxy")
    monkeypatch.setattr(
        lw,
        "ensure_compose_standin",
        lambda: (_ for _ in ()).throw(RuntimeError("gateway unavailable")),
    )
    assert lw.resolve_keyman_transport_optional() == (None, "gateway unavailable")
    assert lw.resolve_product_transport_optional() == (None, "gateway unavailable")

    monkeypatch.setattr(lw, "ensure_compose_standin", lambda: "compose_started")
    assert lw.resolve_product_transport_optional() == (lw.compose_standin_transport, "compose_live_proxy")


def test_urlread_timeout_uses_the_request_socket_deadline(monkeypatch) -> None:
    """A timed-out gateway read returns immediately without waiting on an executor thread."""
    captured: dict[str, object] = {}

    def timed_out(request, *, timeout, context):  # noqa: ANN001
        captured.update({"request": request, "timeout": timeout, "context": context})
        raise TimeoutError("socket deadline")

    monkeypatch.setattr(lw.urllib.request, "urlopen", timed_out)
    with pytest.raises(TimeoutError, match="socket deadline"):
        lw._urlread_with_timeout(lw.urllib.request.Request("https://gateway.example"), timeout=1)
    assert captured["timeout"] == 1
    assert captured["context"] is None


def test_zotero_response_provenance_and_nested_attachment_keys_are_preserved() -> None:
    """Keep connector digests and nested attachment keys auditable."""
    paper = {**lw.OA_METHOD_PAPERS[0], "full_text": "bounded source text"}
    stored = lw.store_oa_method_paper(
        paper,
        transport=lambda _payload: {
            "status_code": 201,
            "body": {"key": "LOCAL-ITEM", "contentDigest": "source-digest", "successful": {"0": {"attachment": {"attachmentKey": "LOCAL-ATTACHMENT"}}}},
        },
    )
    assert stored["content_digest"] == "source-digest"
    assert stored["zotero_attachment_key"] == "LOCAL-ATTACHMENT"
    assert lw._extract_first_string(None, ["attachmentKey"]) is None
    assert lw._extract_first_string({"missing": None, "attachmentKey": "found"}, ["attachmentKey"]) == "found"
    assert lw._extract_first_string({"attachmentKey": None, "nested": {"attachmentKey": "nested"}}, ["attachmentKey"]) == "nested"
    assert lw._extract_first_string({}, ["attachmentKey"]) is None
    assert lw._extract_first_string([], ["attachmentKey"]) is None
    assert lw._extract_first_string(42, ["attachmentKey"]) is None
    assert lw._extract_first_string((None, "found"), ["attachmentKey"]) == "found"
    assert lw._extract_first_string((None, ""), ["attachmentKey"]) is None
    assert lw._extract_first_string(
        {"attachmentKey": "", "nested": [None, ""]}, ["attachmentKey"]
    ) is None


def test_dom_structure_keeps_semantic_units_and_layout_without_raw_markup_or_bytes() -> None:
    """Split realistic formatted HTML into safe DB-ready blocks and asset profiles."""
    encoded_png = base64.b64encode(b"\x89PNG\r\n\x1a\nfixture").decode("ascii")
    source = (
        '<section><p align="right"><span style="color: #224488; font-size: 15px">'
        f'납기 협의</span></p><ul><li style="font-weight: 700">다음 주 확인</li></ul>'
        f'<img src="data:image/png;base64,{encoded_png}"></section>'
    )
    structure = lw.extract_content_structure(source)
    blocks = structure["blocks"]
    assert [block["block_kind"] for block in blocks] == ["paragraph", "list_item"]
    assert blocks[0]["source_position"] == source.index("<p")
    assert {tuple(hint.items()) for hint in blocks[0]["format_hints"]} >= {
        (("hint_kind", "text_align"), ("hint_value", "right")),
        (("hint_kind", "color"), ("hint_value", "#224488")),
        (("hint_kind", "font_size"), ("hint_value", "15px")),
    }
    assert {tuple(hint.items()) for hint in blocks[1]["format_hints"]} >= {
        (("hint_kind", "font_weight"), ("hint_value", "700")),
        (("hint_kind", "list_marker"), ("hint_value", "bullet")),
    }
    asset = structure["assets"][0]
    assert asset["mime_type"] == "image/png"
    assert asset["source_position"] == source.index("data:image/png")
    assert asset["inspection_eligible"] is True
    assert "data_uri" not in asset
    assert "data:image" not in json.dumps(structure)
    assert encoded_png not in json.dumps(structure)
    assert lw.extract_inline_assets("data:application/pdf;base64,QUJD")[0]["inspection_eligible"] is False


def test_persisted_content_structure_keeps_large_inline_images_eligible_without_bytes(monkeypatch) -> None:
    """Refresh old metadata eligibility without selecting a large data URI from PostgreSQL."""
    query_texts: list[str] = []

    assert lw.is_content_inspection_eligible("image/png", 40 * 1024 * 1024) is True
    assert lw.is_content_inspection_eligible("image/png", 100 * 1024 * 1024) is False
    assert lw.is_content_inspection_eligible("text/plain", 40 * 1024 * 1024) is False
    assert lw.is_content_inspection_eligible("image/png", "not-a-size") is False

    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)

    def query(_connection, sql, params=()):
        query_texts.append(sql)
        assert params == ("DOC-40M",)
        if "FROM analysis_content_blocks" in sql:
            return [
                {
                    "block_index": 0,
                    "source_evidence_id": "evidence-1",
                    "source_row_number": "17",
                    "block_kind": "paragraph",
                    "source_position": 41,
                    "text_content": "납기 협의",
                    "text_sha256": "a" * 64,
                }
            ]
        if "FROM analysis_content_format_hints" in sql:
            return [{"block_index": 0, "hint_kind": "font_weight", "hint_value": "700"}]
        return [
            {
                "asset_index": 0,
                "source_evidence_id": "evidence-1",
                "source_row_number": "17",
                "source_position": 118,
                "mime_type": "image/png",
                "encoded_bytes": 40 * 1024 * 1024,
                "content_kind": lw.CONTENT_INLINE_IMAGE,
                "asset_sha256": "b" * 64,
                "inspection_eligible": False,
            }
        ]

    monkeypatch.setattr(lw, "_database_query", query)
    structure = lw.load_document_content_structure(object(), "DOC-40M")

    assert structure["blocks"][0]["source_position"] == 41
    assert structure["blocks"][0]["format_hints"] == [{"hint_kind": "font_weight", "hint_value": "700"}]
    assert structure["assets"] == [
        {
            "asset_index": 0,
            "source_evidence_id": "evidence-1",
            "source_row_number": "17",
            "source_position": 118,
            "mime_type": "image/png",
            "encoded_bytes": 40 * 1024 * 1024,
            "content_kind": lw.CONTENT_INLINE_IMAGE,
            "asset_sha256": "b" * 64,
            "inspection_eligible": True,
        }
    ]
    assert all("data_uri" not in sql and "encoded_data" not in sql for sql in query_texts)

    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, table: table != lw.ANALYSIS_CONTENT_ASSET_TABLE)
    assert lw.load_document_content_structure(object(), "DOC-40M") == {"blocks": [], "assets": []}


def test_content_structure_preserves_visible_malformed_dom_without_inline_bytes() -> None:
    """Keep visible DOM order and layout hints while dropping markup and ignored content."""
    structure = lw.extract_content_structure(
        "outside "
        '<p align="center" style="font-weight:700;color:#111">'
        'Visible <strong>text</strong><img src="data:image/png;base64,AAAA"></p>'
        "<ul><li>First item</li></ul>"
        "<script>ignored script text</script>"
        '<p style="font-size:14px">Unfinished'
    )

    assert [(block["block_kind"], block["text_content"]) for block in structure["blocks"]] == [
        ("text", "outside"),
        ("paragraph", "Visible text"),
        ("list_item", "First item"),
        ("paragraph", "Unfinished"),
    ]
    assert structure["blocks"][1]["format_hints"] == [
        {"hint_kind": "text_align", "hint_value": "center"},
        {"hint_kind": "font_weight", "hint_value": "700"},
        {"hint_kind": "color", "hint_value": "#111"},
    ]
    assert structure["blocks"][2]["format_hints"] == [
        {"hint_kind": "list_marker", "hint_value": "bullet"}
    ]
    assert structure["blocks"][3]["format_hints"] == [
        {"hint_kind": "font_size", "hint_value": "14px"}
    ]
    assert all("data:image" not in str(block) for block in structure["blocks"])
    assert all("ignored script text" not in block["text_content"] for block in structure["blocks"])


def test_customer_master_normalizes_malformed_duplicate_llm_rows_without_losing_evidence() -> None:
    """Accept common LLM shape drift but reject role labels as customer organizations."""
    customer_master = lw.parse_customer_master_response(
        {
            "customers": [
                "시장",
                "Northwind",
                {
                    "name": "Northwind UK",
                    "tier": "country",
                    "parent": "Northwind",
                    "document_nos": "DOC-A",
                },
                {
                    "account_name": "Northwind UK",
                    "tier": "head office",
                    "document_nos": ["DOC-B", "DOC-A"],
                },
                {"account_name": "", "parent_name": "Northwind"},
                {"account_name": "Blocked", "parent_name": "고객"},
                42,
            ],
            "edges": [
                "not-an-edge",
                {
                    "parent": "Northwind",
                    "child": "Northwind UK",
                    "document_nos": "DOC-C",
                },
                {
                    "parent": "Northwind",
                    "child": "Northwind UK",
                    "document_nos": ["DOC-D", "DOC-C"],
                },
                {"parent": "고객", "child": "Northwind UK", "document_nos": ["DOC-X"]},
            ],
        }
    )

    accounts = {account["account_name"]: account for account in customer_master["accounts"]}
    assert set(accounts) == {"Northwind", "Northwind UK", "Blocked"}
    assert accounts["Northwind UK"]["tier"] == "national"
    assert accounts["Northwind UK"]["parent_name"] == "Northwind"
    assert accounts["Northwind UK"]["document_nos"] == ["DOC-A", "DOC-B"]
    assert accounts["Blocked"]["parent_name"] == ""
    edge = next(
        edge
        for edge in customer_master["edges"]
        if edge["parent"] == "Northwind" and edge["child"] == "Northwind UK"
    )
    assert edge["document_nos"] == ["DOC-C", "DOC-D"]
    assert customer_master["source"] == "llm"


def test_inline_asset_profiles_bound_repeated_images_and_keep_private_handles_optional() -> None:
    """Keep adversarially dense inline media bounded without leaking byte handles into metadata."""
    repeated_image = "data:image/png;base64,AA=="
    bounded = lw.extract_inline_assets(
        " ".join([repeated_image] * (lw.MAX_CONTENT_ASSETS_PER_SOURCE + 1)),
        include_data_uri=False,
    )
    assert len(bounded) == lw.MAX_CONTENT_ASSETS_PER_SOURCE
    assert all("data_uri" not in asset for asset in bounded)
    assert lw.extract_inline_assets("<svg><text>safe</text></svg>", include_data_uri=False)[0]["mime_type"] == "image/svg+xml"
    bounded_svg = lw.extract_inline_assets(
        " ".join(["<svg><text>safe</text></svg>"] * (lw.MAX_CONTENT_ASSETS_PER_SOURCE + 1)),
        include_data_uri=False,
    )
    assert len(bounded_svg) == lw.MAX_CONTENT_ASSETS_PER_SOURCE
    opaque_base64 = "A" * 256
    assert lw.classify_content_kind(f"prefix data:application/octet-stream;base64,{opaque_base64}") == lw.CONTENT_INLINE_BINARY
    assert lw.extract_inline_assets(opaque_base64, include_data_uri=False)[0]["mime_type"] == "application/octet-stream"
    assert lw._safe_visible_fragment(opaque_base64) == ""


def test_content_and_dag_boundary_validation_rejects_untrusted_shapes(monkeypatch) -> None:
    """Reject malformed private assets, unsafe table names, and non-standard evidence states."""
    with pytest.raises(ValueError, match="invalid inline asset data"):
        lw.content_asset_sha256({})
    with pytest.raises(ValueError, match="unknown evidence_status"):
        lw.make_lineage_edge(
            source="doc:A",
            target="doc:B",
            relation="shared_topic",
            reason="fixture",
            evidence_status="fabricated",
        )
    with pytest.raises(ValueError, match="invalid table identifier"):
        lw.resolve_source_table("public.safe_rows; DROP TABLE analysis_document_nodes")
    monkeypatch.delenv("LINEAGE_SOURCE_TABLE", raising=False)
    with pytest.raises(RuntimeError, match="set --table"):
        lw.resolve_source_table()


def test_customer_ladder_preserves_direct_edge_evidence_when_inserting_hierarchy() -> None:
    """Keep the observed direct relationship evidence when expanding a group-to-plant ladder."""
    customer_master = lw.parse_customer_master_response(
        {
            "customers": [
                {"name": "Acme Group", "tier": "group", "document_nos": ["DOC-PARENT"]},
                {"name": "Acme Group Plant", "tier": "plant", "document_nos": ["DOC-PLANT"]},
            ],
            "edges": [
                {
                    "parent": "Acme Group",
                    "child": "Acme Group Plant",
                    "relation": "customer_affiliate",
                    "document_nos": ["DOC-DIRECT"],
                }
            ],
        }
    )

    assert customer_master["parent_of"]["Acme Group Korea"] == "Acme Group"
    assert customer_master["parent_of"]["Acme Group HQ"] == "Acme Group Korea"
    assert customer_master["parent_of"]["Acme Group Plant"] == "Acme Group HQ"
    assert "Acme Group Plant" not in {
        edge["child"] for edge in customer_master["edges"] if edge["parent"] == "Acme Group"
    }
    ladder_edges = [
        edge
        for edge in customer_master["edges"]
        if edge["parent"] in {"Acme Group", "Acme Group Korea", "Acme Group HQ"}
    ]
    assert all("DOC-DIRECT" in edge["document_nos"] for edge in ladder_edges)


def test_customer_ladder_merges_shared_hierarchy_evidence_without_rewriting_complete_or_misclassified_paths() -> None:
    """Preserve every observed document while completing only genuinely missing plant paths."""
    source = {
        "source": "llm",
        "accounts": [
            {"account_name": "Acme Group", "tier": "group", "document_nos": ["DOC-GROUP"]},
            {"account_name": "Acme Group Plant One", "tier": "plant", "document_nos": ["DOC-ONE"]},
            {"account_name": "Acme Group Plant Two", "tier": "plant", "document_nos": ["DOC-TWO"]},
        ],
        "edges": [
            {"parent": "Acme Group", "child": "Acme Group Plant One", "document_nos": ["DOC-ONE"]},
            {"parent": "Acme Group", "child": "Acme Group Plant Two", "document_nos": ["DOC-TWO"]},
        ],
    }
    completed = lw.complete_customer_master_ladder(source)
    root_edge = next(
        edge
        for edge in completed["edges"]
        if edge["parent"] == "Acme Group" and edge["child"] == "Acme Group Korea"
    )
    assert root_edge["document_nos"] == ["DOC-GROUP", "DOC-ONE", "DOC-TWO"]
    assert lw.complete_customer_master_ladder(completed) == completed

    misclassified = lw.complete_customer_master_ladder(
        {
            "accounts": [{"account_name": "Contoso Korea", "tier": "plant"}],
            "edges": [{"parent": "Contoso", "child": "Contoso Korea", "document_nos": ["DOC-BAD"]}],
        }
    )
    assert misclassified["parent_of"] == {"Contoso Korea": "Contoso"}
    assert "Contoso HQ" not in misclassified["nodes"]


def test_product_enrichment_routes_issue_appointment_and_keyman_to_separate_llm_tasks() -> None:
    """Fill popup operations from task-specific model responses without mixing Keyman sides."""
    product_tasks: list[str] = []
    keyman_sides: list[str] = []

    def product_transport(body: dict) -> dict:
        product_tasks.append(body["task"])
        if body["task"] == "entity_role_classification":
            return {"entity_role": "고객", "confidence": 0.91, "rationale": "고객 납기 이슈"}
        if body["task"] == "roles_and_responsibilities":
            return {
                "roles_and_responsibilities": [
                    {
                        "actor_type": "organization",
                        "actor_name": "Customer Authority",
                        "role": "승인 기관",
                        "responsibility": "기술 승인",
                    }
                ]
            }
        if body["task"] == "issue_work_items":
            assert body["document_no"] == "DOC-1"
            return {
                "todo_body": "Confirm delivery owner",
                "calendar_body": "Schedule customer review",
                "due_on": "2026/09/01",
            }
        assert body["task"] == "appointment_extract"
        return {"appointments": [{"date": "2026.09.02", "excerpt": "Customer review meeting"}]}

    def keyman_transport(body: dict) -> dict:
        keyman_sides.append(body["extract_side"])
        if body["extract_side"] == "our_side":
            return {"our_side": [{"name": "Kim", "org": "Delivery Team"}], "model": "fixture-keyman"}
        return {"counterpart_side": [{"name": "Park", "org": "Customer Group"}], "model": "fixture-keyman"}

    document = {
        "document_no": "DOC-1",
        "title_sample": "고객 납기 이슈 미팅",
        "first_stage": "W",
        "first_status": "W",
        "first_event": "UPDATE",
        "first_row_ts": "2026-08-30T10:00:00Z",
        "corp_code": "CWL1",
        "owner_pu": "PU01",
        "created_by": "Kim",
        "changed_by": "Reviewer",
        "user_id": "Kim",
    }
    enriched = lw.attach_product_fields(
        document,
        enum_values={"entity_role": ["고객"]},
        product_transport=product_transport,
        keyman_transport=keyman_transport,
    )

    assert product_tasks == [
        "entity_role_classification",
        "roles_and_responsibilities",
        "issue_work_items",
        "appointment_extract",
    ]
    assert keyman_sides == ["our_side", "counterpart_side"]
    assert enriched["entity_role"] == "고객"
    assert enriched["entity_role_source"] == "llm"
    assert enriched["entity_role_confidence"] == 0.91
    assert enriched["issue_tickets"][0]["todo"]["source"] == "llm"
    assert enriched["issue_tickets"][0]["calendar"] == {
        "calendar_id": "cal-tkt-DOC-1",
        "ticket_id": "tkt-DOC-1",
        "document_no": "DOC-1",
        "title": "고객 납기 이슈 미팅",
        "body": "Schedule customer review",
        "occurred_on": "2026-09-01",
        "source": "llm",
    }
    assert enriched["appointments"][0]["occurred_on"] == "2026-09-02"
    assert enriched["appointments"][0]["document_no"] == "DOC-1"
    assert enriched["keyman_our_side"] == [{"person_name": "Kim", "org_name": "Delivery Team"}]
    assert enriched["keyman_counterpart_side"] == [{"person_name": "Park", "org_name": "Customer Group"}]
    assert enriched["keyman_source"] == "llm"


def test_entity_role_llm_alias_and_abstention_are_safe() -> None:
    """Normalize supported English aliases and reject roles outside common ENUM."""
    calls: list[dict[str, object]] = []

    def alias_transport(body: dict[str, object]) -> dict[str, object]:
        calls.append(body)
        return {"classification": "end customer", "confidence": "bad"}

    result = lw.derive_entity_role_via_llm(
        {"document_no": "DOC-ROLE", "title_sample": "delivery"},
        enum_values={"entity_role": ["고객의 고객", "시장"]},
        transport=alias_transport,
    )
    assert result["entity_role"] == "고객의 고객"
    assert result["source"] == "llm"
    assert result["confidence"] == 0.0
    assert calls[0]["allowed_entity_roles"] == ["고객의 고객", "시장"]

    rejected = lw.derive_entity_role_via_llm(
        {"document_no": "DOC-ROLE", "title_sample": "delivery"},
        enum_values={"entity_role": ["시장"]},
        transport=lambda _body: {"entity_role": "unknown", "confidence": 2},
    )
    assert rejected["entity_role"] == ""
    assert rejected["source"] == "llm_abstention"
    assert rejected["confidence"] == 1.0

    def unavailable(_body: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("gateway unavailable")

    failed = lw.derive_entity_role_via_llm(
        {"document_no": "DOC-ROLE", "title_sample": "delivery"},
        enum_values={"entity_role": ["시장"]},
        transport=unavailable,
    )
    assert failed["entity_role"] == ""
    assert failed["source"] == "llm_abstention"


def test_role_responsibility_llm_keeps_organization_agents_and_person_affiliations() -> None:
    """Model institutions as agents and retain evidence-marked person affiliations."""
    requests: list[dict] = []

    def transport(body: dict) -> dict:
        requests.append(body)
        return {
            "roles_and_responsibilities": [
                {
                    "actor_type": "organization",
                    "actor_name": "SEWA",
                    "role": "승인 기관",
                    "responsibility": "기술 승인",
                    "affiliation_status": "observed",
                },
                {
                    "actor_type": "person",
                    "actor_name": "Alex Kim",
                    "organization_name": "Siemens",
                    "rank": "Director",
                    "title": "Engineering Lead",
                    "role": "기술 담당자",
                    "responsibility": "설계 질의 회신",
                    "affiliation_status": "inferred",
                    "node": {"id": "person:alex", "type": "person"},
                    "entity": "engineering_case",
                    "relationship": "memberOf",
                    "direction": "outgoing",
                },
                {
                    "actor_type": "person",
                    "actor_name": "Alex Kim",
                    "organization_name": "Siemens",
                    "rank": "Senior Manager",
                    "title": "Approval Lead",
                    "role": "승인 담당자",
                    "responsibility": "설계 승인",
                    "affiliation_status": "inferred",
                },
            ]
        }

    rows = lw.derive_roles_and_responsibilities_via_llm(
        {
            "document_no": "DOC-1",
            "title_sample": "SEWA 기술 승인 및 Siemens 설계 회신",
            "first_stage": "W",
            "first_event": "UPDATE",
            "created_by": "Alex Kim",
        },
        transport=transport,
    )

    assert requests[0]["task"] == "roles_and_responsibilities"
    assert rows[0]["actor_type"] == "organization"
    assert rows[0]["agent_class_uri"] == "http://www.w3.org/ns/prov#Organization"
    assert rows[0]["organization_name"] == "SEWA"
    assert rows[0]["affiliation_property_uri"] == ""
    assert rows[1]["agent_class_uri"] == "http://www.w3.org/ns/prov#Person"
    assert rows[1]["organization_name"] == "Siemens"
    assert rows[1]["rank"] == "Director"
    assert rows[1]["title"] == "Engineering Lead"
    assert rows[1]["node"] == {"id": "person:alex", "type": "person"}
    assert rows[1]["entity"] == "engineering_case"
    assert rows[1]["relationship"] == "memberOf"
    assert rows[1]["direction"] == "outgoing"
    assert rows[1]["job_title_property_uri"] == "https://schema.org/jobTitle"
    assert rows[1]["membership_class_uri"] == "http://www.w3.org/ns/org#Membership"
    assert rows[1]["affiliation_property_uri"] == "http://www.w3.org/ns/org#memberOf"
    assert rows[1]["affiliation_status"] == "inferred"
    graph = lw.build_knowledge_graph(
        [
            {
                "id": "doc:DOC-1",
                "type": "document",
                "document_no": "DOC-1",
                "title_sample": "SEWA 기술 승인 및 Siemens 설계 회신",
                "roles_and_responsibilities": rows,
            }
        ],
        [],
    )
    assert {"organization", "person", "role", "membership", "attribution"} <= {
        node["type"] for node in graph["nodes"]
    }
    matching_people = [
        node for node in graph["nodes"] if node["type"] == "person" and node["label"] == "Alex Kim"
    ]
    assert len(matching_people) == 2
    assert len({node["id"] for node in matching_people}) == 2
    attribution = next(
        node for node in graph["nodes"]
        if node["type"] == "attribution" and node.get("semantic_context")
    )
    assert attribution["semantic_context"] == {
        "node": {"id": "person:alex", "type": "person"},
        "entity": "engineering_case",
        "relationship": "memberOf",
        "direction": "outgoing",
    }
    assert {
        "responsible_agent",
        "qualified_attribution",
        "attribution_agent",
        "attribution_role",
        "membership_member",
        "membership_organization",
        "membership_role",
    } <= {edge["relation"] for edge in graph["edges"]}
    qualified = [edge for edge in graph["edges"] if edge["relation"] == "qualified_attribution"]
    assert qualified and all(edge["source"].startswith("kg:document:") for edge in qualified)
    assert all(edge["target"].startswith("kg:attribution:") for edge in qualified)
    standards = {term["standard_uri"] for term in lw.semantic_layer_records(graph)["terms"]}
    assert "http://www.w3.org/ns/org#Membership" in standards
    assert "http://www.w3.org/ns/org#member" in standards
    assert "http://www.w3.org/ns/org#organization" in standards
    assert "http://www.w3.org/ns/org#role" in standards
    assert "http://www.w3.org/ns/prov#wasAttributedTo" in standards
    assert "http://www.w3.org/ns/prov#Attribution" in standards
    assert "http://www.w3.org/ns/prov#Role" in standards
    assert "http://www.w3.org/ns/prov#qualifiedAttribution" in standards
    assert "http://www.w3.org/ns/prov#agent" in standards
    assert "http://www.w3.org/ns/prov#hadRole" in standards


def test_meso_team_actor_is_not_an_organization() -> None:
    """A design-team label is a meso org:OrganizationalUnit with a parent company."""
    rows = lw.parse_roles_and_responsibilities_response(
        {
            "roles_and_responsibilities": [
                {
                    "actor_type": "organization",
                    "actor_name": "설계팀",
                    "organization_name": "한국수력원자력",
                    "role": "설계",
                    "responsibility": "계통 설계 검토",
                }
            ]
        },
        {"first_stage": "W"},
    )
    assert rows[0]["actor_type"] == "team"
    assert rows[0]["actor_name"] == "설계팀"
    assert rows[0]["affiliated_organization_name"] == "한국수력원자력"
    assert rows[0]["agent_class_uri"] == "http://www.w3.org/ns/org#OrganizationalUnit"
    assert rows[0]["affiliation_property_uri"] == "http://www.w3.org/ns/org#unitOf"


def test_organization_abbreviation_expands_from_searxng_evidence() -> None:
    """Short legal names expand from searched evidence, not from a hardcoded map."""
    evidence = [
        {
            "title": "한국수력원자력(한수원) 소개",
            "excerpt": "한수원은 원전 운영 공기업이다.",
            "source_uri": "https://example.test/khnp",
        }
    ]
    expanded = lw.expand_organization_abbreviation(
        "한수원",
        evidence=evidence,
        context="원전 설계 검토",
    )
    assert expanded["abbreviation"] == "한수원"
    assert expanded["canonical_name"] == "한국수력원자력"
    assert expanded["verification"] == "searxng"
    rows = lw.apply_organization_expansions(
        [
            {
                "actor_type": "organization",
                "actor_name": "한수원",
                "organization_name": "한수원",
                "role": "발주",
                "responsibility": "계약",
            }
        ],
        search=lambda _labels: {"mode": "searxng", "evidence": evidence},
    )
    assert rows[0]["organization_name"] == "한국수력원자력"
    assert rows[0]["expansion_verification"] == "searxng"


def test_organization_expansion_covers_empty_llm_and_search_boundaries(monkeypatch) -> None:
    """Keep abbreviation expansion evidence-bound across empty, LLM, and SearxNG paths."""
    assert lw.expand_organization_abbreviation("") == {
        "abbreviation": "",
        "canonical_name": "",
        "verification": "unchanged",
    }
    assert lw.expand_organization_abbreviation(
        "KHNP", llm_canonical="KHNP Korea Hydro & Nuclear Power"
    )["verification"] == "unchanged"
    assert lw.expand_organization_abbreviation(
        "KHNP",
        evidence=[{"title": "KHNP", "excerpt": "Korea Hydro Nuclear Power"}],
        llm_canonical="Korea Hydro Nuclear Power",
    )["verification"] == "searxng"
    assert lw.expand_organization_abbreviation(
        "KHNP", evidence=[{"title": "KHNP (Korea Hydro Nuclear Power)"}]
    )["canonical_name"] == "Korea Hydro Nuclear Power"
    assert lw.expand_organization_abbreviation("KHNP")["verification"] == "unchanged"

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "http://127.0.0.1:8888")
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "results": [
                    "invalid",
                    {"url": "file:///unsafe", "title": "unsafe", "content": "unsafe"},
                    {"url": "https://example.test/alias", "title": "KHNP", "content": "Korea Hydro & Nuclear Power"},
                ]
            }
        ),
    )
    result = lw.search_abbreviation_evidence("KHNP")
    assert result["mode"] == "searxng"
    assert result["evidence"][0]["source_uri"] == "https://example.test/alias"
    assert lw.search_abbreviation_evidence("")["mode"] == "not_configured"
    assert lw.apply_organization_expansions(
        [
            {"actor_type": "person", "actor_name": "Kim", "organization_name": "KHNP"},
            {"actor_type": "team", "actor_name": "Design Team", "organization_name": "KHNP"},
            {"actor_type": "organization", "organization_name": "KHNP"},
        ]
    )[0]["organization_name"] == "KHNP"


def test_organization_abbreviation_rejects_short_matches_and_search_failures(monkeypatch) -> None:
    """Keep too-short parenthetical matches and unavailable search results untrusted."""
    assert lw.expand_organization_abbreviation(
        "KHNP",
        evidence=[{"title": "ABC (KHNP) KHNP (XYZ)"}],
    ) == {"abbreviation": "KHNP", "canonical_name": "KHNP", "verification": "unchanged"}

    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")),
    )
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "http://127.0.0.1:8888")
    assert lw.search_abbreviation_evidence("KHNP")["mode"] == "unavailable"

    monkeypatch.setattr(lw.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response([]))
    assert lw.search_abbreviation_evidence("KHNP")["mode"] == "unavailable"

    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "results": [
                    {"url": f"https://example.test/{index}", "title": f"Result {index}", "content": "evidence"}
                    for index in range(6)
                ]
            }
        ),
    )
    assert len(lw.search_abbreviation_evidence("KHNP")["evidence"]) == 5


def test_organization_alias_helpers_fail_closed_and_preserve_existing_edges(monkeypatch) -> None:
    """Reject invalid aliases, normalize malformed model output, and avoid duplicate edges."""
    with pytest.raises(ValueError, match="at least two"):
        lw.search_external_organization_alias_evidence("A")
    monkeypatch.setattr(
        lw,
        "search_abbreviation_evidence",
        lambda alias: {"mode": "searxng", "query": alias, "evidence": [{"evidence_id": "e1"}]},
    )
    external = lw.search_external_organization_alias_evidence("AB", limit=99)
    assert external["evidence"][0]["evidence_kind"] == "external"
    normalized = lw.normalize_organization_alias_resolution(
        {"decision": "unknown", "canonical_name": "Canonical", "confidence": "bad"},
        "AB",
        [{"evidence_id": "e1", "evidence_kind": "external"}],
    )
    assert normalized["decision"] == "insufficient"
    assert normalized["confidence"] == 0.0
    graph, candidate = lw.attach_verified_organization_alias(
        {"nodes": [], "edges": []}, normalized, document_no="DOC-1"
    )
    assert graph == {"nodes": [], "edges": []}
    assert candidate["evidence_status"] == lw.EVIDENCE_INFERRED


def test_team_rr_handles_equal_actor_and_affiliation_labels() -> None:
    """Preserve the parent organization when a team label is supplied twice."""
    rows = lw.parse_roles_and_responsibilities_response(
        {
            "roles_and_responsibilities": [
                {
                    "actor_type": "team",
                    "actor_name": "설계팀",
                    "organization_name": "설계팀",
                    "affiliated_organization_name": "한국수력원자력",
                    "role": "설계",
                    "responsibility": "검토",
                }
            ]
        },
        {},
    )
    assert rows[0]["organization_name"] == "한국수력원자력"


def test_team_rr_preserves_an_observed_affiliation_status() -> None:
    """Do not downgrade an explicitly observed team-to-organization affiliation."""
    rows = lw.parse_roles_and_responsibilities_response(
        {
            "roles_and_responsibilities": [
                {
                    "actor_type": "team",
                    "actor_name": "설계팀",
                    "organization_name": "한국수력원자력",
                    "affiliated_organization_name": "한국수력원자력",
                    "affiliation_status": "observed",
                    "role": "설계",
                    "responsibility": "검토",
                }
            ]
        },
        {},
    )
    assert rows[0]["affiliation_status"] == "observed"


def test_live_organization_alias_resolution_preserves_direction_and_external_evidence() -> None:
    """Persist an LLM-resolved alias only when it cites supplied external evidence."""
    evidence = [
        {
            "evidence_id": "external-1",
            "evidence_kind": "external",
            "title": "Official organization: 약칭 → 정식기관명",
            "excerpt": "The alias identifies the canonical organization.",
            "source_uri": "https://example.test/official",
            "source_rank": 1,
        }
    ]
    resolution = lw.derive_organization_alias_resolution(
        "약칭",
        document_context={"title": "약칭 설계 검토"},
        external_evidence=evidence,
        transport=lambda body: {
            "decision": "verified",
            "canonical_name": "정식기관명",
            "confidence": 0.94,
            "rationale": body["external_evidence"][0]["title"],
            "evidence_ids": ["external-1"],
            "model": "fixture-model",
        },
    )
    graph, candidate = lw.attach_verified_organization_alias(
        {"nodes": [], "edges": []},
        resolution,
        document_no="DOC-1",
    )
    assert resolution["direction"] == "alias_to_canonical"
    assert candidate["source_node"].startswith("kg:organization_alias:")
    assert candidate["target_node"].startswith("kg:organization:")
    assert graph["edges"][0]["source"] == candidate["source_node"]
    assert graph["edges"][0]["target"] == candidate["target_node"]
    assert graph["edges"][0]["evidence_status"] == lw.EVIDENCE_INFERRED
    assert graph["edges"][0]["verification_decision"] == "verified"
    assert "http://www.w3.org/2004/02/skos/core#exactMatch" in {
        term["standard_uri"] for term in lw.semantic_layer_records(graph)["terms"]
    }
    assert lw.normalize_organization_alias_resolution(
        {"decision": "verified", "canonical_name": "정식기관명", "evidence_ids": ["unknown"]},
        "약칭",
        evidence,
    )["decision"] == "insufficient"
    assert lw.normalize_organization_alias_resolution(
        {"decision": "verified", "canonical_name": "다른기관", "evidence_ids": ["external-1"]},
        "약칭",
        evidence,
    )["decision"] == "insufficient"
    duplicate_graph, _ = lw.attach_verified_organization_alias(graph, resolution, document_no="DOC-1")
    assert len(duplicate_graph["edges"]) == 1


def test_content_inspection_rejects_unavailable_placeholder() -> None:
    """A vision placeholder is not OCR; the asset must go to the omni-modal path."""
    try:
        lw.normalize_content_inspection_response({"ocr_text": "[image: content unavailable]"})
    except ValueError as exc:
        assert "placeholder" in str(exc)
    else:
        raise AssertionError("placeholder OCR must fail closed")


def test_semantic_metadata_bounds_nested_values_and_rejects_malformed_roles() -> None:
    """Bound arbitrary model metadata while preserving useful JSON-shaped semantics."""
    assert lw._bounded_semantic_value(None) == ""
    assert lw._bounded_semantic_value(["one", {"two": ["three"]}]) == [
        "one",
        {"two": "['three']"},
    ]
    assert lw._bounded_semantic_value({"outer": {"inner": {"leaf": "value"}}}) == {
        "outer": {"inner": "{'leaf': 'value'}"}
    }
    assert lw._bounded_semantic_value(object())
    assert lw.parse_roles_and_responsibilities_response(
        {"roles_and_responsibilities": {}}, {}
    ) == []


def test_appointment_llm_derivation_preserves_live_dates_and_safe_extract_fallback() -> None:
    """Use the appointment task first, then retain a document-anchored extract if it is unavailable."""
    requests: list[dict] = []
    derived = lw.derive_appointments_via_llm(
        "Customer review meeting",
        document_no="260220-0010-01",
        transport=lambda body: requests.append(body)
        or {"promises": [{"date": "2026.03.05", "text": "Customer review meeting"}]},
    )
    assert requests[0]["task"] == "appointment_extract"
    assert derived[0]["occurred_on"] == "2026-03-05"
    assert derived[0]["excerpt"] == "Customer review meeting"
    assert derived[0]["source"] == "llm"

    fallback = lw.derive_appointments_via_llm(
        "Customer visit meeting",
        document_no="260220-0010-01",
        transport=lambda _body: (_ for _ in ()).throw(RuntimeError("worker unavailable")),
    )
    assert fallback[0]["occurred_on"] == "2026-02-20"
    assert fallback[0]["source"] == "extract"


def test_ontology_inference_verification_is_bounded_and_fails_closed(monkeypatch) -> None:
    """Keep LLM verification inside supplied evidence and never promote transitions."""
    graph = {
        "nodes": [
            {"id": "kg:document:DOC-1", "type": "document", "document_nos": ["DOC-1"], "label": "Document"},
            {"id": "kg:org:left", "type": "organization", "document_nos": ["DOC-1"], "label": "Acme Korea"},
            {"id": "kg:org:right", "type": "organization", "document_nos": ["DOC-2"], "label": "Acme Plant"},
        ],
        "edges": [
            {"source": "kg:document:DOC-1", "target": "kg:org:left", "relation": "document_customer_entity", "evidence_id": "ROW-1"},
            {"source": "kg:org:left", "target": "kg:org:right", "relation": "affiliate_affinity", "evidence_status": "inferred", "reason": "tree"},
        ],
    }
    candidate = lw.inference_candidates_for_document(graph, "DOC-1")[0]
    internal = lw.search_internal_inference_evidence(graph, candidate)
    assert [item["evidence_id"] for item in internal] == ["ROW-1"]
    assert lw.inference_organization_labels(graph, candidate) == ["Acme Korea", "Acme Plant"]
    assert lw.normalize_ontology_relationship_verification(
        {"decision": "verified", "confidence": 2, "evidence_ids": ["not-supplied"]},
        ["ROW-1"],
    )["decision"] == "insufficient"
    verified = lw.derive_ontology_relationship_verification(
        candidate,
        internal_evidence=internal,
        external_evidence=[],
        transport=lambda body: {"decision": "verified", "confidence": "0.8", "evidence_ids": [body["internal_evidence"][0]["evidence_id"]]},
    )
    assert verified["decision"] == "verified"
    assert candidate["relation_name"] not in lw.TRANSITION_RELATIONS

    monkeypatch.delenv("LINEAGEWEAVE_SEARXNG_URL", raising=False)
    assert lw.search_external_inference_evidence(["Acme Korea", "Acme Plant"])["mode"] == "not_configured"


def test_rehydrated_kg_keeps_lineage_evidence_tier_and_reason() -> None:
    """Restore persisted relationship metadata and add a previously absent prediction."""
    graph = {
        "nodes": [
            {"id": "kg:document:DOC-1", "type": "document", "document_no": "DOC-1", "document_nos": ["DOC-1"], "label": "First"},
            {"id": "kg:document:DOC-2", "type": "document", "document_no": "DOC-2", "document_nos": ["DOC-2"], "label": "Second"},
        ],
        "edges": [
            {"source": "kg:document:DOC-1", "target": "kg:document:DOC-2", "relation": "topic_affinity"},
        ],
    }
    repaired, changed = lw.merge_lineage_evidence_into_knowledge_graph(
        graph,
        [
            {
                "source": "doc:DOC-1",
                "target": "doc:DOC-2",
                "relation": "topic_affinity",
                "evidence_status": lw.EVIDENCE_INFERRED,
                "reason": "shared_topic",
            },
            {
                "source": "doc:DOC-2",
                "target": "doc:DOC-1",
                "relation": "entity_role_affinity",
                "evidence_status": lw.EVIDENCE_PREDICTED,
                "reason": "shared_role_hypothesis",
            },
        ],
    )
    assert changed == 3
    candidates = lw.inference_candidates_for_document(repaired, "DOC-1")
    assert {(item["relation_name"], item["evidence_status"], item["reason"]) for item in candidates} == {
        ("topic_affinity", lw.EVIDENCE_INFERRED, "shared_topic"),
        ("entity_role_affinity", lw.EVIDENCE_PREDICTED, "shared_role_hypothesis"),
    }


def test_searxng_evidence_query_never_uses_person_labels(monkeypatch) -> None:
    """Send only organization labels through the optional external-search boundary."""
    captured = {}

    def urlopen(request, **_kwargs):  # noqa: ANN001
        captured["url"] = request.full_url
        return _Response({"results": [
            {"url": "javascript:alert(1)", "title": "unsafe", "content": "ignore me"},
            {"url": "https://example.test/evidence", "title": "Acme relationship", "content": "verified source"},
        ]})

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "http://127.0.0.1:8888")
    monkeypatch.setattr(lw.urllib.request, "urlopen", urlopen)
    result = lw.search_external_inference_evidence(["Acme Korea", "Acme Plant"], limit=1)
    assert result["mode"] == "searxng"
    assert result["evidence"][0]["evidence_kind"] == "external"
    assert result["evidence"][0]["source_uri"] == "https://example.test/evidence"
    assert "Acme+Korea" in captured["url"]


def test_zotero_method_paper_store_uses_recorded_path_and_honest_unreachable(monkeypatch) -> None:
    """Post OA extract/verify papers to Local Zotero without inventing a stored write."""
    paper = lw.OA_METHOD_PAPERS[0]
    payload = lw.zotero_item_payload(paper)
    assert payload["url"].startswith("https://")
    assert payload["title"]
    assert payload["creators"][0]["lastName"]
    banned_tenant = "".join(("hyo", "sung"))
    assert banned_tenant not in json.dumps(payload).lower()
    assert lw.zotero_connector_save_url("http://127.0.0.1:23119/api").endswith("/connector/saveItems")
    stored = lw.store_oa_method_paper(
        paper,
        transport=lambda body: {"status_code": 201, "body": b""},
    )
    assert stored["store_status"] == "stored"
    assert stored["zotero_item_key"] == paper["paper_id"]
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://127.0.0.1:23119/api")

    def boom(_request, **_kwargs):  # noqa: ANN001
        raise urllib.error.URLError("zotero down")

    monkeypatch.setattr(lw.urllib.request, "urlopen", boom)
    missed = lw.store_oa_method_paper(paper)
    assert missed["store_status"] == "unreachable"
    probe = lw.probe_zotero_local_api(transport=lambda *_args: {"status_code": 200, "body": b"Nothing to see here."})
    assert probe["status"] == "reachable"
    statements: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((sql, tuple(params))),
    )
    written = lw.persist_method_paper_records(object(), [stored, missed])
    assert written == 2
    assert any("analysis_method_paper_records" in sql for sql, _ in statements)
    assert all(params[7] in {"stored", "unreachable"} for sql, params in statements if len(params) >= 8)
    upsert_sql = next(sql for sql, params in statements if len(params) >= 8)
    assert "WHEN EXCLUDED.attachment_status = 'not_attempted'" in upsert_sql
    assert "analysis_method_paper_records.zotero_attachment_key" in upsert_sql


def test_external_verification_fails_closed_and_keeps_only_safe_citations(monkeypatch) -> None:
    """Treat unavailable verification and unsafe search results as non-evidence."""
    monkeypatch.delenv("LINEAGEWEAVE_SEARXNG_URL", raising=False)
    assert lw.search_external_inference_evidence(["Northwind", "Plant"])["mode"] == "not_configured"

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "http://127.0.0.1:8888")
    assert lw.search_external_inference_evidence(["Northwind"])["mode"] == "not_applicable"
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "results": [
                    "not-a-result",
                    {"url": "file:///untrusted", "title": "ignore", "content": "ignore"},
                    {
                        "url": "https://evidence.example.test/relationship",
                        "title": "Public relationship evidence",
                        "content": "Bounded public evidence excerpt",
                    },
                    {
                        "url": "https://evidence.example.test/second",
                        "title": "second",
                        "content": "second",
                    },
                ]
            }
        ),
    )
    result = lw.search_external_inference_evidence(["Northwind", "Plant"], limit=0)
    assert result["mode"] == "searxng"
    assert [item["source_uri"] for item in result["evidence"]] == [
        "https://evidence.example.test/relationship"
    ]

    class LargeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return b"x" * 1_000_001

    monkeypatch.setattr(lw.urllib.request, "urlopen", lambda *_args, **_kwargs: LargeResponse())
    assert lw.search_external_inference_evidence(["Northwind", "Plant"])["mode"] == "unavailable"
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")),
    )
    assert lw.search_external_inference_evidence(["Northwind", "Plant"])["mode"] == "unavailable"


def test_zotero_store_statuses_and_response_shapes_remain_honest(monkeypatch) -> None:
    """Classify malformed, rejected, unreachable, and connector-keyed OA paper writes explicitly."""
    paper = lw.OA_METHOD_PAPERS[0]
    rejected = lw.store_oa_method_paper({**paper, "source_uri": "file:///not-a-citation"})
    assert rejected["store_status"] == "rejected"
    stored = lw.store_oa_method_paper(
        paper,
        transport=lambda _payload: {"status_code": 201, "body": [{"successful": {"0": {"key": "ZOTERO-1"}}}]},
    )
    assert (stored["store_status"], stored["zotero_item_key"]) == ("stored", "ZOTERO-1")
    assert lw.store_oa_method_paper(paper, transport=lambda _payload: {"status_code": 400, "body": b""})["store_status"] == "rejected"
    assert lw.store_oa_method_paper(paper, transport=lambda _payload: {"status_code": 503, "body": b""})["store_status"] == "unreachable"

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://127.0.0.1:23119/api")
    assert lw.probe_zotero_local_api(transport=lambda *_args: {"status_code": 503, "body": b""})["status"] == "unreachable"
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://example.invalid/api")
    assert lw.probe_zotero_local_api()["status"] == "invalid_url"

    records = lw.store_default_oa_method_papers(transport=lambda _payload: {"status_code": 201, "body": {"key": "batch-key"}})
    assert len(records) == len(lw.OA_METHOD_PAPERS)
    assert {record["store_status"] for record in records} == {"stored"}


def test_multimodal_method_papers_cover_layout_and_ocr_choices() -> None:
    """Keep the image/layout research set in the same provenance registry."""
    papers = {paper["paper_id"]: paper for paper in lw.OA_METHOD_PAPERS}
    assert {
        "layoutlm-2020",
        "layoutlmv2-2020",
        "docformer-2021",
        "donut-2022",
    } <= papers.keys()
    assert all(str(papers[paper_id]["source_uri"]).startswith("https://") for paper_id in papers)


def test_zotero_store_posts_connector_protocol_and_reads_success_key(monkeypatch) -> None:
    """Exercise the real Local Zotero connector request path without a network dependency."""
    captured: dict[str, object] = {}

    class Response:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return b'{"successful":{"0":{"key":"LOCAL-ITEM"}}}'

    def urlopen(request, **_kwargs):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        return Response()

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://127.0.0.1:23119/api")
    monkeypatch.setattr(lw.urllib.request, "urlopen", urlopen)
    stored = lw.store_oa_method_paper(lw.OA_METHOD_PAPERS[0])

    assert stored["store_status"] == "stored"
    assert stored["zotero_item_key"] == "LOCAL-ITEM"
    assert str(captured["url"]).endswith("/connector/saveItems")
    assert captured["body"]["items"][0]["url"].startswith("https://")


def test_zotero_store_reuses_existing_exact_item_and_attachment(monkeypatch) -> None:
    """Prevent repeat analysis runs from creating duplicate Zotero parents and files."""
    paper = lw.OA_METHOD_PAPERS[3]
    source_bytes = b"%PDF-1.7 existing OA fixture"
    requests: list[urllib.request.Request] = []

    class Response:
        status = 200
        headers: dict[str, str] = {}

        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, *_args):
            return self.body

    def urlopen(request, **_kwargs):  # noqa: ANN001
        requests.append(request)
        assert request.get_method() == "GET"
        if "/items?" in request.full_url:
            return Response(json.dumps([{
                "key": "EXISTING-PARENT",
                "data": {
                    "key": "EXISTING-PARENT",
                    "itemType": "journalArticle",
                    "title": paper["title"],
                    "url": paper["source_uri"],
                },
            }]).encode())
        if request.full_url.endswith("/items/EXISTING-PARENT/children?limit=100"):
            return Response(json.dumps([{
                "key": "EXISTING-ATTACHMENT",
                "data": {
                    "key": "EXISTING-ATTACHMENT",
                    "itemType": "attachment",
                    "parentItem": "EXISTING-PARENT",
                    "url": lw.method_paper_attachment_uri(paper),
                    "md5": lw.hashlib.md5(source_bytes).hexdigest(),
                },
            }]).encode())
        assert request.full_url == lw.method_paper_attachment_uri(paper)
        return Response(source_bytes)

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://127.0.0.1:23119/api")
    monkeypatch.setattr(lw.urllib.request, "urlopen", urlopen)

    stored = lw.store_oa_method_paper(paper, include_attachment=True)

    assert stored["store_status"] == "stored"
    assert stored["attachment_status"] == "stored"
    assert stored["zotero_item_key"] == "EXISTING-PARENT"
    assert stored["zotero_attachment_key"] == "EXISTING-ATTACHMENT"
    assert stored["content_digest"] == lw.hashlib.sha256(source_bytes).hexdigest()
    assert all(request.get_method() == "GET" for request in requests)

    def parent_only(request, **_kwargs):  # noqa: ANN001
        assert "/items?" in request.full_url
        return Response(json.dumps([{
            "key": "EXISTING-PARENT",
            "data": {
                "key": "EXISTING-PARENT",
                "itemType": "journalArticle",
                "title": paper["title"],
                "url": paper["source_uri"],
            },
        }]).encode())

    monkeypatch.setattr(lw.urllib.request, "urlopen", parent_only)
    metadata_only = lw.store_oa_method_paper(paper, include_attachment=False)
    assert metadata_only["zotero_item_key"] == "EXISTING-PARENT"
    assert metadata_only["attachment_status"] == "not_attempted"

    def invalid_child(request, **_kwargs):  # noqa: ANN001
        if "/items?" in request.full_url:
            return parent_only(request, **_kwargs)
        assert request.full_url.endswith("/items/EXISTING-PARENT/children?limit=100")
        return Response(json.dumps([{
            "key": "INVALID-ATTACHMENT",
            "data": {
                "itemType": "attachment",
                "url": "https://example.invalid/not-the-original.pdf",
                "md5": "",
            },
        }]).encode())

    monkeypatch.setattr(lw.urllib.request, "urlopen", invalid_child)
    assert lw._existing_zotero_method_paper(
        "http://127.0.0.1:23119/api", paper, include_attachment=True
    ) is None

    def missing_md5(request, **_kwargs):  # noqa: ANN001
        if "/items?" in request.full_url:
            return parent_only(request, **_kwargs)
        if request.full_url.endswith("/items/EXISTING-PARENT/children?limit=100"):
            return Response(json.dumps([{
                "key": "ATTACHMENT-WITHOUT-MD5",
                "data": {
                    "itemType": "attachment",
                    "url": lw.method_paper_attachment_uri(paper),
                    "md5": "",
                },
            }]).encode())
        assert request.full_url == lw.method_paper_attachment_uri(paper)
        return Response(source_bytes)

    monkeypatch.setattr(lw.urllib.request, "urlopen", missing_md5)
    assert lw._existing_zotero_method_paper(
        "http://127.0.0.1:23119/api", paper, include_attachment=True
    ) == (
        "EXISTING-PARENT",
        "ATTACHMENT-WITHOUT-MD5",
        lw.hashlib.sha256(source_bytes).hexdigest(),
    )


def test_zotero_store_can_attach_bounded_oa_original_and_fail_honestly(monkeypatch) -> None:
    """Use the Local Zotero two-request connector protocol for an OA original."""
    paper = lw.OA_METHOD_PAPERS[3]
    assert lw.method_paper_attachment_uri(paper).endswith(".pdf")
    assert lw.method_paper_attachment_uri({**paper, "source_uri": "https://arxiv.org/abs/2606.21228.pdf"}).endswith(".pdf")
    assert lw.method_paper_attachment_uri(lw.OA_METHOD_PAPERS[0]) == lw.OA_METHOD_PAPERS[0]["source_uri"]
    with pytest.raises(RuntimeError, match="source_invalid"):
        lw._store_zotero_method_attachment(
            "http://127.0.0.1:23119/api",
            {"source_uri": "file:///not-an-oa-source"},
            session_id="fixture-session",
            parent_item_id="fixture-parent",
        )

    class AttachmentResponse:
        """Expose status, headers, and bounded bytes for a source or connector response."""

        def __init__(self, body: bytes, *, status: int, content_type: str = "") -> None:
            self.body = body
            self.status = status
            self.headers = {"Content-Type": content_type} if content_type else {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, *_args):
            return self.body

    requests: list[urllib.request.Request] = []
    source_bytes = b"%PDF-1.7 bounded fixture"

    def urlopen(request, **_kwargs):  # noqa: ANN001
        requests.append(request)
        if len(requests) == 1:
            return AttachmentResponse(b"[]", status=200, content_type="application/json")
        if len(requests) == 2:
            return AttachmentResponse(
                b'{"successful":{"lineageweave:sakana-fugu-2026":{"key":"PARENT"}}}',
                status=201,
                content_type="application/json",
            )
        if len(requests) == 3:
            return AttachmentResponse(source_bytes, status=200)
        if len(requests) == 4:
            return AttachmentResponse(b"not-json", status=201, content_type="application/json")
        if len(requests) == 5:
            return AttachmentResponse(json.dumps([{
                "key": "PARENT",
                "data": {
                    "key": "PARENT",
                    "itemType": "journalArticle",
                    "title": paper["title"],
                    "url": paper["source_uri"],
                },
            }]).encode(), status=200, content_type="application/json")
        if len(requests) == 6:
            return AttachmentResponse(json.dumps([{
                "key": "ATTACHMENT",
                "data": {
                    "itemType": "attachment",
                    "url": lw.method_paper_attachment_uri(paper),
                    "md5": "",
                },
            }]).encode(), status=200, content_type="application/json")
        return AttachmentResponse(source_bytes, status=200, content_type="application/pdf")

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://127.0.0.1:23119/api")
    monkeypatch.setattr(lw.urllib.request, "urlopen", urlopen)
    stored = lw.store_oa_method_paper(paper, include_attachment=True)
    assert stored["store_status"] == "stored"
    assert stored["attachment_status"] == "stored"
    assert stored["zotero_item_key"] == "PARENT"
    assert stored["zotero_attachment_key"] == "ATTACHMENT"
    assert stored["content_digest"] == lw.hashlib.sha256(source_bytes).hexdigest()
    metadata = json.loads(requests[3].get_header("X-metadata"))
    assert requests[2].get_header("User-agent").startswith("LineageWeave/")
    assert metadata["sessionID"]
    assert metadata["parentItemID"] == "lineageweave:sakana-fugu-2026"
    assert metadata["contentType"] == "application/pdf"
    assert requests[3].full_url.startswith("http://127.0.0.1:23119/connector/saveAttachment?")

    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([
                AttachmentResponse(b"[]", status=200, content_type="application/json"),
                AttachmentResponse(b'{"key":"PARENT"}', status=201, content_type="application/json"),
                urllib.error.URLError("source offline"),
                AttachmentResponse(b"[]", status=200, content_type="application/json"),
            ]),
        )
    unavailable = lw.store_oa_method_paper(paper, include_attachment=True)
    assert (unavailable["store_status"], unavailable["attachment_status"]) == ("stored", "unreachable")

    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([
                AttachmentResponse(b"[]", status=200, content_type="application/json"),
                AttachmentResponse(b'{"key":"PARENT"}', status=201, content_type="application/json"),
                AttachmentResponse(source_bytes, status=200, content_type="application/pdf"),
                AttachmentResponse(b"rejected", status=400),
                AttachmentResponse(b"[]", status=200, content_type="application/json"),
            ]),
    )
    rejected = lw.store_oa_method_paper(paper, include_attachment=True)
    assert (rejected["store_status"], rejected["attachment_status"]) == ("stored", "rejected")

    monkeypatch.setattr(lw, "MAX_METHOD_PAPER_ATTACHMENT_BYTES", 4)
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([
                AttachmentResponse(b"[]", status=200, content_type="application/json"),
                AttachmentResponse(b'{"key":"PARENT"}', status=201, content_type="application/json"),
                AttachmentResponse(b"too large", status=200, content_type="application/pdf"),
                AttachmentResponse(b"[]", status=200, content_type="application/json"),
            ]),
    )
    too_large = lw.store_oa_method_paper(paper, include_attachment=True)
    assert too_large["attachment_status"] == "unreachable"

    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([
                AttachmentResponse(b"[]", status=200, content_type="application/json"),
                AttachmentResponse(b'{"key":"PARENT"}', status=201, content_type="application/json"),
                AttachmentResponse(b"", status=200, content_type="application/pdf"),
                AttachmentResponse(b"[]", status=200, content_type="application/json"),
            ]),
    )
    empty = lw.store_oa_method_paper(paper, include_attachment=True)
    assert empty["attachment_status"] == "unreachable"
    metadata_only = lw.store_default_oa_method_papers(
        transport=lambda _payload: {"status_code": 201, "body": {"key": "PARENT"}},
        include_attachments=False,
    )
    assert len(metadata_only) == len(lw.OA_METHOD_PAPERS)


def test_zotero_loopback_http_is_valid_without_dev_mode(monkeypatch) -> None:
    """Local Zotero is HTTP on loopback; CLI persist must not label that invalid_url."""
    monkeypatch.delenv("LINEAGEWEAVE_DEV_MODE", raising=False)
    monkeypatch.delenv("LINEAGEWEAVE_ZOTERO_API", raising=False)
    assert lw.zotero_local_api_url() == "http://127.0.0.1:23119/api"
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://localhost:23119/api")
    assert lw.zotero_local_api_url() == "http://localhost:23119/api"
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://example.invalid/api")
    try:
        lw.zotero_local_api_url()
    except RuntimeError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("non-loopback HTTP Zotero URL must fail closed")


def test_zotero_connector_attachment_url_targets_root_connector_endpoint() -> None:
    """Resolve any Zotero API base into the connector attachment endpoint."""
    assert lw.zotero_connector_attachment_url("https://127.0.0.1:23119/api") == "https://127.0.0.1:23119/connector/saveAttachment"
    assert (
        lw.zotero_connector_attachment_url("http://127.0.0.1:23119/api?foo=bar")
        == "http://127.0.0.1:23119/connector/saveAttachment"
    )


def test_zotero_connector_failure_statuses_remain_auditable(monkeypatch) -> None:
    """Map Local Zotero URL and connector failures to explicit non-success states."""
    paper = lw.OA_METHOD_PAPERS[0]
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "ftp://127.0.0.1:23119/api")
    assert lw.store_oa_method_paper(paper)["store_status"] == "invalid_url"

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://127.0.0.1:23119/api")
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_Response([]), _http_error(429)]))
    assert lw.store_oa_method_paper(paper)["store_status"] == "rejected"
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_Response([]), _http_error(503)]))
    assert lw.store_oa_method_paper(paper)["store_status"] == "unreachable"
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_Response([]), urllib.error.URLError("offline")]))
    assert lw.store_oa_method_paper(paper)["store_status"] == "unreachable"


def test_database_image_marker_classifies_a_large_cell_without_exporting_bytes() -> None:
    """Treat a DB-detected image marker beyond the bounded prefix as an inline image."""
    payload = lw.build_payload(
        [
            {
                "guid_field": "ROW-1",
                "docnosub_field": "DOC-1",
                "acthguid_field": "THREAD-1",
                "voctp_field": "opened",
                "grade_field": "A",
                "title_field": "Large inline content fixture",
                "ststs_field": "open",
                "dtsts_field": "active",
                "bukrs_field": "CORP-A",
                "pucode_field": "PU-A",
                "ernam_field": "Ana",
                "aenam_field": "Ana",
                "userid_field": "ana",
                "erdat_field": "2026-01-01",
                "erzet_field": "09:00:00",
                "aedat_field": "2026-01-01",
                "aezet_field": "10:00:00",
                "source_row_number": "1",
                "content_prefix": "<html>bounded prefix without the image marker</html>",
                "content_bytes": str(40 * 1024 * 1024 + 1),
                "content_has_inline_image": "true",
                "artifact_reference": "false",
            }
        ]
    )

    manifest = payload["nodes"][0]["content_manifest"]
    assert manifest["max_bytes"] == 40 * 1024 * 1024 + 1
    assert manifest["inline_image_candidate_rows"] == 1
    assert manifest["row_counts_by_kind"] == {lw.CONTENT_INLINE_IMAGE: 1}


def test_source_query_escapes_image_marker_wildcards_for_psycopg() -> None:
    """Emit SQL that psycopg can execute instead of mistaking image markers for binds."""
    query = lw.build_source_query("schema.fixture_table")

    assert "LIKE '%%data:%%;base64,%%'" in query
    assert "LIKE '%%<svg%%'" in query


def test_live_gateway_and_compose_transport_contracts(monkeypatch) -> None:
    """Use live-model fallbacks and ensure the Compose worker never invents an auth credential."""
    monkeypatch.setattr(lw, "verified_gateway_ssl_context", lambda: object())
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([_http_error(404), _Response({"model": "chat", "choices": [{"message": {"content": '{"our_side":["Ana"],"counterpart_side":["Bo"]}'}}]})]),
    )
    assert lw.post_keyman_http({"task": "keyman_extract"}, base_url="https://gateway.example", token="token")["model"] == "chat"
    captured: list[dict[str, object]] = []

    def product_urlopen(request, **_kwargs):  # noqa: ANN001
        captured.append(json.loads(request.data.decode("utf-8")))
        return _Response(
            {
                "model": "chat",
                "choices": [
                    {
                        "message": {
                            "content": '{"appointments":[]}',
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr(lw.urllib.request, "urlopen", product_urlopen)
    assert lw.post_product_llm_http(
        {"task": "appointment_extract", "text": "meeting"},
        base_url="https://gateway.example",
        token="token",
    ) == {"appointments": [], "model": "chat"}
    assert "appointments array" in captured[0]["messages"][0]["content"]
    with pytest.raises(ValueError, match="unsupported_product_llm_task"):
        lw.post_product_llm_http({}, base_url="https://gateway.example", token="token")
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([_http_error(405), _Response({"model": "vision", "choices": [{"message": {"content": "plain OCR"}}]})]),
    )
    assert lw.post_content_inspection_http({"image_data_uri": "data:image/png;base64,AA=="}, base_url="https://gateway.example", token="token")["ocr_text"] == "plain OCR"
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([_http_error(404), _Response({"model": "chat", "choices": [{"message": {"content": '{"answer":"ok","evidence_ids":["row-1"]}'}}]})]),
    )
    assert lw.post_lineage_chat({"events": []}, base_url="https://gateway.example", token="token")["answer"] == "ok"

    observed: list[object] = []
    monkeypatch.setattr(lw.urllib.request, "urlopen", lambda request, **_kwargs: observed.append(request) or _Response({"answer": "ok"}))
    monkeypatch.delenv("ORCHESTRATOR_TOKEN", raising=False)
    monkeypatch.setenv("LINEAGEWEAVE_COMPOSE_STANDIN_URL", "http://worker.example")
    assert lw.compose_standin_transport({"task": "event_lineage_chat"}) == {"answer": "ok"}
    assert lw.compose_standin_transport({"task": "customer_master"}) == {"answer": "ok"}
    assert observed[0].get_header("Authorization") is None
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "token")
    assert lw.live_http_config() == ("https://gateway.example", "token", "gpt-4.1-mini")
    keyman_transport = lw.make_live_keyman_transport()
    monkeypatch.setattr(lw, "post_keyman_http", lambda body, **_kwargs: {"keymen": [body["task"]]})
    assert keyman_transport({"task": "keyman_extract"}) == {"keymen": ["keyman_extract"]}
    monkeypatch.setenv("LINEAGEWEAVE_PRODUCT_LLM_TIMEOUT", "13")
    monkeypatch.setenv("LINEAGEWEAVE_REPORT_JUDGE_TIMEOUT", "7")
    product_transport = lw.make_live_product_transport()
    product_timeouts: dict[str, int] = {}

    def post_product(body, **kwargs):  # noqa: ANN001
        product_timeouts[str(body["task"])] = int(kwargs["timeout"])
        return {"task": body["task"]}

    monkeypatch.setattr(
        lw,
        "post_product_llm_http",
        post_product,
    )
    assert product_transport({"task": "report_judge"}) == {"task": "report_judge"}
    assert product_transport({"task": "appointment_extract"}) == {"task": "appointment_extract"}
    assert product_timeouts == {"report_judge": 7, "appointment_extract": 13}
    monkeypatch.setattr(lw, "make_live_product_transport", lambda: product_transport)
    assert lw.resolve_product_transport() == (product_transport, "live_http")
    monkeypatch.delenv("LLM_GATEWAY_URL")
    monkeypatch.delenv("LLM_GATEWAY_API_KEY")
    monkeypatch.delenv("ORCHESTRATOR_BASE_URL", raising=False)
    monkeypatch.setattr(lw, "load_runtime_env", lambda: None)
    monkeypatch.setattr(lw.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response({"ok": True}))
    assert lw.ensure_compose_standin() == "compose_already_up"


def test_orchestration_policy_allocates_route_and_conduct(monkeypatch) -> None:
    """Carry paper-derived routing, role, budget, recursion, and access metadata."""
    simple = lw.build_orchestration_envelope(
        {"task": "keyman_extract", "orchestration": {"conductor_role": "worker"}}
    )
    assert simple["fugu_routing_vs_composition"] == "single_model_routing"
    assert simple["workflow_stages"] == ["worker"]
    assert simple["recursion_depth"] == 0
    assert simple["reasoning_effort"] == "medium"

    deep = lw.build_orchestration_envelope(
        {
            "task": "event_lineage_chat",
            "orchestration": {"conductor_role": "thinker", "workflow_stage": "event_narrative"},
        }
    )
    assert deep["fugu_routing_vs_composition"] == "deep_multi_agent"
    assert deep["workflow_stages"] == ["thinker", "worker", "verifier", "synthesizer"]
    assert deep["task_decomposition"] == "bounded_evidence_units"
    assert deep["recursion_depth"] == 1
    assert deep["workflow_stage"] == "event_narrative"
    assert deep["access_list"] == ["authorized_document_context", "semantic_layer", "source_evidence"]

    bare_visual = lw.build_orchestration_envelope(
        {"task": "content_inspection", "image_data_uri": "data:image/png;base64,AA=="}
    )
    assert bare_visual["conductor_role"] == "verifier"
    assert bare_visual["workflow_stage"] == "content_inspection"

    monkeypatch.delenv("ORCHESTRATOR_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    assert not lw._uses_contextual_orchestrator("https://gateway.example")
    monkeypatch.setenv("ORCHESTRATOR_BASE_URL", "https://orchestrator.example/")
    assert lw._uses_contextual_orchestrator("https://orchestrator.example")
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://gateway.example")
    assert not lw._uses_contextual_orchestrator("https://orchestrator.example")


def test_contextual_orchestrator_receives_mode_and_multimodal_policy(monkeypatch) -> None:
    """Send route/conduct controls at the gateway boundary, not only inside prompt JSON."""
    captured: list[dict[str, object]] = []

    def contextual_urlopen(request, **_kwargs):  # noqa: ANN001
        payload = json.loads(request.data.decode("utf-8"))
        captured.append(payload)
        if request.full_url.endswith("/api/v1/content_inspection"):
            raise _http_error(404)
        response_content = (
            '{"ocr_text":"{}","object_labels":[]}'
            if isinstance(payload.get("messages", [{}, {}])[1].get("content"), list)
            else "{}"
        )
        return _Response({"model": "orchestrator-model", "choices": [{"message": {"content": response_content}}]})

    monkeypatch.setenv("ORCHESTRATOR_BASE_URL", "https://orchestrator.example")
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    monkeypatch.setattr(lw, "verified_gateway_ssl_context", lambda: object())
    monkeypatch.setattr(lw.urllib.request, "urlopen", contextual_urlopen)

    assert lw.post_product_llm_http(
        {"task": "report_judge", "report": {"report_id": "R-1"}},
        base_url="https://orchestrator.example",
        token="token",
    ) == {"model": "orchestrator-model"}
    assert captured[0]["orchestration"] == "conduct"
    assert captured[0]["reasoning_effort"] == "high"
    prompt_body = json.loads(captured[0]["messages"][1]["content"])
    assert prompt_body["orchestration"]["workflow_stages"][-1] == "synthesizer"
    assert prompt_body["orchestration"]["access_list"][-1] == "source_evidence"

    captured.clear()
    assert lw.post_content_inspection_http(
        {"task": "content_inspection", "image_data_uri": "data:image/png;base64,AA=="},
        base_url="https://orchestrator.example",
        token="token",
    ) == {"ocr_text": "{}", "object_labels": [], "model": "orchestrator-model"}
    assert captured[0]["orchestration"]["fugu_routing_vs_composition"] == "deep_multi_agent"
    assert captured[1]["orchestration"] == "conduct"
    multimodal_content = captured[1]["messages"][1]["content"]
    assert multimodal_content[1]["image_url"]["url"].startswith("data:image/png")
    assert json.loads(multimodal_content[0]["text"])["orchestration"]["recursion_depth"] == 1


def test_live_transport_failure_and_bootstrap_contracts(monkeypatch) -> None:
    """Exercise HTTP transport guards and the owned Compose bootstrap without a live gateway."""
    monkeypatch.setattr(lw, "load_runtime_env", lambda: None)
    monkeypatch.setattr(lw, "verified_gateway_ssl_context", lambda: object())
    monkeypatch.delenv("LINEAGEWEAVE_MLSIRM_URL", raising=False)
    with pytest.raises(RuntimeError, match="fast_mlsirm_url_unset"):
        lw.make_mlsirm_transport()

    observed: list[object] = []
    monkeypatch.setenv("LINEAGEWEAVE_MLSIRM_URL", "https://mlsirm.example/")
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        lambda request, **_kwargs: observed.append(request) or _Response({"scores": []}),
    )
    transport = lw.make_mlsirm_transport()
    assert transport.__name__ == "fast_mlsirm_http_transport"
    assert transport({"items": []}) == {"scores": []}
    assert observed[0].full_url == "https://mlsirm.example/api/v1/fipc_cat_link"
    assert observed[0].get_header("Authorization") is None
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_Response([])]))
    with pytest.raises(RuntimeError, match="fast_mlsirm_non_object"):
        transport({"items": []})

    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_Response({"ocr_text": "direct"})]))
    assert lw.post_content_inspection_http({}, base_url="https://gateway.example", token="token")["ocr_text"] == "direct"
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_http_error(401)]))
    with pytest.raises(RuntimeError, match="content inspection HTTP 401"):
        lw.post_content_inspection_http({"image_data_uri": "data:image/png;base64,AA=="}, base_url="https://gateway.example", token="token")
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([urllib.error.URLError("offline")]))
    with pytest.raises(ValueError, match="content inspection image is required"):
        lw.post_content_inspection_http({}, base_url="https://gateway.example", token="token")

    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_Response({"answer": "direct"})]))
    assert lw.post_lineage_chat({}, base_url="https://gateway.example", token="token")["answer"] == "direct"
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_http_error(401)]))
    with pytest.raises(RuntimeError, match="lineage chat HTTP 401"):
        lw.post_lineage_chat({}, base_url="https://gateway.example", token="token")
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_Response([])]))
    with pytest.raises(RuntimeError, match="compose stand-in returned a non-object"):
        lw.compose_standin_transport({"task": "keyman_extract"})
    with pytest.raises(RuntimeError, match="unsupported_compose_task"):
        lw.compose_standin_transport({"task": "identity"})
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([urllib.error.URLError("offline")]))
    with pytest.raises(RuntimeError, match="compose_worker_unavailable"):
        lw.compose_standin_transport({"task": "keyman_extract"})

    monkeypatch.setenv("LLM_GATEWAY_URL", "https://gateway.example")
    assert lw.ensure_compose_standin() == "live_url_present"
    monkeypatch.delenv("LLM_GATEWAY_URL")
    monkeypatch.delenv("ORCHESTRATOR_BASE_URL", raising=False)
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([urllib.error.URLError("down"), _Response({"ok": True})]))
    monkeypatch.setattr(lw.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""))
    assert lw.ensure_compose_standin() == "compose_started"


def test_keyman_and_report_item_models_preserve_two_sided_and_dichotomous_contracts() -> None:
    """Normalize model variations without moving a person across sides or inventing factor scores."""
    calls: list[str] = []

    def keyman_transport(body: dict) -> dict:
        calls.append(body["extract_side"])
        if body["extract_side"] == "our_side":
            return {"our_side": [{"name": "Author"}]}
        return {"counterpart_side": [], "model": "fixture-keyman"}

    derived = lw.derive_keymen_via_llm(
        "Operational review",
        transport=keyman_transport,
        authors={"created_by": "Author", "changed_by": "Reviewer"},
    )
    assert calls == ["our_side", "counterpart_side"]
    assert derived["our_side"] == [{"person_name": "Author", "org_name": ""}]
    assert derived["counterpart_side"] == [{"person_name": "Reviewer", "org_name": ""}]
    assert derived["response_model"] == "fixture-keyman"

    items = [
        {"item_id": "positive", "factor_id": "factor", "item_stem": "Positive condition"},
        {"item_id": "negative", "factor_id": "factor", "item_stem": "Negative condition"},
    ]
    assert lw.parse_factor_item_responses(
        {"item_scores": {"positive": "yes", "negative": "no", "ignored": "maybe"}}, items
    ) == [
        {"item_id": "positive", "response": 1},
        {"item_id": "negative", "response": 0},
    ]
    assert lw.derive_factor_item_responses_via_llm(
        {"report_id": "report-1"}, [], items, transport=lambda _body: {"item_responses": [{"item_id": "positive", "response": 1}]}
    ) == [{"item_id": "positive", "response": 1}]
    with pytest.raises(RuntimeError, match="factor_item_score_transport_failed"):
        lw.derive_factor_item_responses_via_llm(
            {"report_id": "report-1"}, [], items, transport=lambda _body: (_ for _ in ()).throw(RuntimeError("offline"))
        )
    with pytest.raises(RuntimeError, match="factor_item_scores_missing"):
        lw.derive_factor_item_responses_via_llm({"report_id": "report-1"}, [], items, transport=lambda _body: {})

    judged = lw.derive_dichotomous_judge_via_llm(
        {"report_id": "report-1", "title": "Weekly report", "document_nos": []},
        transport=lambda body: {
            "verdict": "pass",
            "item_scores": [{"item_id": body["items"][0]["item_id"], "response": 1}],
            "ragas_metrics": [
                {
                    "metric_id": "ragas_faithfulness",
                    "score": 0.9,
                    "rationale": "The cited writing supports the report.",
                    "evidence_ids": ["DOC-1"],
                }
            ],
        },
        items=items,
    )
    assert judged["verdict"] == "pass"
    assert judged["item_responses"] == [{"item_id": "positive", "response": 1}]
    assert judged["ragas_metrics"] == [
        {
            "metric_id": "ragas_faithfulness",
            "score": 0.9,
            "verdict": "pass",
            "metric_source": "llm_judge",
            "rationale": "The cited writing supports the report.",
            "evidence_ids": ["DOC-1"],
        }
    ]


def test_keyman_empty_model_result_is_not_replaced_by_regex_hints() -> None:
    """Keep an empty LLM result explicit so the authorized server can fail the derivation."""
    calls: list[str] = []

    def transport(body: dict) -> dict:
        calls.append(body["extract_side"])
        return {}

    result = lw.derive_keymen_via_llm("[External] named contact", transport=transport)

    assert calls == ["our_side", "counterpart_side"]
    assert result["names"] == []
    assert result["our_side"] == []
    assert result["counterpart_side"] == []
    assert (result["source"], result["status"]) == ("none", "empty")


def test_generic_keyman_model_output_keeps_author_on_our_side() -> None:
    """Recover a two-sided result from a model's legacy generic Keyman payload."""
    calls: list[str] = []

    def transport(body: dict) -> dict:
        calls.append(body["extract_side"])
        return {
            "keymen": [
                {"person_name": "Author", "org_name": "Our group"},
                {"person_name": "Partner", "org_name": "Partner group"},
            ],
            "model": "generic-keyman-fixture",
        }

    derived = lw.derive_keymen_via_llm(
        "Operational review",
        transport=transport,
        authors={"created_by": "Author"},
    )

    assert calls == ["our_side", "counterpart_side"]
    assert derived["our_side"] == [{"person_name": "Author", "org_name": "Our group"}]
    assert derived["counterpart_side"] == [{"person_name": "Partner", "org_name": "Partner group"}]
    assert derived["response_model"] == "generic-keyman-fixture"


def test_chat_and_content_normalizers_drop_duplicate_or_untrusted_rendering_inputs() -> None:
    """Keep model citations and DOM text bounded to authorized, visible evidence."""
    response = lw.normalize_event_chat_response(
        {
            "answer": "Grounded answer",
            "citations": [
                {"guid": "ROW-1", "label": "model label"},
                {"evidence_id": "ROW-1"},
                {"source_guid": "ROW-2"},
                {"guid": "outside"},
            ],
            "evidence_ids": ["ROW-2", "ROW-1"],
            "model": "fixture-chat",
        },
        [
            {"guid": "ROW-1", "title": "First event"},
            {"evidence_id": "ROW-2", "event": "Second event"},
        ],
        "DOC-1",
        semantic_context={
            "node_terms": [
                {"standard_uri": "urn:semantic:customer", "term_label": "Customer"},
                {"term_uri": "urn:semantic:customer", "term_label": "Duplicate"},
            ],
            "edge_assertions": [{"term_uri": "urn:semantic:affinity", "term_label": "Affinity"}, {}],
        },
    )
    assert response["evidence_ids"] == ["ROW-1", "ROW-2"]
    assert response["semantic_term_uris"] == ["urn:semantic:customer", "urn:semantic:affinity"]
    assert response["citations"][0]["label"] == "model label"
    assert response["model"] == "fixture-chat"

    structure = lw.extract_content_structure(
        "<template><span>ignored nested markup</span></template><p/>"
        "<p>data:image/png;base64,AAAA<br/>Visible content</p>"
    )
    assert [(block["block_kind"], block["text_content"]) for block in structure["blocks"]] == [
        ("paragraph", "Visible content")
    ]
    assert "data:image" not in str(structure)


def test_content_context_and_asset_digests_stay_bounded_at_transport_edges(monkeypatch) -> None:
    """Preserve visible context while excluding private bytes and unsupported image types."""
    bounded = lw.content_semantic_context(
        {
            "blocks": [
                {"text_content": "x" * lw.MAX_CHAT_CONTENT_CHARS, "block_kind": "paragraph"},
                {"text_content": "must-not-enter", "block_kind": "paragraph"},
            ],
            "assets": [{"mime_type": "image/png", "data_uri": "private", "asset_sha256": "private"}],
        }
    )
    assert bounded["block_count"] == 2
    assert len(bounded["blocks"]) == 1
    assert "data_uri" not in bounded["assets"][0]
    assert len(lw.content_asset_sha256({"data_uri": "data:text/plain,fixture"})) == 64
    assert not lw._image_has_expected_signature("image/tiff", b"fixture")

    monkeypatch.setattr(lw, "MAX_VISION_REQUEST_BYTES", 9)
    prepared = lw.prepare_content_inspection_asset(
        {"mime_type": "image/png", "data_uri": "data:image/png;base64,iVBORw0KGgo="}
    )
    assert prepared["mime_type"] == "image/png"


def test_report_judge_falls_back_to_item_scoring_without_inventing_scores() -> None:
    """Use a second LLM task only when the judge response omits item-level evidence."""
    items = [{"item_id": "factor-1", "factor_id": "factor", "item_stem": "Delivery commitment"}]
    calls: list[str] = []

    def transport(body: dict) -> dict:
        calls.append(body["task"])
        if body["task"] == "report_judge":
            return {"verdict": "yes", "rationale": "Observed commitment"}
        return {"item_responses": [{"item_id": "factor-1", "response": "pass"}]}

    report = {"report_id": "report-1", "title": "Weekly", "document_nos": ["DOC-1"]}
    judged = lw.derive_dichotomous_judge_via_llm(
        report,
        documents=[{"document_no": "DOC-1", "title_sample": "Customer commitment"}],
        items=items,
        transport=transport,
    )
    assert calls == ["report_judge", "report_item_scores"]
    assert judged["verdict"] == "pass"
    assert judged["item_responses"] == [{"item_id": "factor-1", "response": 1}]

    failed_followup = lw.derive_dichotomous_judge_via_llm(
        report,
        items=items,
        transport=lambda body: (
            {"verdict": "fail"}
            if body["task"] == "report_judge"
            else (_ for _ in ()).throw(RuntimeError("item scorer offline"))
        ),
    )
    assert failed_followup["item_responses"] == []
    with pytest.raises(RuntimeError, match="dichotomous_judge_transport_failed"):
        lw.derive_dichotomous_judge_via_llm(
            report,
            items=items,
            transport=lambda _body: (_ for _ in ()).throw(RuntimeError("judge offline")),
        )


def test_ragas_metric_parser_is_bounded_and_preserves_abstentions() -> None:
    """Accept only requested finite scores and retain unsupported metrics as abstentions."""
    structured = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "ragas_metrics": [
                                {
                                    "metric_id": "ragas_faithfulness",
                                    "score": 0.2,
                                    "evidence_ids": "DOC-1",
                                },
                                {
                                    "metric_id": "ragas_answer_relevancy",
                                    "score": "not-a-number",
                                    "verdict": "pass",
                                    "source": "fixture",
                                },
                                {
                                    "metric_id": "ragas_context_precision",
                                    "score": True,
                                    "status": "fail",
                                },
                                {
                                    "metric_id": "ragas_context_recall",
                                    "verdict": "abstain",
                                    "rationale": "No reference answer was supplied.",
                                },
                                {"metric_id": "unknown", "score": 1},
                                "malformed",
                                {"metric_id": "ragas_context_precision", "status": "maybe"},
                            ]
                        }
                    )
                }
            }
        ]
    }
    assert lw.parse_ragas_metric_scores(structured) == [
        {
            "metric_id": "ragas_faithfulness",
            "score": 0.2,
            "verdict": "fail",
            "metric_source": "llm_judge",
            "rationale": "",
            "evidence_ids": ["DOC-1"],
        },
        {
            "metric_id": "ragas_answer_relevancy",
            "score": 1.0,
            "verdict": "pass",
            "metric_source": "fixture",
            "rationale": "",
            "evidence_ids": [],
        },
        {
            "metric_id": "ragas_context_precision",
            "score": 0.0,
            "verdict": "fail",
            "metric_source": "llm_judge",
            "rationale": "",
            "evidence_ids": [],
        },
        {
            "metric_id": "ragas_context_recall",
            "score": None,
            "verdict": "abstain",
            "metric_source": "llm_judge",
            "rationale": "No reference answer was supplied.",
            "evidence_ids": [],
        },
    ]
    assert lw.parse_ragas_metric_scores(
        {"ragas_metrics": {"ragas_faithfulness": {"score": "pass"}, "ragas_answer_relevancy": 0.7}}
    )[1]["score"] == 0.7
    assert lw.parse_ragas_metric_scores({"ragas_metrics": "invalid"}) == []
    parsed_missing = lw.parse_ragas_metric_scores(
        {"verdict": "unavailable", "rationale": "mock timeout", "source": "llm_judge"},
        emit_missing_as_abstain=True,
    )
    assert len(parsed_missing) == 4
    assert {metric["metric_id"] for metric in parsed_missing} == {
        "ragas_faithfulness",
        "ragas_answer_relevancy",
        "ragas_context_precision",
        "ragas_context_recall",
    }
    assert all(metric["verdict"] == "abstain" for metric in parsed_missing)


def test_period_report_judge_stops_on_budget_and_fatal_transport(monkeypatch) -> None:
    """Bound repeated judge calls and disable later slices after fatal TLS failure."""
    slices = [
        {"report_id": "R-1", "slice_key": "PU-1", "document_nos": [], "title": "Fixture"},
        {"report_id": "R-2", "slice_key": "PU-2", "document_nos": [], "title": "Fixture"},
    ]
    monkeypatch.setenv("LINEAGEWEAVE_REPORT_JUDGE_TOTAL_ATTEMPTS", "1")
    budgeted = lw.score_period_reports(
        slices,
        [],
        judge_transport=lambda _body: {"verdict": "pass"},
    )
    assert budgeted[0]["judge"]["source"] == "llm_judge"
    assert budgeted[1]["judge"]["rationale"] == "report_judge_attempt_budget_exhausted"

    monkeypatch.setenv("LINEAGEWEAVE_REPORT_JUDGE_TOTAL_ATTEMPTS", "2")
    bounded = lw.score_period_reports(
        slices[:1],
        [],
        judge_transport=lambda _body: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert bounded[0]["judge"]["source"] == "unavailable"
    assert bounded[0]["judge"]["rationale"].startswith("dichotomous_judge_transport_failed")

    override_attempts: list[bool] = []
    lw.score_period_reports(
        slices[:1],
        [],
        judge_transport=lambda _body: override_attempts.append(True) or (_ for _ in ()).throw(RuntimeError("offline")),
        judge_max_attempts=1,
    )
    assert override_attempts == [True]

    monkeypatch.setenv("LINEAGEWEAVE_REPORT_JUDGE_TOTAL_ATTEMPTS", "0")
    fatal = lw.score_period_reports(
        slices,
        [],
        judge_transport=lambda _body: (_ for _ in ()).throw(RuntimeError("certificate verify failed")),
    )
    assert fatal[0]["judge"]["source"] == "unavailable"
    assert "certificate verify failed" in fatal[0]["judge"]["rationale"]
    assert fatal[1]["judge"]["rationale"] == "judge transport disabled after fatal transport failure"

    monkeypatch.setattr(
        lw,
        "derive_dichotomous_judge_via_llm",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("certificate verify failed")),
    )
    no_cause = lw.score_period_reports(
        slices[:1],
        [],
        judge_transport=lambda _body: {},
    )
    assert "certificate verify failed" in no_cause[0]["judge"]["rationale"]


def test_factor_item_parser_preserves_boolean_judge_observations() -> None:
    """Accept JSON boolean item scores without treating them as missing evidence."""
    items = [{"item_id": "factor-yes"}, {"item_id": "factor-no"}]

    assert lw.parse_factor_item_responses(
        {
            "item_scores": [
                {"item_id": "factor-yes", "response": True},
                {"item_id": "factor-no", "response": False},
            ]
        },
        items,
    ) == [
        {"item_id": "factor-yes", "response": 1},
        {"item_id": "factor-no", "response": 0},
    ]


def test_keyman_customer_master_and_judge_edge_contracts() -> None:
    """Preserve evidence ownership across uncommon, but valid, product inputs."""
    our_side, counterpart_side = lw.separate_keyman_sides(
        [{"person_name": "Counterparty", "org_name": "Partner Org"}],
        [],
        title="[Partner Org] meeting",
    )
    assert our_side == []
    assert counterpart_side == [{"person_name": "Counterparty", "org_name": "Partner Org"}]

    generic = lw.derive_keymen_via_llm(
        "Status update",
        transport=lambda request: (
            {"keymen": [{"person_name": "First"}, {"person_name": "Second"}]}
            if request["extract_side"] == "our_side"
            else {}
        ),
    )
    assert generic["our_side"] == [{"person_name": "First", "org_name": ""}]
    assert generic["counterpart_side"] == [{"person_name": "Second", "org_name": ""}]

    one_sided = lw.derive_keymen_via_llm(
        "Status update",
        transport=lambda request: (
            {"keymen": [{"person_name": "Our"}]}
            if request["extract_side"] == "our_side"
            else {"counterpart_side": [{"person_name": "Counter"}]}
        ),
    )
    assert one_sided["our_side"] == [{"person_name": "Our", "org_name": ""}]
    assert one_sided["counterpart_side"] == [{"person_name": "Counter", "org_name": ""}]

    changed_owner = lw.derive_keymen_via_llm(
        "Status update",
        transport=lambda request: (
            {"our_side": [{"person_name": "Author"}]}
            if request["extract_side"] == "our_side"
            else {}
        ),
        authors={"created_by": "Author", "changed_by": "Editor"},
    )
    assert changed_owner["counterpart_side"] == [{"person_name": "Editor", "org_name": ""}]
    assert lw.normalize_keyman_side(["", None]) == []
    same_name = lw.normalize_keyman_side(
        [
            {"person_name": "Alex Kim", "org_name": "Org", "rank": "Director", "title": "Lead"},
            {"person_name": "Alex Kim", "org_name": "Org", "rank": "Manager", "title": "Lead"},
        ]
    )
    assert lw.keyman_person_key(same_name[0]) != lw.keyman_person_key(same_name[1])
    assert lw.separate_keyman_sides([], [{"person_name": "Author"}], authors={"created_by": "Author"}) == (
        [],
        [{"person_name": "Author", "org_name": ""}],
    )
    same_owner = lw.derive_keymen_via_llm(
        "Status update",
        transport=lambda request: {"our_side": [{"person_name": "Author"}]} if request["extract_side"] == "our_side" else {},
        authors={"created_by": "Author", "changed_by": "Author"},
    )
    assert same_owner["counterpart_side"] == []
    assert lw.extract_keymen("김철수님, 김철수팀장") == ["김철수"]


def test_keyman_institution_actor_survives_normalization_and_kg() -> None:
    """Keep an institution as an organization node, not a fabricated person."""
    assert lw.keyman_actor_name("Direct label") == "Direct label"
    assert lw.keyman_actor_name(42) == ""
    assert lw.keyman_organization_name("Direct organization") == ""
    institution = {
        "actor_type": "institution",
        "actor_name": "Grid Authority",
        "organization_name": "Grid Authority",
        "affiliated_organization_name": "National Energy Group",
        "rank": "",
        "title": "Regulator",
        "node": "authority-node",
        "entity": "institution",
        "relationship": "oversees",
        "direction": "source_to_target",
    }
    normalized = lw.normalize_keyman_side([institution])
    assert normalized[0]["actor_type"] == "organization"
    assert normalized[0]["actor_name"] == "Grid Authority"
    assert normalized[0]["organization_name"] == "Grid Authority"
    assert "person_name" not in normalized[0]
    assert normalized[0]["affiliated_organization_name"] == "National Energy Group"
    assert normalized[0]["node"] == "authority-node"
    assert normalized[0]["relationship"] == "oversees"
    assert normalized[0]["direction"] == "source_to_target"

    graph = lw.build_knowledge_graph(
        [
            {
                "type": "document",
                "document_no": "DOC-INSTITUTION",
                "title_sample": "Authority review",
                "keyman_counterpart_side": normalized,
            }
        ],
        [],
    )
    actor_nodes = [node for node in graph["nodes"] if node.get("label") == "Grid Authority"]
    assert len(actor_nodes) == 1
    assert actor_nodes[0]["type"] == "organization"
    assert not any(node.get("type") == "person" and node.get("label") == "Grid Authority" for node in graph["nodes"])


def test_keyman_team_and_same_name_actor_qualifiers_are_preserved() -> None:
    """Separate meso units and same-name people by actor and organization metadata."""
    rows = lw.normalize_keyman_side(
        [
            {
                "actor_type": "team",
                "actor_name": "Delivery Team",
                "affiliated_organization_name": "Our Group",
                "relationship": "unitOf",
            },
            {
                "actor_type": "person",
                "actor_name": "Alex Kim",
                "organization_name": "Org A",
                "rank": "Director",
                "title": "Lead",
            },
            {
                "actor_type": "person",
                "actor_name": "Alex Kim",
                "organization_name": "Org B",
                "rank": "Manager",
                "title": "Lead",
            },
            {
                "actor_type": "person",
                "actor_name": "Solo Person",
                "canonical_name": "Solo Person Canonical",
                "affiliation_status": "observed",
            },
        ]
    )
    assert rows[0]["actor_type"] == "team"
    assert rows[0]["actor_name"] == "Delivery Team"
    assert rows[0]["affiliated_organization_name"] == "Our Group"
    assert rows[1]["person_name"] == rows[2]["person_name"] == "Alex Kim"
    assert lw.keyman_person_key(rows[1]) != lw.keyman_person_key(rows[2])
    assert rows[3]["canonical_name"] == "Solo Person Canonical"
    assert rows[3]["affiliation_status"] == "observed"
    assert lw._keyman_affinity_tokens(
        {
            "keyman_our_side": [
                {"actor_type": "organization", "actor_name": "Authority"},
                {"actor_type": "team", "actor_name": "Delivery Team"},
            ]
        }
    ) == {"org:authority", "team:delivery team"}

    graph = lw.build_knowledge_graph(
        [{"type": "document", "document_no": "DOC-TEAM", "title_sample": "Team review", "keyman_our_side": [rows[0]]}],
        [],
    )
    team_nodes = [node for node in graph["nodes"] if node.get("label") == "Delivery Team"]
    assert len(team_nodes) == 1
    assert team_nodes[0]["type"] == "team"
    orphan_responsibility = lw.build_knowledge_graph(
        [
            {
                "type": "document",
                "document_no": "DOC-ORPHAN-ROLE",
                "title_sample": "Unscoped role",
                "roles_and_responsibilities": [
                    {"actor_type": "organization", "actor_name": "Unscoped Authority", "role": "Reviewer"}
                ],
            }
        ],
        [],
    )
    assert any(node.get("label") == "Unscoped Authority" for node in orphan_responsibility["nodes"])

    bound = lw.bind_customer_master_document_nos(
        {
            "accounts": [
                {"account_name": "Existing", "document_nos": ["DOC-OLD"]},
                {"account_name": "", "document_nos": []},
            ]
        },
        [{"document_no": "DOC-NEW", "title_sample": "Existing customer update"}],
    )
    assert bound["accounts"][0]["document_nos"] == ["DOC-OLD"]
    assert bound["accounts"][1]["document_nos"] == []

    ladder = lw.complete_customer_master_ladder(
        {
            "accounts": [{"account_name": "Group Korea HQ Plant", "tier": "plant", "document_nos": []}],
            "edges": [
                {"parent": "Group", "child": "Group Korea"},
                {"parent": "Group Korea", "child": "Group Korea HQ"},
                {"parent": "Group Korea HQ", "child": "Group Korea HQ Plant"},
            ],
        }
    )
    assert {edge["child"] for edge in ladder["edges"]} == {
        "Group Korea",
        "Group Korea HQ",
        "Group Korea HQ Plant",
    }

    unavailable = lw.derive_customer_master_via_llm(
        [{"document_no": "DOC-1", "title_sample": "No organisation supplied"}],
        transport=lambda _request: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert unavailable["source"] == "empty"
    assert unavailable["request"] == {"task": "customer_master", "document_count": 1}

    merged = lw.merge_customer_master_into_tree(
        {"nodes": ["Corp"], "edges": [], "parent_of": {}},
        {"edges": [{"parent": "", "child": "Orphan"}]},
    )
    assert merged["nodes"] == ["Corp"]
    with pytest.raises(ValueError, match="dichotomous_judge_requires_pass_or_fail"):
        lw.parse_dichotomous_judge({"verdict": "pending"})


def test_period_scoring_and_fast_mlsirm_connector_error_contracts(monkeypatch) -> None:
    """Keep report scoring useful when its optional calibrated connector is unavailable."""
    slices = lw.build_period_report_slices(
        [
            {"type": "row", "document_no": "ROW-1", "owner_pu": "PU-ROW"},
            {"type": "document", "document_no": "DOC-1", "owner_pu": "PU-1", "acthguid": "THREAD-1"},
        ]
    )
    assert all("ROW-1" not in report["document_nos"] for report in slices)
    first = dict(slices[0])
    first["document_nos"] = ["DOC-1"]
    scored = lw.score_period_reports(
        [first],
        [{"document_no": "DOC-1", "title_sample": "Customer review"}],
        judge_transport=lambda _body: (_ for _ in ()).throw(RuntimeError("judge offline")),
        mlsirm_transport=lambda _body: {},
    )
    assert scored[0]["judge"]["source"] == "unavailable"
    assert scored[0]["linking_status"] == "unavailable"
    assert scored[0]["linking_source"] == "unavailable"
    assert scored[0]["linked_scores"] == []

    monkeypatch.setenv("LINEAGEWEAVE_MLSIRM_URL", "https://mlsirm.invalid")
    monkeypatch.setenv("LINEAGEWEAVE_MLSIRM_TOKEN", "test-token")
    monkeypatch.setattr(lw, "verified_gateway_ssl_context", lambda: object())
    http_payloads = iter([{"linked_scores": []}, []])
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(next(http_payloads)),
    )
    http_transport = lw.make_mlsirm_transport()
    assert http_transport({"payload": {}}) == {"linked_scores": []}
    with pytest.raises(RuntimeError, match="fast_mlsirm_non_object"):
        http_transport({"payload": {}})

    configured_python = "/test/fast-mlsirm-python"
    monkeypatch.setenv("LINEAGEWEAVE_MLSIRM_PYTHON", configured_python)
    monkeypatch.setattr(lw.Path, "is_file", lambda path: str(path) == configured_python)
    monkeypatch.setattr(lw.os, "access", lambda path, _mode: str(path) == configured_python)
    assert lw.discover_fast_mlsirm_python() == configured_python

    local_results = iter(
        [
            SimpleNamespace(returncode=1, stderr="connector failed", stdout=""),
            SimpleNamespace(returncode=0, stderr="", stdout="[]"),
            SimpleNamespace(returncode=0, stderr="", stdout='{"ok": true, "linked_scores": []}'),
        ]
    )
    monkeypatch.setattr(lw, "discover_fast_mlsirm_python", lambda: configured_python)
    monkeypatch.setattr(lw.subprocess, "run", lambda *_args, **_kwargs: next(local_results))
    local_transport = lw.make_local_fast_mlsirm_transport()
    with pytest.raises(RuntimeError, match="connector failed"):
        local_transport({"payload": {}})
    with pytest.raises(RuntimeError, match="fast_mlsirm_local_non_object"):
        local_transport({"payload": {}})
    assert local_transport({"payload": {}}) == {"ok": True, "linked_scores": []}


def test_knowledge_graph_helpers_keep_content_and_walks_bounded(monkeypatch) -> None:
    """Retain only document-scoped KG material and honor adaptive traversal limits."""
    untouched = lw.attach_document_content_knowledge_graph(
        {"nodes": [{"id": "kg:document:OTHER", "type": "document"}], "edges": []},
        "DOC-1",
        {"blocks": [{"block_index": 1, "text_sha256": "hash"}]},
    )
    assert untouched["nodes"] == [{"id": "kg:document:OTHER", "type": "document"}]

    graph = {"nodes": [{"id": "kg:document:DOC-1", "type": "document", "document_no": "DOC-1"}], "edges": []}
    content = lw.attach_document_content_knowledge_graph(
        graph,
        "DOC-1",
        {
            "blocks": [
                {
                    "block_index": 0,
                    "block_kind": "paragraph",
                    "source_evidence_id": "ROW-1",
                    "text_sha256": "hash-1",
                    "format_hints": ["bold"],
                }
            ]
        },
    )
    content = lw.attach_document_content_knowledge_graph(
        content,
        "DOC-1",
        {"blocks": [{"block_index": 0, "source_evidence_id": "ROW-1", "text_sha256": "hash-1"}]},
    )
    assert len([edge for edge in content["edges"] if edge["relation"] == "document_content_block"]) == 1

    customer_graph = lw.attach_customer_master_knowledge_graph(
        graph,
        {
            "accounts": [
                {"account_name": "Scoped", "document_nos": ["DOC-1"]},
                {"account_name": "Unscoped", "document_nos": []},
                "not-an-account",
            ],
            "edges": [
                {"parent": "Scoped", "child": "Unscoped"},
                "not-an-edge",
            ],
        },
    )
    assert "Scoped" in {str(node.get("label") or "") for node in customer_graph["nodes"]}
    assert "Unscoped" not in {node.get("label") for node in customer_graph["nodes"]}

    assert lw.refresh_document_keyman_knowledge_graph(graph, {"document_no": ""}) == graph
    assert lw._hydrate_knowledge_nodes(object(), []) == {}
    assert lw._knowledge_edges_touching(object(), []) == []
    assert lw.load_persisted_keyman_neighborhood(object(), "") == {
        "person_name": "",
        "nodes": [],
        "edges": [],
        "depths": {},
    }

    fixture_nodes = {
        "seed": {"id": "seed", "type": "person", "label": "Seed"},
        "neighbor": {"id": "neighbor", "type": "organization", "label": "Neighbor"},
    }
    monkeypatch.setattr(
        lw,
        "_hydrate_knowledge_nodes",
        lambda _connection, identifiers: {
            identifier: fixture_nodes[identifier]
            for identifier in identifiers
            if identifier in fixture_nodes
        },
    )
    monkeypatch.setattr(
        lw,
        "_knowledge_edges_touching",
        lambda _connection, identifiers: (
            [{"source": "seed", "target": "neighbor", "relation": "member_of"}]
            if "seed" in identifiers
            else []
        ),
    )
    star = lw.load_persisted_kg_star(object(), ["seed"], hop_limit=2, node_limit=2)
    assert {node["id"] for node in star["nodes"]} == {"seed", "neighbor"}
    assert star["edges"] == [{"source": "seed", "target": "neighbor", "relation": "member_of"}]

    assert lw.knowledge_node_id(("corp", None, "pu")) == "corp:pu"
    assert lw.json_safe_depth_map({("corp", "pu"): 2, None: 3}) == {"corp:pu": 2}
    bounded = lw.knowledge_neighborhood(
        {
            "nodes": [
                {"id": "person", "type": "person", "kg_depth": 3},
                {"id": "other", "type": "organization", "kg_depth": 2},
            ],
            "edges": [{"source": "person", "target": "other", "relation": "cross_pu_transaction"}],
        },
        ["person"],
        depth=1,
    )
    assert [node["id"] for node in bounded["nodes"]] == ["person"]
    assert lw.knowledge_neighborhood(graph, ["missing"]) == {"nodes": [], "edges": [], "depths": {}}
    duplicated = lw.attach_document_content_knowledge_graph(
        graph,
        "DOC-1",
        {"blocks": [
            {"block_index": 0, "source_evidence_id": "ROW-1", "text_sha256": "same"},
            {"block_index": 0, "source_evidence_id": "ROW-1", "text_sha256": "same"},
        ]},
    )
    assert len(duplicated["edges"]) == 1
    duplicated_customer = lw.attach_customer_master_knowledge_graph(
        graph,
        {
            "accounts": [
                {"account_name": "Parent", "document_nos": ["DOC-1"]},
                {"account_name": "Child", "document_nos": ["DOC-1"]},
            ],
            "edges": [{"parent": "Parent", "child": "Child"}, {"parent": "Parent", "child": "Child"}],
        },
    )
    assert len([edge for edge in duplicated_customer["edges"] if edge["relation"] == "customer_affiliate"]) == 1
    keyman_document = {"type": "document", "document_no": "DOC-1", "corp_code": "CORP", "owner_pu": "PU", "keyman_our_side": [{"person_name": "Owner"}]}
    refreshed = lw.refresh_document_keyman_knowledge_graph(graph, keyman_document)
    refreshed = lw.refresh_document_keyman_knowledge_graph(refreshed, keyman_document)
    assert len([edge for edge in refreshed["edges"] if edge["relation"] == "document_corp"]) == 1
    assert lw.load_persisted_kg_star(object(), ["seed"], hop_limit=0)["edges"] == []
    assert [node["id"] for node in lw.knowledge_neighborhood(
        {"nodes": [{"id": "seed", "type": "document"}, {"id": "", "type": "person"}], "edges": [{"source": "seed", "target": "missing", "relation": "related"}]},
        ["seed"],
    )["nodes"]] == ["seed"]


def test_relatedness_and_inference_helpers_apply_evidence_guardrails(monkeypatch) -> None:
    """Keep affinity edges bounded and prevent inferred links from becoming facts."""
    assert lw._inferred_affiliate_edges([], {"parent_of": {}}) == []
    parent_of = {f"Child {index:03}": f"Parent {index:03}" for index in range(65)}
    affiliate_nodes = [
        node
        for index in range(65)
        for node in (
            {"id": f"parent-{index}", "title_sample": f"Parent {index:03}"},
            {"id": f"child-{index}", "title_sample": f"Child {index:03}"},
        )
    ]
    assert len(lw._inferred_affiliate_edges(affiliate_nodes, {"parent_of": parent_of})) == 64
    assert lw._keyman_affinity_tokens(
        {"keyman_our_side": "invalid", "keyman_counterpart_side": [{}, {"org_name": "Partner"}]}
    ) == {"org:partner"}
    assert len(
        lw._inferred_keyman_affinity_edges(
            [
                {"id": "DOC-1", "document_no": "1", "keyman_our_side": [{"person_name": "Alex"}]},
                {"id": "DOC-1", "document_no": "2", "keyman_our_side": [{"person_name": "Alex"}]},
                {"id": "DOC-2", "document_no": "3", "keyman_our_side": [{"person_name": "Alex"}]},
            ],
            limit=1,
        )
    ) == 1

    source = {"id": "source", "entity_role": "고객", "acthguid": "THREAD-1"}
    predicted = lw._predicted_entity_role_edges(
        source,
        [
            {},
            source,
            {"id": "same-thread", "entity_role": "고객", "acthguid": "THREAD-1"},
            {"id": "wrong-role", "entity_role": "시장", "acthguid": "THREAD-2"},
            {"id": "match-1", "entity_role": "고객", "acthguid": "THREAD-2"},
            {"id": "match-2", "entity_role": "고객", "acthguid": "THREAD-3"},
        ],
        limit=1,
    )
    assert [edge["relation"] for edge in predicted] == ["entity_role_affinity"]
    assert lw._predicted_entity_role_edges({}, []) == []

    existing = {
        "source": "source",
        "target": "match-1",
        "relation": "entity_role_affinity",
        "evidence_status": lw.EVIDENCE_PREDICTED,
    }
    merged = lw.merge_predicted_relatedness_edges(
        [existing],
        [
            {"evidence_status": lw.EVIDENCE_OBSERVED, "relation": "ignored", "source": "source", "target": "match-1"},
            {"evidence_status": lw.EVIDENCE_PREDICTED, "relation": "row_successor", "source": "source", "target": "match-1"},
            {"evidence_status": lw.EVIDENCE_PREDICTED, "relation": "missing", "source": "missing", "target": "match-1"},
            existing,
            {"evidence_status": lw.EVIDENCE_PREDICTED, "relation": "new-hypothesis", "source": "source", "target": "match-1"},
        ],
        [{"id": "source"}, {"id": "match-1"}],
    )
    assert [edge["relation"] for edge in merged] == ["entity_role_affinity", "new-hypothesis"]

    executed: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda _connection, _sql, params=(): [{"present": 1}] if params and params[0] == "existing" else [],
    )
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): executed.append((sql, tuple(params))),
    )
    written = lw.persist_lineage_relatedness_edges(
        object(),
        [
            {"evidence_status": lw.EVIDENCE_OBSERVED, "relation": "ignored"},
            {"evidence_status": lw.EVIDENCE_INFERRED, "relation": "row_successor"},
            {"evidence_status": lw.EVIDENCE_PREDICTED, "relation": "kept", "source": "existing", "target": "target"},
            {"evidence_status": lw.EVIDENCE_PREDICTED, "relation": "kept", "source": "new", "target": "target"},
        ],
    )
    assert written == 1
    assert executed[0][1][:4] == ("new", "target", "kept", lw.EVIDENCE_PREDICTED)

    graph = {
        "nodes": [
            {"id": "document", "type": "document", "document_no": "DOC-1", "label": "Document"},
            {"id": "other", "type": "organization", "label": "Other"},
            {"id": "outside", "type": "organization", "label": "Outside"},
        ],
        "edges": [
            {"source": "document", "target": "other", "relation": "hypothesis", "evidence_status": lw.EVIDENCE_INFERRED},
            {"source": "document", "target": "other", "relation": "hypothesis", "evidence_status": lw.EVIDENCE_INFERRED},
            {"source": "document", "target": "outside", "relation": "prediction", "evidence_status": lw.EVIDENCE_PREDICTED},
            {"source": "outside", "target": "other", "relation": "outside", "evidence_status": lw.EVIDENCE_OBSERVED, "evidence_id": "ROW-OUT"},
            {"source": "document", "target": "other", "relation": "observed", "evidence_status": lw.EVIDENCE_OBSERVED, "evidence_id": "ROW-1"},
            {"source": "document", "target": "other", "relation": "duplicate", "evidence_status": lw.EVIDENCE_OBSERVED, "evidence_id": "ROW-1"},
        ],
    }
    candidates = lw.inference_candidates_for_document(graph, "DOC-1")
    assert len(candidates) == 2
    assert len(lw.inference_candidates_for_document(graph, "DOC-1", limit=1)) == 1
    evidence = lw.search_internal_inference_evidence(graph, candidates[0], limit=1)
    assert len(evidence) == 1
    assert evidence[0]["evidence_id"] in {"ROW-OUT", "ROW-1"}
    assert evidence[0]["evidence_kind"] == "internal"
    assert lw.customer_master_sample_documents(
        [{"document_no": "DOC-1", "title_sample": "fallback title", "keyman_our_side": [{"person_name": "Owner"}]}]
    ) == [{"document_no": "DOC-1", "title_sample": "fallback title", "keyman_our_side": [{"person_name": "Owner"}]}]
    labels = lw.inference_organization_labels(
        {
            "nodes": [
                {"id": "start", "type": "document", "label": "Document"},
                {"id": "person", "type": "person", "label": "Person"},
                {"id": "org-a", "type": "organization", "label": "Vendor"},
                {"id": "org-b", "type": "organization", "label": "Vendor"},
                {"id": "tail", "type": "person", "label": "Tail"},
            ],
            "edges": [
                {"source": "start", "target": "missing"},
                {"source": "start", "target": "person"},
                {"source": "person", "target": "org-a"},
                {"source": "person", "target": "org-b"},
                {"source": "org-a", "target": "tail"},
            ],
        },
        {"source_node": "start"},
    )
    assert labels == ["Vendor"]


def test_lineage_override_storage_and_review_is_tenant_scoped(monkeypatch) -> None:
    """Review only visible same-corp candidates and persist normalized decisions."""
    state = {"ready": False}
    statements: list[tuple[str, tuple[object, ...]]] = []
    rows = [
        {"source_node": "doc:MISSING", "target_node": "doc:PUBLIC-TARGET", "relation_name": "topic_affinity", "evidence_status": lw.EVIDENCE_INFERRED},
        {"source_node": "doc:PRIVATE-SOURCE", "target_node": "doc:PUBLIC-TARGET", "relation_name": "topic_affinity", "evidence_status": lw.EVIDENCE_INFERRED},
        {"source_node": "doc:PUBLIC-SOURCE", "target_node": "doc:PRIVATE-TARGET", "relation_name": "topic_affinity", "evidence_status": lw.EVIDENCE_INFERRED},
        {"source_node": "doc:PUBLIC-SOURCE", "target_node": "doc:PUBLIC-TARGET", "relation_name": "topic_affinity", "evidence_status": lw.EVIDENCE_INFERRED, "acthguid": "THREAD-1", "reason": "shared topic"},
    ]
    documents = [
        {"document_no": "PRIVATE-SOURCE", "corp_code": "CORP_A", "owner_pu": "PU_B", "title_sample": "Private source", "visibility_code": lw.VISIBILITY_PRIVATE},
        {"document_no": "PUBLIC-SOURCE", "corp_code": "CORP_A", "owner_pu": "PU_B", "title_sample": "Public source", "visibility_code": lw.VISIBILITY_PUBLIC},
        {"document_no": "PRIVATE-TARGET", "corp_code": "CORP_A", "owner_pu": "PU_B", "title_sample": "Private target", "visibility_code": lw.VISIBILITY_PRIVATE},
        {"document_no": "PUBLIC-TARGET", "corp_code": "CORP_A", "owner_pu": "PU_B", "title_sample": "Public target", "visibility_code": lw.VISIBILITY_PUBLIC},
    ]
    override = {"source_node": "doc:PUBLIC-SOURCE", "target_node": "doc:PUBLIC-TARGET", "relation_name": "topic_affinity", "override_status": "suppressed", "reason": "reviewed"}

    monkeypatch.setattr(
        lw,
        "_database_table_exists",
        lambda _connection, table: state["ready"] and table in {lw.ANALYSIS_EDGE_TABLE, lw.ANALYSIS_LINEAGE_OVERRIDE_TABLE},
    )
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda _connection, sql, _params=(): (
            [override] if lw.ANALYSIS_LINEAGE_OVERRIDE_TABLE in sql
            else documents if lw.ANALYSIS_DOCUMENT_TABLE in sql
            else rows if lw.ANALYSIS_EDGE_TABLE in sql
            else []
        ),
    )
    assert lw.load_lineage_edge_overrides(object()) == []
    assert lw.load_lineage_review_edges(object(), {"corp_code": "CORP_A", "pu_code": "PU_A", "roles": ["reader"]}) == {"items": [], "total": 0}
    state["ready"] = True
    review = lw.load_lineage_review_edges(
        object(),
        {"corp_code": "CORP_A", "pu_code": "PU_A", "roles": ["reader"]},
        query="public",
        limit=2,
    )
    assert review["total"] == 1
    assert review["items"][0]["override_status"] == "suppressed"
    assert review["items"][0]["source_title"] == "Public source"
    with pytest.raises(ValueError, match="lineage_review_query_too_long"):
        lw.load_lineage_review_edges(object(), {"corp_code": "CORP_A"}, query="x" * 129)
    monkeypatch.setattr(lw, "_database_exec", lambda _connection, sql, params=(): statements.append((sql, tuple(params))))
    lw.persist_lineage_edge_override(
        object(),
        source_node="doc:PUBLIC-SOURCE",
        target_node="doc:PUBLIC-TARGET",
        relation_name="topic_affinity",
        override_status="restored",
        reason="rechecked",
        updated_by="admin",
    )
    assert statements and statements[0][1][-1] == "admin"
    with pytest.raises(ValueError, match="unknown"):
        lw.persist_lineage_edge_override(
            object(), source_node="source", target_node="target", relation_name="topic", override_status="invalid", reason="", updated_by="admin"
        )


def test_external_evidence_and_zotero_contracts_never_claim_unverified_success(monkeypatch) -> None:
    """Exercise the network boundaries entirely through controlled local transports."""
    monkeypatch.delenv("LINEAGEWEAVE_SEARXNG_URL", raising=False)
    assert lw.search_external_inference_evidence(["One", "Two"])["mode"] == "not_configured"
    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "https://search.invalid")
    monkeypatch.setattr(lw, "verified_ssl_context", lambda _name: object())
    monkeypatch.setattr(lw.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response([]))
    assert lw.search_external_inference_evidence(["One", "Two"])["mode"] == "unavailable"
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "results": [
                    "invalid",
                    {"url": "mailto:not-allowed@example.test", "title": "Ignored"},
                    {"url": "https://evidence.example/paper", "title": "Evidence", "content": "Bounded"},
                ]
            }
        ),
    )
    searched = lw.search_external_inference_evidence(["One", "Two"], limit=1)
    assert searched["mode"] == "searxng"
    assert [item["source_uri"] for item in searched["evidence"]] == ["https://evidence.example/paper"]

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "http://localhost:23119/api")
    assert lw.zotero_local_api_url() == "http://localhost:23119/api"

    class _StatusResponse(_Response):
        status = 204

    monkeypatch.setattr(lw.urllib.request, "urlopen", lambda *_args, **_kwargs: _StatusResponse({}))
    assert lw.probe_zotero_local_api()["status"] == "reachable"
    paper = {
        "paper_id": "paper-1",
        "title": "Method paper",
        "authors": "Researcher",
        "year": 2026,
        "source_uri": "https://evidence.example/paper",
        "purpose": "verification",
        "full_text": "open text",
    }
    stored = lw.store_oa_method_paper(
        paper,
        transport=lambda _payload: {"status_code": 202, "body": [{"key": "ITEM-1"}]},
    )
    assert stored["store_status"] == "stored"
    assert stored["zotero_item_key"] == "ITEM-1"
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            {"results": [
                {"url": "https://evidence.example/one", "title": "One"},
                {"url": "https://evidence.example/two", "title": "Two"},
            ]}
        ),
    )
    assert len(lw.search_external_inference_evidence(["One", "Two"], limit=2)["evidence"]) == 2
    monkeypatch.setattr(lw.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response({"results": []}))
    assert lw.search_external_inference_evidence(["One", "Two"])["evidence"] == []
    assert lw.store_oa_method_paper(
        paper,
        transport=lambda _payload: {"status_code": 500, "body": "unexpected"},
    )["store_status"] == "unreachable"

    persisted: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(lw, "ensure_method_paper_tables", lambda _connection: None)
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): persisted.append((sql, tuple(params))),
    )
    assert lw.persist_method_paper_records(
        object(),
        [{"store_status": "invalid"}, stored],
    ) == 1
    assert persisted[0][1][0] == "paper-1"


def test_attach_product_fields_uses_the_local_work_item_mapper_when_live_tasks_are_absent(monkeypatch) -> None:
    """Do not require an LLM call merely to expose an already-derived issue ticket."""
    monkeypatch.setattr(lw, "derive_issue_tickets", lambda _document: [{"ticket_id": "T-1", "title": "Follow up"}])
    monkeypatch.setattr(
        lw,
        "map_issue_to_work_items",
        lambda ticket, _document: {
            "todo": {"ticket_id": ticket["ticket_id"], "body": "Follow up"},
            "calendar": {"ticket_id": ticket["ticket_id"], "body": "Follow up"},
        },
    )
    attached = lw.attach_product_fields({"document_no": "DOC-1", "title_sample": "Follow up"})
    assert attached["todo_items"] == [{"ticket_id": "T-1", "body": "Follow up"}]
    assert attached["calendar_items"] == [{"ticket_id": "T-1", "body": "Follow up"}]


def test_runtime_helpers_cover_empty_and_bounded_paths(monkeypatch, tmp_path) -> None:
    """Keep empty inputs, persisted fragments, and output files safe and deterministic."""
    assert lw.normalize_ontology_relationship_verification({"decision": "unknown"}, ["ROW-1"])["decision"] == "insufficient"
    monkeypatch.setattr(lw, "unwrap_product_llm_object", lambda _response: [])
    assert lw.parse_issue_work_content({}) == {}
    monkeypatch.undo()
    assert lw.parse_dichotomous_judge({"verdict": "no"})["verdict"] == "fail"
    assert lw.score_period_reports(
        [{"report_id": "R-1", "slice_key": "PU-1", "document_nos": []}],
        [],
    )[0]["judge"]["source"] == "unavailable"

    monkeypatch.delenv("LINEAGEWEAVE_MLSIRM_PYTHON", raising=False)
    monkeypatch.setattr(lw.Path, "is_file", lambda _path: False)
    assert lw.discover_fast_mlsirm_python() is None
    monkeypatch.setattr(lw, "discover_fast_mlsirm_python", lambda: None)
    with pytest.raises(RuntimeError, match="fast_mlsirm_local_unavailable"):
        lw.make_local_fast_mlsirm_transport()
    assert lw.build_org_unit_affiliate_tree([{"corp_code": "", "owner_pu": "PU-1"}])["nodes"] == []
    assert lw.collect_affiliate_labels([None, ""]) == []
    assert lw.build_affiliate_tree(["Alpha", "Beta"])["edges"] == []
    assert lw.document_org_unit_labels(
        {"corp_code": "CORP", "keyman_our_side": [None], "keyman_counterpart_side": ["Partner"]}
    ) == ["Corp CORP", "Partner"]
    assert lw.build_org_unit_affiliate_tree([{"corp_code": "CORP", "owner_pu": ""}])["edges"] == []
    assert lw.build_affiliate_tree(["Alpha", "Alphax"])["edges"] == []
    row_without_scope = lw.build_knowledge_graph(
        [
            {"type": "document", "document_no": "DOC-1", "title_sample": "Fixture"},
            {"type": "row", "document_no": "DOC-1", "guid": "ROW-1", "event": "opened"},
        ],
        [],
    )
    assert any(node["type"] == "event" for node in row_without_scope["nodes"])

    person_id = lw._knowledge_id("person", "llm:Existing")
    refreshed = lw.refresh_document_keyman_knowledge_graph(
        {
            "nodes": [
                {"id": "kg:document:DOC-1", "type": "document", "document_no": "DOC-1"},
                {"id": person_id, "type": "person", "identity_source": "source", "document_nos": ["DOC-2"]},
            ],
            "edges": [],
        },
        {
            "type": "document",
            "document_no": "DOC-1",
            "title_sample": "Existing",
            "keyman_our_side": [{"person_name": "Existing"}],
        },
    )
    existing = next(node for node in refreshed["nodes"] if node["id"] == person_id)
    assert existing["document_nos"] == ["DOC-1", "DOC-2"]

    monkeypatch.setattr(
        lw,
        "_database_table_exists",
        lambda _connection, table_name: table_name == lw.ANALYSIS_KG_NODE_TABLE,
    )
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda _connection, _sql, _params=(): [
            {"node_id": "kg-1", "node_type": "person", "label": "Known", "document_no": "DOC-1", "metadata_payload": '{"scope": "verified"}'},
            {"node_id": "", "metadata_payload": {}},
        ],
    )
    hydrated = lw._hydrate_knowledge_nodes(object(), ["kg-1"])
    assert hydrated["kg-1"]["scope"] == "verified"
    assert lw._knowledge_edges_touching(object(), ["kg-1"]) == []

    limited = lw.knowledge_neighborhood(
        {
            "nodes": [{"id": "seed", "type": "person"}, {"id": "a", "type": "organization"}, {"id": "b", "type": "organization"}],
            "edges": [{"source": "seed", "target": "a", "relation": "member_of"}, {"source": "seed", "target": "b", "relation": "member_of"}],
        },
        ["seed"],
        limit=2,
    )
    assert len(limited["nodes"]) == 2
    assert lw._keyman_affinity_tokens({"keyman_our_side": ["not-a-row"]}) == set()
    assert lw.search_internal_inference_evidence(
        {"nodes": [], "edges": [{"source": "outside", "target": "far", "evidence_id": "ROW-X"}]},
        {"source_node": "source", "target_node": "target"},
    ) == []

    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "http://remote.invalid")
    monkeypatch.delenv("LINEAGEWEAVE_DEV_MODE", raising=False)
    with pytest.raises(RuntimeError, match="must be HTTPS"):
        lw._searxng_search_url()
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "https://zotero.invalid")
    assert lw.zotero_local_api_url() == "https://zotero.invalid"
    monkeypatch.setenv("LINEAGEWEAVE_ZOTERO_API", "https://user:pass@zotero.invalid")
    with pytest.raises(RuntimeError, match="is invalid"):
        lw.zotero_local_api_url()

    assert lw.build_event_lineage({"document_no": "DOC-1", "document_events": ["invalid"]}, [])["beads"]
    assert lw.build_access_directory([SimpleNamespace(corp_code="", pu_code="")])["UNASSIGNED"]["units"]
    output_json = tmp_path / "payload.json"
    lw._write_outputs({"nodes": [], "edges": []}, output_json, None)
    assert output_json.exists()
    lw._write_outputs({"nodes": [], "edges": []}, None, None)
    assert lw._build_analytics([], [], [])["avg_rows_per_document"] == 0
    with pytest.raises(PermissionError, match="unauthenticated"):
        lw.filter_payload_for_actor({}, None)
    filtered = lw.filter_payload_for_actor(
        {
            "nodes": [
                {"id": "doc:DOC-1", "type": "document", "document_no": "DOC-1", "corp_code": "CORP", "owner_pu": "PU", "visibility": "public"},
                {"id": "org:CORP", "type": "organization", "label": "Corp CORP"},
            ],
            "edges": [],
        },
        {"corp_code": "CORP", "pu_code": "PU", "roles": ["reader"]},
    )
    assert [node["id"] for node in filtered["nodes"]] == ["doc:DOC-1"]


def test_normalized_persistence_writes_nonempty_structures(monkeypatch) -> None:
    """Exercise the 3NF write paths without requiring a live database mutation."""
    class Cursor:
        def __init__(self) -> None:
            self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
            self.executemany_calls: list[tuple[str, list[tuple[object, ...]]]] = []

        def __enter__(self) -> "Cursor":
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
            self.execute_calls.append((sql, params))

        def executemany(self, sql: str, params: list[tuple[object, ...]]) -> None:
            self.executemany_calls.append((sql, params))

    class Connection:
        def __init__(self) -> None:
            self.cursor_value = Cursor()

        def cursor(self) -> Cursor:
            return self.cursor_value

    connection = Connection()
    monkeypatch.setattr(lw, "_database_exec", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(lw, "ensure_content_structure_tables", lambda _connection: None)
    content_counts = lw.persist_document_content_structure(
        connection,
        "DOC-1",
        {
            "blocks": [
                {
                    "block_index": 0,
                    "source_evidence_id": "ROW-1",
                    "block_kind": "paragraph",
                    "source_position": 0,
                    "text_content": "Visible evidence",
                    "text_sha256": "hash",
                    "format_hints": [{"hint_kind": "weight", "hint_value": "bold"}],
                }
            ],
            "assets": [
                {
                    "asset_index": 0,
                    "source_evidence_id": "ROW-1",
                    "source_position": 1,
                    "mime_type": "image/png",
                    "encoded_bytes": 256,
                    "content_kind": "inline_image",
                    "asset_sha256": "asset-hash",
                    "inspection_eligible": True,
                }
            ],
        },
    )
    assert content_counts == {
        "content_block_rows": 1,
        "content_format_hint_rows": 1,
        "content_asset_rows": 1,
    }

    graph = {
        "nodes": [
            {"id": "kg:document:DOC-1", "type": "document", "label": "Document", "document_no": "DOC-1"},
            {"id": "kg:organization:ORG-1", "type": "organization", "label": "Organization", "document_nos": ["DOC-1"]},
        ],
        "edges": [
            {
                "source": "kg:document:DOC-1",
                "target": "kg:organization:ORG-1",
                "relation": "document_customer_entity",
                "evidence_id": "ROW-1",
                "evidence_status": lw.EVIDENCE_OBSERVED,
            }
        ],
    }
    semantic = lw.persist_knowledge_semantic_layer(connection, graph)
    assert semantic["semantic_node_rows"] >= 1
    assert semantic["semantic_edge_rows"] >= 1
    assert lw.persist_knowledge_semantic_layer(
        connection, graph, ensure_schema=False
    )["semantic_edge_rows"] >= 1
    snapshot = lw.persist_knowledge_graph_snapshot(connection, graph)
    assert snapshot["knowledge_node_rows"] == 2
    assert snapshot["knowledge_edge_rows"] == 1
    assert len(connection.cursor_value.executemany_calls) >= 5

    merged, changed = lw.merge_lineage_evidence_into_knowledge_graph(
        {"nodes": graph["nodes"], "edges": []},
        [
            {
                "source": "doc:DOC-1",
                "target": "doc:DOC-1",
                "relation": "related",
                "evidence_status": lw.EVIDENCE_INFERRED,
                "acthguid": "THREAD-1",
                "reason": "first",
            }
        ],
    )
    merged, changed_again = lw.merge_lineage_evidence_into_knowledge_graph(
        merged,
        [
            {
                "source": "doc:DOC-1",
                "target": "doc:DOC-1",
                "relation": "related",
                "evidence_status": lw.EVIDENCE_PREDICTED,
                "reason": "updated",
            }
        ],
    )
    assert changed == 1 and changed_again == 2
    assert merged["edges"][0]["reason"] == "updated"
    sparse, sparse_changed = lw.merge_lineage_evidence_into_knowledge_graph(
        {"nodes": graph["nodes"], "edges": []},
        [{"source": "doc:DOC-1", "target": "doc:DOC-1", "relation": "sparse", "evidence_status": lw.EVIDENCE_OBSERVED}],
    )
    assert sparse_changed == 1 and sparse["edges"][0].get("evidence_id") is None
    assert lw.merge_lineage_evidence_into_knowledge_graph(
        sparse,
        [{"source": "doc:DOC-1", "target": "doc:DOC-1", "relation": "sparse", "evidence_status": lw.EVIDENCE_OBSERVED}],
    )[1] == 0

    assert lw.persist_period_reports(
        connection,
        [
            {
                "report_id": "REPORT-1",
                "period_kind": "weekly",
                "period_start": "2026-01-01",
                "period_end": "2026-01-07",
                "slice_kind": "pu",
                "slice_key": "PU-1",
                "document_count": 1,
                "judge": {
                    "verdict": "pass",
                    "source": "llm",
                    "ragas_metrics": [
                        {
                            "metric_id": "ragas_faithfulness",
                            "score": 0.8,
                            "evidence_ids": ["DOC-1"],
                        }
                    ],
                },
                "linked_scores": [{"score_id": "SCORE-1", "factor_id": "factor", "theta": 0.2, "standard_error": 0.1}],
            }
        ],
    ) == 1
    assert any(
        lw.ANALYSIS_REPORT_METRIC_TABLE in sql
        and params
        and params[0][0] == "REPORT-1"
        for sql, params in connection.cursor_value.executemany_calls
    )
    assert lw.persist_document_content_structure(
        connection, "DOC-EMPTY", {"blocks": [], "assets": []}
    ) == {
        "content_block_rows": 0,
        "content_format_hint_rows": 0,
        "content_asset_rows": 0,
    }
    assert lw.persist_knowledge_semantic_layer(connection, {"nodes": [], "edges": []})[
        "semantic_edge_rows"
    ] == 0
    empty_snapshot = lw.persist_knowledge_graph_snapshot(connection, {"nodes": [], "edges": []})
    assert empty_snapshot["knowledge_node_rows"] == empty_snapshot["knowledge_edge_rows"] == 0
    assert empty_snapshot["semantic_node_rows"] == empty_snapshot["semantic_edge_rows"] == 0
    assert lw.persist_period_reports(connection, []) == 0
    assert lw.persist_period_reports(connection, [{"period_kind": "weekly"}]) == 1
    assert lw.persist_operational_surfaces(
        connection,
        {"customer_master": {"accounts": [{"account_name": "Unlinked customer"}]}},
        [],
    )["customer_document_rows"] == 0
    assert lw.load_common_enum_values(
        [{"enum_family": "entity_role", "enum_code": "customer"}, {"enum_family": "entity_role"}, {}]
    ) == {"entity_role": ["customer"]}
    assert lw.extract_content_structure("</ul>")["blocks"] == []
    assert lw.extract_content_structure("first<span>second")["blocks"][0]["text_content"] == "firstsecond"


def test_period_report_loader_attaches_persisted_evaluation_metrics(monkeypatch) -> None:
    """Read scalar metrics and separately normalized evidence rows."""
    period_rows = [
        {
            "report_id": "REPORT-1",
            "period_kind": "weekly",
            "period_start": "2026-01-01",
            "period_end": "2026-01-07",
            "slice_kind": "pu",
            "slice_key": "PU-1",
            "document_count": 1,
            "judge_verdict": "pass",
            "judge_source": "llm_judge",
            "report_payload": {"judge": {"verdict": "pass"}},
        },
        {
            "report_id": "REPORT-2",
            "period_kind": "monthly",
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "slice_kind": "project",
            "slice_key": "PROJECT-1",
            "document_count": 1,
            "judge_verdict": "abstain",
            "judge_source": "unavailable",
            "report_payload": {"judge": "legacy"},
        },
    ]
    score_rows = [
        {
            "score_id": "SCORE-1",
            "report_id": "REPORT-1",
            "person_or_group": "REPORT-1",
            "factor_id": "gm-pos-delivery",
            "theta": 0.2,
            "standard_error": 0.1,
            "linking_method": "fipc",
            "calibration_source": "fast_mlsirm",
        }
    ]
    metric_rows = [
        {
            "report_id": "REPORT-1",
            "metric_id": "ragas_faithfulness",
            "score": 0.75,
            "verdict": "pass",
            "metric_source": "llm_judge",
            "rationale": "supported",
        },
        {
            "report_id": "REPORT-2",
            "metric_id": "ragas_context_recall",
            "score": None,
            "verdict": "abstain",
            "metric_source": "llm_judge",
            "rationale": "reference unavailable",
        },
        {
            "report_id": "REPORT-2",
            "metric_id": "ragas_context_precision",
            "score": 0.5,
            "verdict": "pass",
            "metric_source": "llm_judge",
            "rationale": "already decoded",
        },
    ]
    metric_evidence_rows = [
        {"report_id": "REPORT-1", "metric_id": "ragas_faithfulness", "evidence_id": "DOC-1"},
        {"report_id": "REPORT-1", "metric_id": "ragas_faithfulness", "evidence_id": ""},
        {"report_id": "REPORT-2", "metric_id": "ragas_context_precision", "evidence_id": "DOC-2"},
    ]

    def query(_connection, sql, _params=()):
        if lw.ANALYSIS_PERIOD_REPORT_TABLE in sql:
            return period_rows
        if lw.ANALYSIS_LINKED_SCORE_TABLE in sql:
            return score_rows
        if lw.ANALYSIS_REPORT_METRIC_EVIDENCE_TABLE in sql:
            return metric_evidence_rows
        return metric_rows

    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, _table: True)
    monkeypatch.setattr(lw, "_database_query", query)
    reports = lw.load_period_reports(object())
    assert reports[0]["judge"]["ragas_metrics"][0]["score"] == 0.75
    assert reports[0]["linked_scores"][0]["factor_label"] == "납기 준수"
    assert reports[1]["judge"]["ragas_metrics"][0]["verdict"] == "abstain"
    assert reports[1]["judge"]["ragas_metrics"][1]["evidence_ids"] == ["DOC-2"]

    monkeypatch.setattr(
        lw,
        "_database_table_exists",
        lambda _connection, table: table != lw.ANALYSIS_REPORT_METRIC_EVIDENCE_TABLE,
    )
    without_evidence_table = lw.load_period_reports(object())
    assert without_evidence_table[0]["judge"]["ragas_metrics"][0]["evidence_ids"] == []

    monkeypatch.setattr(
        lw,
        "_database_table_exists",
        lambda _connection, table: table != lw.ANALYSIS_REPORT_METRIC_TABLE,
    )
    period_rows[0]["report_payload"] = {"judge": {"verdict": "pass"}}
    period_rows[1]["report_payload"] = {"judge": "legacy"}
    legacy = lw.load_period_reports(object())
    assert legacy[0]["judge"]["ragas_metrics"] == []


def test_persist_analysis_restores_prior_keyman_without_replacing_live_results(monkeypatch) -> None:
    """Preserve a curated two-sided Keyman result when an ingestion rebuild is incomplete."""
    class Cursor:
        def __enter__(self) -> "Cursor":
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def executemany(self, _sql: str, _params: list[tuple[object, ...]]) -> None:
            return None

    class Connection:
        def cursor(self) -> Cursor:
            return Cursor()

    connection = Connection()
    monkeypatch.setattr(lw, "_database_exec", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        lw,
        "_database_table_exists",
        lambda _connection, table_name: table_name in {lw.ANALYSIS_DOCUMENT_TABLE, lw.ANALYSIS_OVERRIDE_TABLE},
    )
    keyman_rows = [
        {
            "document_no": "LIVE",
            "keyman_source": "llm",
            "keyman_status": "managed",
            "keyman_our_side": "[]",
            "keyman_counterpart_side": "[]",
        },
        {
            "document_no": "RESTORE",
            "keyman_source": "user_override",
            "keyman_status": "managed",
            "keyman_our_side": '[{"person_name": "Owner", "org_name": ""}]',
            "keyman_counterpart_side": "[]",
        },
        {
            "document_no": "RESTORE-2",
            "keyman_source": "user_override",
            "keyman_status": "managed",
            "keyman_our_side": '[{"person_name": "Owner 2", "org_name": ""}]',
            "keyman_counterpart_side": "[]",
        },
    ]

    def query(_connection, sql: str, _params=()):  # noqa: ANN001
        if f"FROM {lw.ANALYSIS_KG_EDGE_TABLE}" in sql or "FROM information_schema.columns" in sql:
            return []
        return keyman_rows

    monkeypatch.setattr(lw, "_database_query", query)
    monkeypatch.setattr(lw, "load_predicted_relatedness_edges", lambda _connection: [])
    monkeypatch.setattr(lw, "persist_knowledge_semantic_layer", lambda *_args, **_kwargs: {"semantic_node_rows": 0, "semantic_edge_rows": 0})
    monkeypatch.setattr(lw, "persist_affiliate_tree", lambda *_args, **_kwargs: {"affiliate_edge_rows": 0})
    monkeypatch.setattr(lw, "persist_operational_surfaces", lambda *_args, **_kwargs: {"ticket_rows": 0, "calendar_rows": 0, "todo_rows": 0})
    payload = {
        "metadata": {"row_count": 3, "document_count": 3, "thread_count": 1},
        "nodes": [
            {"id": "doc:LIVE", "type": "document", "document_no": "LIVE", "keyman_source": "llm"},
            {"id": "doc:RESTORE", "type": "document", "document_no": "RESTORE", "title_sample": "Update", "keyman_source": "pending"},
            {"id": "doc:RESTORE-2", "type": "document", "document_no": "RESTORE-2", "title_sample": "Update 2", "keyman_source": "pending"},
        ],
        "edges": [],
        "customer_master": {},
    }
    counts = lw.persist_analysis_payload(connection, payload, release_schema_locks=True)
    restored = next(node for node in payload["nodes"] if node["document_no"] == "RESTORE")
    assert counts["document_rows"] == 3
    assert restored["keyman_source"] == "user_override"
    assert restored["keyman_our_side"] == [{"person_name": "Owner", "org_name": ""}]
    restored_two = next(node for node in payload["nodes"] if node["document_no"] == "RESTORE-2")
    assert restored_two["keyman_our_side"] == [{"person_name": "Owner 2", "org_name": ""}]


def test_persisted_read_paths_rehydrate_authorized_overrides_and_customer_context(monkeypatch) -> None:
    """Rebuild persisted detail safely, including user overrides and evidence-scoped entities."""
    table_names = {
        lw.ANALYSIS_DOCUMENT_TABLE,
        lw.ANALYSIS_OVERRIDE_TABLE,
        lw.ANALYSIS_TICKET_TABLE,
        lw.ANALYSIS_TODO_TABLE,
        lw.ANALYSIS_CALENDAR_TABLE,
        lw.ANALYSIS_APPOINTMENT_TABLE,
        lw.ANALYSIS_EDGE_TABLE,
        lw.ANALYSIS_KG_NODE_TABLE,
        lw.ANALYSIS_KG_EDGE_TABLE,
    }
    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, table_name: table_name in table_names)
    monkeypatch.setattr(lw, "ensure_lineage_edge_reason_column", lambda _connection: None)
    monkeypatch.setattr(lw, "ensure_knowledge_graph_edge_evidence_columns", lambda _connection: None)
    monkeypatch.setattr(lw, "persist_lineage_relatedness_edges", lambda *_args: 0)
    monkeypatch.setattr(
        lw,
        "document_row_to_node",
        lambda _row: {
            "id": "doc:DOC-1",
            "type": "document",
            "document_no": "DOC-1",
            "acthguid": "THREAD-1",
            "corp_code": "CORP",
            "owner_pu": "PU-1",
            "entity_role": "고객",
            "visibility": "public",
            "issue_tickets": [],
            "document_events": [],
        },
    )
    calls: list[str] = []

    def query(_connection: object, sql: str, _params: tuple[object, ...] = ()) -> list[dict[str, object]]:
        calls.append(sql)
        if lw.ANALYSIS_OVERRIDE_TABLE in sql:
            return [{"visibility_code": "private", "keyman_our_side": '[{"person_name": "Owner"}]', "keyman_counterpart_side": '[]'}]
        if lw.ANALYSIS_TICKET_TABLE in sql:
            return [{"ticket_id": "T-1", "title": "Ticket"}]
        if lw.ANALYSIS_TODO_TABLE in sql:
            return [{"todo_id": "TODO-1", "content_source": "llm"}]
        if lw.ANALYSIS_CALENDAR_TABLE in sql:
            return [{"calendar_id": "CAL-1", "content_source": "llm"}]
        if lw.ANALYSIS_APPOINTMENT_TABLE in sql:
            return [{"appointment_id": "APT-1", "content_source": "extract"}]
        if lw.ANALYSIS_KG_NODE_TABLE in sql:
            return [{"node_id": "kg:document:DOC-1", "node_type": "document", "label": "Document", "document_no": "DOC-1", "metadata_payload": "{}"}]
        if lw.ANALYSIS_KG_EDGE_TABLE in sql:
            return [{"source_node": "kg:document:DOC-1", "target_node": "kg:customer:1", "relation_name": "document_customer_entity", "evidence_id": "ROW-1", "evidence_status": lw.EVIDENCE_OBSERVED, "reason": "observed"}]
        return [{}] if lw.ANALYSIS_DOCUMENT_TABLE in sql and "WHERE document_no" in sql else []

    monkeypatch.setattr(lw, "_database_query", query)
    customer_master = {"accounts": [{"account_name": "Customer", "document_nos": ["DOC-1"]}], "edges": [{"parent": "Customer", "child": "Customer Unit"}]}
    monkeypatch.setattr(lw, "load_customer_master", lambda _connection: customer_master)
    attached: list[dict[str, object]] = []
    monkeypatch.setattr(
        lw,
        "attach_customer_master_knowledge_graph",
        lambda graph, master: attached.append(master) or graph,
    )
    detail = lw.load_persisted_document_detail(object(), "DOC-1")
    assert detail is not None
    assert detail["document"]["visibility"] == "private"
    assert detail["document"]["keyman_source"] == "user_override"
    assert detail["document"]["issue_tickets"] == [{"ticket_id": "T-1", "title": "Ticket"}]
    assert detail["document"]["todo_items"][0]["source"] == "llm"
    assert detail["document"]["calendar_items"][0]["source"] == "llm"
    assert detail["document"]["appointments"][0]["source"] == "extract"
    assert attached == [customer_master]
    assert any(lw.ANALYSIS_KG_NODE_TABLE in sql for sql in calls)

    override_rows: list[dict[str, object]] = [
        {"visibility_code": "", "keyman_our_side": "", "keyman_counterpart_side": None}
    ]

    def sparse_query(_connection: object, sql: str, _params: tuple[object, ...] = ()) -> list[dict[str, object]]:
        if lw.ANALYSIS_OVERRIDE_TABLE in sql:
            return override_rows
        if lw.ANALYSIS_EDGE_TABLE in sql:
            return [{"source_node": "doc:DOC-1", "target_node": "doc:DOC-1", "relation_name": "predicted", "evidence_status": lw.EVIDENCE_PREDICTED, "acthguid": "THREAD-1"}]
        if lw.ANALYSIS_DOCUMENT_TABLE in sql:
            return [{}]
        return []

    monkeypatch.setattr(lw, "_database_query", sparse_query)
    monkeypatch.setattr(lw, "load_customer_master", lambda _connection: {"accounts": [], "edges": []})
    sparse_detail = lw.load_persisted_document_detail(object(), "DOC-1")
    assert sparse_detail is not None and sparse_detail["document"]["issue_tickets"] == []
    override_rows.clear()
    assert lw.load_persisted_document_detail(object(), "DOC-1") is not None


def test_persisted_blank_values_do_not_create_customer_links_or_overrides(monkeypatch) -> None:
    """Retain the existing document state when optional database values are blank."""
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)

    def customer_query(_connection: object, sql: str, _params: tuple[object, ...] = ()) -> list[dict[str, object]]:
        if lw.ANALYSIS_CUSTOMER_TABLE in sql:
            return [{"account_name": "Customer", "parent_name": "", "tier_name": "hq", "entity_role": "고객", "content_source": "llm"}]
        if lw.ANALYSIS_CUSTOMER_DOCUMENT_TABLE in sql:
            return [{"account_name": "", "document_no": "DOC-1"}]
        return []

    monkeypatch.setattr(lw, "_database_query", customer_query)
    assert lw.load_customer_master(object())["accounts"][0]["document_nos"] == []
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda _connection, sql, _params=(): (
            [{"document_no": "DOC-1", "visibility_code": "", "keyman_our_side": "", "keyman_counterpart_side": None}]
            if lw.ANALYSIS_OVERRIDE_TABLE in sql
            else []
        ),
    )
    payload = {
        "nodes": [{"type": "document", "document_no": "DOC-1", "visibility": "private", "keyman_our_side": [], "keyman_counterpart_side": []}],
        "customer_master": {"source": "existing"},
        "period_reports": [{"report_id": "existing"}],
    }
    assert lw.load_database_overrides(object(), payload)["nodes"][0]["visibility"] == "private"


def test_persisted_payload_falls_back_to_live_tree_and_retains_customer_master(monkeypatch) -> None:
    """Avoid a full snapshot rebuild when persisted tables already provide the product payload."""
    required = {lw.ANALYSIS_RUN_TABLE, lw.ANALYSIS_DOCUMENT_TABLE, lw.ANALYSIS_EDGE_TABLE}
    monkeypatch.setattr(lw, "_database_table_exists", lambda _connection, table_name: table_name in required)
    monkeypatch.setattr(lw, "ensure_lineage_edge_reason_column", lambda _connection: None)
    monkeypatch.setattr(
        lw,
        "_database_query",
        lambda _connection, sql, _params=(): (
            [{"row_count": 1, "document_count": 1, "thread_count": 1, "metadata_payload": {}}]
            if lw.ANALYSIS_RUN_TABLE in sql
            else ([{"document_no": "DOC-1"}] if lw.ANALYSIS_DOCUMENT_TABLE in sql else [])
        ),
    )
    monkeypatch.setattr(
        lw,
        "document_row_to_node",
        lambda _row: {"id": "doc:DOC-1", "type": "document", "document_no": "DOC-1", "corp_code": "CORP", "owner_pu": "PU-1"},
    )
    monkeypatch.setattr(lw, "load_affiliate_tree", lambda _connection: {"nodes": [], "edges": [], "parent_of": {}})
    customer_master = {"accounts": [{"account_name": "Customer", "document_nos": ["DOC-1"]}], "edges": [{"parent": "Customer", "child": "Customer Unit"}]}
    monkeypatch.setattr(lw, "load_customer_master", lambda _connection: customer_master)
    monkeypatch.setattr(lw, "load_period_reports", lambda _connection: [])
    payload = lw.load_persisted_analysis_payload(object(), include_knowledge_graph=False)
    assert payload["knowledge_graph"] == {"nodes": [], "edges": []}
    assert payload["customer_master"] == customer_master
    assert payload["affiliate_tree"]["edges"]
    assert lw.load_persisted_analysis_payload(object(), include_knowledge_graph=True)["knowledge_graph"] == {
        "nodes": [],
        "edges": [],
    }


def test_keyman_event_and_source_runtime_contracts(monkeypatch) -> None:
    """Keep two-sided Keyman and event citations grounded in authorized evidence."""
    calls: list[dict[str, object]] = []
    def transport(body: dict[str, object]) -> dict[str, object]:
        calls.append(body)
        return {"our_side": [{"person_name": "Ana", "org_name": "Org A"}]} if body["extract_side"] == "our_side" else {"counterpart_side": [{"person_name": "Bo", "org_name": "Org B"}], "model": "fixture"}

    derived = lw.derive_keymen_via_llm("Ana meets Bo", transport=transport, authors={"created_by": "Ana"})
    assert len(calls) == 2
    assert derived["names"] == ["Ana", "Bo"]
    response = lw.normalize_event_chat_response(
        {"answer": "between events", "citations": [{"guid": "row-1"}, {"guid": "outside"}]},
        [{"guid": "row-1", "event": "opened"}],
        "DOC-1",
    )
    assert response["evidence_ids"] == ["row-1"]
    assert lw.derive_event_lineage_chat(
        {"document_no": "DOC-1", "title_sample": "Fixture", "document_events": [{"guid": "row-1", "event": "opened"}]},
        "what changed?",
        transport=lambda _body: {"answer": "opened", "evidence_ids": ["row-1"]},
    )["citations"][0]["guid"] == "row-1"
    assert "LIMIT 3" in lw.build_source_query("schema.table", 3)
    with pytest.raises(ValueError, match="invalid table"):
        lw.resolve_source_table("schema.table;drop")


def test_cli_main_writes_release_artifacts_from_direct_database_contract(monkeypatch, tmp_path, capsys) -> None:
    """Run the CLI wiring with a direct connection double and real output paths."""
    json_out = tmp_path / "lineage.json"
    dot_out = tmp_path / "lineage.dot"
    analytics_out = tmp_path / "analytics.json"
    args = SimpleNamespace(
        dsn="postgresql://fixture",
        table="schema.table",
        limit=0,
        json_out=str(json_out),
        dot_out=str(dot_out),
        analytics_out=str(analytics_out),
        orchestrator_base_url="",
        orchestrator_token="",
        artifact_id="",
        artifact_source="lineageweave",
        keyman_limit=1,
        write_reports=True,
        derive_factor_items=False,
        sweep_content_inspections=False,
        inspection_document_limit=0,
        enrich_appointments=False,
        appointment_enrichment_limit=16,
    )
    payload = {
        "metadata": {"row_count": 1, "document_count": 1, "thread_count": 1},
        "nodes": [{"id": "doc-1", "type": "document", "document_no": "DOC-1"}],
        "edges": [{"source": "doc-1", "target": "doc-1", "relation": "revision"}],
        "analytics": {"total_documents": 1},
    }
    reports = [{"report_id": "weekly-pu-1", "period_kind": "weekly", "slice_kind": "pu"}]
    report_calls: dict[str, object] = {}
    monkeypatch.setattr(lw, "parse_args", lambda: args)
    monkeypatch.setattr(lw.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(lw, "ensure_common_enum_table", lambda *_args: {})
    monkeypatch.setattr(lw, "resolve_keyman_transport_optional", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "build_payload", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(lw, "persist_analysis_payload", lambda *_args, **_kwargs: {"document_rows": 1, "edge_rows": 0, "knowledge_node_rows": 0, "affiliate_edge_rows": 0})
    monkeypatch.setattr(lw, "load_database_overrides", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(lw, "store_default_oa_method_papers", lambda **_kwargs: [{"store_status": "stored"}])
    monkeypatch.setattr(lw, "persist_method_paper_records", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(
        lw,
        "build_period_report_slices",
        lambda documents: report_calls.setdefault("documents", documents) and [{"slice_kind": "pu"}],
    )
    monkeypatch.setattr(lw, "resolve_mlsirm_transport", lambda: (None, "not_configured"))
    monkeypatch.setattr(
        lw,
        "score_period_reports",
        lambda slices, documents, **kwargs: reports
        if slices and documents and kwargs["mlsirm_transport"] is None
        else [],
    )
    monkeypatch.setattr(lw, "persist_period_reports", lambda _connection, rows: len(rows))
    lw.main()
    assert payload["metadata"]["operational_surface_mode"] == "preserve"
    assert json_out.is_file()
    assert '"doc-1" -> "doc-1" [label="revision"' in dot_out.read_text()
    assert json.loads(analytics_out.read_text())["total_documents"] == 1
    assert json.loads(json_out.read_text())["period_reports"] == reports
    assert report_calls["documents"] == payload["nodes"]
    assert "reports=1 weekly=1 monthly=0 slice_kinds=pu judge=live_http mlsirm=not_configured" in capsys.readouterr().out

    payload.pop("period_reports", None)
    args.write_reports = False
    args.orchestrator_base_url = "https://orchestrator.example"
    with pytest.raises(RuntimeError, match="--orchestrator-base-url requires --orchestrator-token"):
        lw.main()
    assert "period_reports" not in json.loads(json_out.read_text())

    uploaded: dict[str, object] = {}
    args.orchestrator_token = "operator-token"
    monkeypatch.setattr(
        lw,
        "_post_to_contextual_orchestrator",
        lambda base_url, token, body, artifact_id, source: uploaded.update(
            {
                "base_url": base_url,
                "token": token,
                "body": body,
                "artifact_id": artifact_id,
                "source": source,
            }
        ),
    )
    lw.main()
    assert uploaded["base_url"] == "https://orchestrator.example"
    assert uploaded["token"] == "operator-token"
    assert uploaded["body"] is payload

    args.orchestrator_base_url = ""
    args.orchestrator_token = ""
    args.write_reports = True
    product_resolutions = iter([(lambda _body: {}, "live_http"), RuntimeError("report gateway offline")])

    def resolve_product_for_report_error():
        """Return the startup transport, then expose a report-specific outage."""
        result = next(product_resolutions)
        if isinstance(result, RuntimeError):
            raise result
        return result

    monkeypatch.setattr(lw, "resolve_product_transport", resolve_product_for_report_error)
    monkeypatch.setattr(lw, "resolve_mlsirm_transport", lambda: (lambda _body: {}, "fixture"))
    lw.main()
    assert "report_judge_unavailable=report gateway offline" in capsys.readouterr().out

    args.write_reports = False
    monkeypatch.setattr(
        lw,
        "resolve_product_transport",
        lambda: (_ for _ in ()).throw(RuntimeError("startup gateway offline")),
    )
    lw.main()
    assert "product_transport=startup gateway offline" in capsys.readouterr().out

    args.json_out = None
    args.dot_out = None
    args.analytics_out = None
    default_export_calls: list[tuple[object, object]] = []
    monkeypatch.setattr(
        lw,
        "_write_outputs",
        lambda _payload, output_json, output_dot: default_export_calls.append((output_json, output_dot)),
    )
    lw.main()
    assert default_export_calls == [(None, None)]
    output = capsys.readouterr().out
    assert "json=disabled" in output
    assert "analytics=disabled" in output

    args.write_reports = True
    args.derive_factor_items = True
    candidate = {
        "item_id": "item-generated",
        "factor_id": "gm-pos-delivery",
        "item_stem": "납기 근거가 있는가",
        "evidence_links": [],
    }
    monkeypatch.setattr(
        lw,
        "derive_factor_item_catalog_via_llm",
        lambda *_args, **_kwargs: {"items": [candidate], "source": "llm"},
    )
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "persist_factor_item_catalog", lambda *_args, **_kwargs: 1)
    lw.main()
    assert "factor_item_candidates=1 source=llm" in capsys.readouterr().out
    monkeypatch.setattr(
        lw,
        "derive_factor_item_catalog_via_llm",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("catalog rejected")),
    )
    lw.main()
    assert "factor_item_catalog_unavailable=catalog rejected" in capsys.readouterr().out

    args.enrich_appointments = True
    args.appointment_enrichment_limit = 8
    monkeypatch.setattr(
        lw,
        "enrich_pending_appointment_records",
        lambda _connection, *, transport, limit, batch_id: {
            "requested": limit,
            "completed": 2,
            "fallback": 1,
            "failed": 0,
            "appointment_rows": 3,
        }
        if transport is not None
        else {},
    )
    monkeypatch.setattr(
        lw,
        "publish_appointment_enrichment_events",
        lambda _connection, *, batch_id, limit: {"requested": limit, "published": 2, "pending": 0},
    )
    lw.main()
    assert 'appointment_enrichment={"appointment_rows": 3, "completed": 2, "events_pending": 0, "events_published": 2, "failed": 0, "fallback": 1, "requested": 8} transport=live_http' in capsys.readouterr().out
    args.enrich_appointments = False
    args.enrich_issue_work = True
    args.issue_work_enrichment_limit = 7
    monkeypatch.setattr(
        lw,
        "enrich_pending_issue_work_items",
        lambda _connection, *, transport, limit, batch_id: {
            "requested": limit,
            "completed": 2,
            "fallback": 1,
            "todo_rows": 2,
            "calendar_rows": 2,
        }
        if transport is not None
        else {},
    )
    monkeypatch.setattr(
        lw,
        "publish_issue_work_enrichment_events",
        lambda _connection, *, batch_id, limit: {"requested": limit, "published": 2, "pending": 0},
    )
    lw.main()
    assert 'issue_work_enrichment={"calendar_rows": 2, "completed": 2, "events_pending": 0, "events_published": 2, "fallback": 1, "requested": 7, "todo_rows": 2} transport=live_http' in capsys.readouterr().out
    args.enrich_appointments = True
    lw.main()
    combined_output = capsys.readouterr().out
    assert "appointment_enrichment=" in combined_output
    assert "issue_work_enrichment=" in combined_output
    args.enrich_appointments = False
    args.enrich_issue_work = False


def test_cli_main_runs_optional_content_inspection_sweep(monkeypatch, tmp_path, capsys) -> None:
    """Run a bounded corpus sweep with a mocked inspection transport."""
    json_out = tmp_path / "lineage.json"
    analytics_out = tmp_path / "analytics.json"
    args = SimpleNamespace(
        dsn="postgresql://fixture",
        table="schema.table",
        limit=0,
        json_out=str(json_out),
        dot_out=None,
        analytics_out=str(analytics_out),
        orchestrator_base_url="",
        orchestrator_token="",
        artifact_id="",
        artifact_source="lineageweave",
        keyman_limit=0,
        write_reports=False,
        sweep_content_inspections=True,
        inspection_document_limit=2,
    )
    payload = {
        "metadata": {"row_count": 0, "document_count": 0, "thread_count": 0},
        "nodes": [],
        "edges": [],
        "analytics": {"total_documents": 0},
    }
    captured_sweep: list[tuple[str, int]] = []

    monkeypatch.setattr(lw, "parse_args", lambda: args)
    monkeypatch.setattr(lw.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(lw, "ensure_common_enum_table", lambda *_args: {})
    monkeypatch.setattr(
        lw,
        "sweep_content_inspections",
        lambda connection, source_table, document_limit=0: captured_sweep.append((source_table, int(document_limit)))
        or {
            "document_count": 1,
            "content_block_rows": 0,
            "content_asset_rows": 0,
            "inspection_candidates": 0,
            "inspected_asset_count": 0,
            "failed_inspection_count": 0,
            "skipped_inspection_count": 0,
            "transport": "compose_live_proxy",
        },
    )
    monkeypatch.setattr(lw, "resolve_keyman_transport_optional", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "build_payload", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(lw, "persist_analysis_payload", lambda *_args, **_kwargs: {"document_rows": 0, "edge_rows": 0, "knowledge_node_rows": 0, "affiliate_edge_rows": 0})
    monkeypatch.setattr(lw, "load_database_overrides", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(lw, "store_default_oa_method_papers", lambda **_kwargs: [{"store_status": "stored"}])
    monkeypatch.setattr(lw, "persist_method_paper_records", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(lw, "resolve_mlsirm_transport", lambda: (None, "not_configured"))
    lw.main()
    assert captured_sweep == [("schema.table", 2)]
    assert "sweep_content_inspections=" in capsys.readouterr().out


def test_cli_module_entrypoint_and_duplicate_timestamp_analytics(monkeypatch) -> None:
    """Keep the executable module and chronology diagnostics covered by real entry behavior."""
    stamp = lw.datetime(2026, 1, 1)
    analytics = lw._build_analytics(
        [
            SimpleNamespace(docno="DOC-1", timestamp=stamp, source_row_number=1, stage="W", status="open"),
            SimpleNamespace(docno="DOC-1", timestamp=stamp, source_row_number=2, stage="W", status="open"),
        ],
        [{"document_no": "DOC-1", "row_count": 2, "acthguid": "THREAD-1"}],
        [],
    )
    assert analytics["docs_with_duplicate_timestamps"] == 1
    assert lw._build_analytics(
        [
            SimpleNamespace(docno="DOC-2", timestamp=stamp, source_row_number=1, stage="W", status="open"),
            SimpleNamespace(docno="DOC-2", timestamp=None, source_row_number=2, stage="W", status="open"),
        ],
        [{"document_no": "DOC-2", "row_count": 2, "acthguid": "THREAD-2"}],
        [],
    )["max_revision_gap_seconds"] == 0
    monkeypatch.setattr(sys, "argv", ["lineageweave.py", "--help"])
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(lw.__file__, run_name="__main__")
    assert exited.value.code == 0


def test_runtime_environment_upload_parser_and_graph_helpers(monkeypatch, tmp_path, capsys) -> None:
    """Load explicit runtime settings, upload on request, parse CLI flags, and bound KG traversal."""
    env_file = tmp_path / "runtime.env"
    env_file.write_text("# fixture\nFRESH_VALUE=loaded\nexport QUOTED_VALUE='quoted'\nPRESERVED_VALUE=ignored\n")
    monkeypatch.delenv("FRESH_VALUE", raising=False)
    monkeypatch.delenv("QUOTED_VALUE", raising=False)
    monkeypatch.setenv("PRESERVED_VALUE", "kept")
    lw.load_runtime_env(env_file)
    assert lw.os.environ["FRESH_VALUE"] == "loaded"
    assert lw.os.environ["QUOTED_VALUE"] == "quoted"
    assert lw.os.environ["PRESERVED_VALUE"] == "kept"

    monkeypatch.setattr(lw.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response({"accepted": True}))
    lw._post_to_contextual_orchestrator("https://orchestrator.example/", "token", {"rows": 1}, "artifact-1", "fixture")
    assert "uploaded_artifact=https://orchestrator.example/api/v1/lineageweave_artifacts" in capsys.readouterr().out
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_http_error(500)]))
    with pytest.raises(RuntimeError, match="HTTP 500"):
        lw._post_to_contextual_orchestrator("https://orchestrator.example", "token", {}, None, "fixture")
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([urllib.error.URLError("offline")]))
    with pytest.raises(RuntimeError, match="offline"):
        lw._post_to_contextual_orchestrator("https://orchestrator.example", "token", {}, None, "fixture")

    monkeypatch.setattr(sys, "argv", ["lineageweave.py", "--table", "schema.table", "--limit", "3", "--keyman-limit", "2"])
    parsed = lw.parse_args()
    assert (
        parsed.table,
        parsed.limit,
        parsed.keyman_limit,
        parsed.sweep_content_inspections,
        parsed.inspection_document_limit,
    ) == ("schema.table", 3, 2, False, 0)
    assert parsed.keyman_offset == 0
    monkeypatch.setattr(sys, "argv", ["lineageweave.py", "--keyman-offset", "2"])
    assert lw.parse_args().keyman_offset == 2
    assert lw.normalize_keyman_side(["Ana", {"name": "Bo", "org": "Org B"}, None]) == [
        {"person_name": "Ana", "org_name": ""},
        {"person_name": "Bo", "org_name": "Org B"},
    ]
    assert lw.named_keyman_side([None, {}, " "]) is False
    assert lw.named_keyman_side([{"org_name": "Fixture organization"}]) is True
    assert lw.named_keyman_side(["Fixture person"]) is True
    assert lw.normalize_document_references(["DOC-2", "", "DOC-1", "DOC-2", 3]) == ["3", "DOC-1", "DOC-2"]
    assert lw.normalize_document_references("DOC-1") == ["DOC-1"]
    assert lw.normalize_document_references({"document_no": "DOC-1"}) == []
    issued = lw.derive_issue_work_items_via_llm(
        {"ticket_id": "ticket-1", "title": "Fixture follow-up"},
        {"document_no": "DOC-1", "title_sample": "Fixture document"},
        transport=lambda _body: ["not a structured response"],
    )
    assert issued["todo"]["source"] == "pending_llm"
    assert issued["content"] == {}
    unavailable = lw.derive_issue_work_items_via_llm(
        {"ticket_id": "ticket-2", "title": "Unavailable worker"},
        {"document_no": "DOC-1", "title_sample": "Fixture document"},
        transport=lambda _body: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert unavailable["calendar"]["source"] == "pending_llm"
    assert lw.parse_issue_work_content(
        {"todo_body": "Do it", "calendar_body": "Meet", "due_on": "2026/09/01"}
    ) == {"todo_body": "Do it", "calendar_body": "Meet", "due_on": "2026-09-01"}
    assert lw.parse_issue_work_content({"due_on": "not-a-date"}) == {}
    fallback = lw.derive_keymen_via_llm(
        "Title",
        transport=lambda _body: {"keymen": ["Ana", "Bo"]},
        authors={"created_by": "Ana"},
    )
    assert [item["person_name"] for item in fallback["our_side"]] == ["Ana"]
    assert [item["person_name"] for item in fallback["counterpart_side"]] == ["Bo"]
    graph = {
        "nodes": [
            {"id": "kg:document:DOC-1", "type": "document", "kg_depth": 3},
            {"id": "kg:person:1", "type": "person", "label": "Ana", "kg_depth": 3},
            {"id": "kg:organization:1", "type": "organization", "label": "Org", "kg_depth": 2},
        ],
        "edges": [
            {"source": "kg:document:DOC-1", "target": "kg:person:1", "relation": "document_person"},
            {"source": "kg:person:1", "target": "kg:organization:1", "relation": "cross_corp_thread"},
        ],
    }
    assert {node["id"] for node in lw.related_knowledge_graph(graph, "DOC-1", depth=1)["nodes"]} == {"kg:document:DOC-1", "kg:person:1"}
    assert lw.related_keyman_graph(graph, "Missing")["nodes"] == []
    assert {"Org", "Org Unit", "Site"} <= set(lw.collect_affiliate_labels(["Org - Org Unit - Site"]))


def test_visibility_persistence_keeps_the_event_optional_and_transactional(monkeypatch) -> None:
    """Write both PostgreSQL visibility rows and enqueue an event only for a mutation payload."""
    statements: list[tuple[str, tuple]] = []
    events: list[tuple] = []
    monkeypatch.setattr(
        lw,
        "_database_exec",
        lambda _connection, sql, params=(): statements.append((" ".join(sql.split()), params)),
    )
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda *_args: events.append(_args))

    lw.persist_visibility(object(), "DOC-1", "private", "account-1", {"visibility": "private"})
    assert len(statements) == 2
    assert statements[0][1] == ("DOC-1", "private", "account-1")
    assert statements[1][1] == ("private", "DOC-1")
    assert events[0][1:] == ("document_visibility_changed", "DOC-1", "account-1", {"visibility": "private"})

    statements.clear()
    events.clear()
    lw.persist_visibility(object(), "DOC-1", "public", "account-1")
    assert len(statements) == 2
    assert events == []


def test_authorization_rejects_missing_claims_unknown_actions_cross_pu_writes_and_invalid_visibility() -> None:
    """Keep every RBAC/ABAC failure on the server side before a product mutation."""
    resource = {"corp_code": "CORP-A", "owner_pu": "PU-A", "visibility": lw.VISIBILITY_PRIVATE}
    author_elsewhere = {"corp_code": "CORP-A", "pu_code": "PU-B", "roles": ["author"]}
    assert lw.authorize_access(actor=None, resource=resource, action="read") == {
        "allowed": False,
        "reason": "unauthenticated",
    }
    assert lw.authorize_access(actor=author_elsewhere, resource=resource, action="invent") == {
        "allowed": False,
        "reason": "unknown_action",
    }
    assert lw.authorize_access(actor=author_elsewhere, resource=resource, action="publish") == {
        "allowed": False,
        "reason": "abac_pu",
    }
    with pytest.raises(ValueError, match="unknown visibility"):
        lw.apply_visibility(resource, "embargoed", author_elsewhere)


def test_appointment_extraction_uses_real_date_shapes_then_anchor_without_rewriting_existing_rows() -> None:
    """Resolve dates from Korean content and preserve an existing human-managed appointment row."""
    reference = lw.datetime(2026, 5, 1, tzinfo=lw.timezone.utc)
    assert lw._normalize_appointment_date("26.05.03", today=reference) == "2026-05-03"
    assert lw._normalize_appointment_date("5/4", today=reference) == "2026-05-04"
    assert lw.appointment_anchor_date("260501 customer meeting") == "2026-05-01"
    assert lw.appointment_anchor_date("260099 invalid") is None
    appointments = lw.extract_appointments(
        "2026-05-03 고객 약속 후 2026-05-03 고객 미팅 확인",
        today=reference,
        document_no="DOC-1",
    )
    assert [item["occurred_on"] for item in appointments] == ["2026-05-03"]
    anchored = lw.extract_appointments("고객 약속을 조율", document_no="260502", fallback_date="2026-04-01")
    assert anchored[0]["occurred_on"] == "2026-05-02"
    assert lw.extract_appointments("고객 약속을 조율", document_no="invalid", fallback_date="not-a-date") == []
    assert lw.resolve_document_appointments({"appointments": ["human-managed"]}) == ["human-managed"]


def test_psychometric_connector_abstains_without_package_output(monkeypatch) -> None:
    """Do not manufacture psychometric scores when fast-mlsirm is unavailable."""
    untouched = {"issue_tickets": [], "todo_items": []}
    assert lw.enrich_pending_document_work(untouched, transport=lambda _body: {}) is untouched
    assert lw.parse_factor_item_responses({"item_scores": "invalid"}, []) == []
    assert lw.parse_mlsirm_link_response([]) == []
    assert lw.parse_mlsirm_link_response({"linked_scores": [None, {"factor_id": "", "person_or_group": "PU-A"}]}) == []
    alias_score = lw.parse_mlsirm_link_response(
        {"linked_scores": [{"factor_id": "factor", "person_or_group": "PU-A", "theta": 0.2, "se": 0.3}]}
    )
    assert alias_score[0]["standard_error"] == 0.3
    assert lw.parse_mlsirm_link_response(
        {
            "linked_scores": [
                {"factor_id": "factor", "person_or_group": "PU-A", "theta": "bad", "standard_error": 0.3},
                {"factor_id": "factor", "person_or_group": "PU-A", "theta": "nan", "standard_error": 0.3},
                {"factor_id": "factor", "person_or_group": "PU-A", "theta": 0.2, "standard_error": 0.3, "calibration_source": "recorded"},
            ]
        }
    ) == []
    fallback = lw.try_fast_mlsirm_link(
        {"responses": [{"person_or_group": "PU-A", "item_id": "item-1", "response": 1}], "items": [{"item_id": "item-1"}]},
        transport=lambda _body: (_ for _ in ()).throw(RuntimeError("connector unavailable")),
    )
    assert fallback["status"] == "unavailable"
    assert fallback["source"] == "unavailable"
    assert fallback["scores"] == []
    invalid_body = lw.try_fast_mlsirm_link(
        {"responses": [], "items": []},
        transport=lambda _body: [],
    )
    assert invalid_body == {
        "status": "unavailable",
        "reason": "fast_mlsirm_response_invalid",
        "scores": [],
        "source": "unavailable",
    }
    no_transport = lw.try_fast_mlsirm_link({"responses": [], "items": []})
    assert no_transport == {
        "status": "unavailable",
        "reason": "fast_mlsirm_transport_unset",
        "scores": [],
        "source": "unavailable",
    }
    assert lw.period_window("monthly", lw.datetime(2026, 12, 5))[1:3] == ("2026-12-01", "2026-12-31")
    monkeypatch.setattr(lw, "make_mlsirm_transport", lambda: (_ for _ in ()).throw(RuntimeError("http unset")))
    monkeypatch.setattr(lw, "make_local_fast_mlsirm_transport", lambda: (_ for _ in ()).throw(RuntimeError("local unset")))
    assert lw.resolve_mlsirm_transport() == (None, "local unset")
    assert lw.document_org_unit_labels({"keyman_our_side": ["Customer Group"]}) == ["Customer Group"]


def test_authorized_event_context_and_live_gateway_fallbacks_never_invent_evidence(monkeypatch, tmp_path) -> None:
    """Keep popup events citeable when model routes downgrade from workflow endpoints to chat."""
    nodes = [{"type": "document", "document_no": "DOC-1", "title_sample": "Observed title", "first_row_ts": "2026-05-01", "first_event": "OPEN"}]
    lw.attach_document_events(nodes)
    assert nodes[0]["document_events"][0]["guid"] == "DOC-1"
    normalized = lw.normalize_event_chat_response(
        {"answer": "확인됨", "citations": [None]},
        [None, {"guid": "ROW-1", "title": "Observed row"}, {"guid": "ROW-1", "title": "Duplicate row"}],
        "DOC-1",
        semantic_context={"node_terms": [{"standard_uri": "ROW-1", "term_label": "Duplicate semantic row"}]},
    )
    assert normalized["evidence_ids"] == ["ROW-1"]
    assert normalized["semantic_term_uris"] == []
    lw.load_runtime_env(tmp_path / "absent.env")

    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([_Response({"choices": [{"message": {"content": "[]"}}]})]),
    )
    assert lw._post_chat_completion_json(
        {"task": "fixture"},
        base_url="https://gateway.example",
        token="fixture",
        model="fixture-model",
        system_prompt="fixture",
        timeout=1,
    ) == {}

    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([_Response({"our_side": [], "counterpart_side": []})]),
    )
    assert lw.post_keyman_http({}, base_url="https://gateway.example", token="fixture") == {
        "our_side": [],
        "counterpart_side": [],
    }
    monkeypatch.setattr(lw, "_post_chat_completion_json", lambda *_args, **_kwargs: {"fallback": True})
    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([urllib.error.URLError("offline")]))
    assert lw.post_keyman_http({}, base_url="https://gateway.example", token="fixture") == {"fallback": True}


def test_vision_chat_and_compose_failures_keep_model_and_queue_boundaries_explicit(monkeypatch) -> None:
    """Use only explicit HTTP fallbacks and report worker launch failure without synthetic output."""
    image_body = {"task": "content_inspection", "image_data_uri": "data:image/png;base64,AA=="}
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([
            _Response({"unexpected": True}),
            _Response({"model": "vision-model", "choices": [{"message": {"content": "[]"}}]}),
        ]),
    )
    vision = lw.post_content_inspection_http(image_body, base_url="https://gateway.example", token="fixture")
    assert vision == {"ocr_text": "[]", "object_labels": [], "model": "vision-model"}

    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([
            urllib.error.URLError("workflow offline"),
            _Response({"model": "chat-model", "choices": [{"message": {"content": "plain Korean answer"}}]}),
        ]),
    )
    fallback_chat = lw.post_lineage_chat({"task": "event_lineage_chat"}, base_url="https://gateway.example", token="fixture")
    assert fallback_chat["answer"] == "plain Korean answer"
    assert fallback_chat["evidence_ids"] == []
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([
            _Response({"unexpected": True}),
            _Response({"choices": [{"message": {"content": "workflow fallback"}}]}),
        ]),
    )
    assert lw.post_lineage_chat({"task": "event_lineage_chat"}, base_url="https://gateway.example", token="fixture")["answer"] == "workflow fallback"
    monkeypatch.setattr(
        lw.urllib.request,
        "urlopen",
        _sequence_urlopen([
            urllib.error.URLError("workflow offline"),
            _Response({"choices": [{"message": {"content": "[]"}}]}),
        ]),
    )
    assert lw.post_lineage_chat({"task": "event_lineage_chat"}, base_url="https://gateway.example", token="fixture")["answer"] == "[]"

    monkeypatch.setattr(lw, "load_runtime_env", lambda path=None: None)
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    monkeypatch.delenv("LLM_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    monkeypatch.setenv("ORCHESTRATOR_BASE_URL", "https://orchestrator.example")
    monkeypatch.setenv("ORCHESTRATOR_TOKEN", "fixture")
    assert lw.live_http_config() == ("https://orchestrator.example", "fixture", "gpt-4.1-mini")

    monkeypatch.setattr(lw.urllib.request, "urlopen", _sequence_urlopen([_http_error(503)]))
    with pytest.raises(RuntimeError, match="compose_worker_http_503"):
        lw.compose_standin_transport({"task": "event_lineage_chat"})

    monkeypatch.delenv("ORCHESTRATOR_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    monkeypatch.setattr(lw.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")))
    monkeypatch.setattr(lw.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="compose stdout", stderr="compose stderr"))
    with pytest.raises(RuntimeError, match="compose stdout"):
        lw.ensure_compose_standin()
