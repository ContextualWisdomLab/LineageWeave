"""Drive shipped access, role, and tree functions — not a re-implementation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest
from psycopg.types.json import Json

import lineageweave as lw
import lineageweave_server as server


def _test_dsn() -> str:
    """Read the process-local DSN after pytest configures the integration database."""
    return os.environ.get("LINEAGEWEAVE_TEST_DSN", "postgresql://localhost/postgres")


def test_test_dsn_reads_runtime_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration helpers must observe pytest's process-local DSN at call time."""
    monkeypatch.setenv("LINEAGEWEAVE_TEST_DSN", "postgresql://fixture/test_database")
    assert _test_dsn() == "postgresql://fixture/test_database"


def _row(
    *,
    guid: str,
    docno: str,
    acthguid: str,
    date: str,
    time: str = "10:00:00",
    title: str | None = None,
    source_row_number: str = "1",
) -> dict[str, str | None]:
    return {
        "guid_field": guid,
        "docnosub_field": docno,
        "acthguid_field": acthguid,
        "aedat_field": date,
        "aezet_field": time,
        "erdat_field": date,
        "erzet_field": time,
        "title_field": title,
        "voctp_field": None,
        "dtsts_field": None,
        "ststs_field": "Z",
        "grade_field": None,
        "bukrs_field": "CWL1",
        "pucode_field": "PU01",
        "ernam_field": "fixture-user",
        "aenam_field": "fixture-user",
        "userid_field": "fixture-user",
        "source_row_number": source_row_number,
    }


def _keyman_fixture_transport(_body: dict) -> dict:
    return {
        "our_side": [{"person_name": "Fixture analyst", "org_name": "Fixture group"}],
        "counterpart_side": [
            {"person_name": "Fixture partner", "org_name": "Fixture partner org"},
            {"person_name": "Fixture stakeholder", "org_name": "Fixture stakeholder org"},
        ],
        "keymen": ["Fixture analyst", "Fixture partner", "Fixture stakeholder"],
        "model": "fixture-worker",
    }


def _keyverse_claims(**overrides: object) -> dict[str, object]:
    claims: dict[str, object] = {
        "active": True,
        "iss": "https://keyverse.example/realms/cwl",
        "aud": ["lineageweave-web"],
        "client_id": "lineageweave-web",
        "exp": time.time() + 300,
        "sub": "acct-fixture-1",
        "org": "CWL1",
        "workspace": "PU01",
        "role": "member",
    }
    claims.update(overrides)
    return claims


def _keyverse_metadata() -> dict[str, str]:
    return {
        "issuer": "https://keyverse.example/realms/cwl",
        "client_id": "lineageweave-web",
        "client_secret": "fixture-secret",
        "redirect_uri": "https://lineageweave.example/api/oidc/callback",
        "authorization_endpoint": "https://keyverse.example/realms/cwl/protocol/openid-connect/auth",
        "token_endpoint": "https://keyverse.example/realms/cwl/protocol/openid-connect/token",
        "introspection_endpoint": "https://keyverse.example/realms/cwl/protocol/openid-connect/token/introspect",
    }


def test_keyverse_claims_require_account_tenant_and_role() -> None:
    assert server._actor_from_value({"org": "CWL1", "workspace": "PU01", "role": "reader"}) is None


def test_keyverse_oidc_permits_explicit_local_keyverse_http_only(monkeypatch) -> None:
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_COOKIE_SECURE", "0")
    monkeypatch.setenv("KEYVERSE_ISSUER", "http://127.0.0.1:8080")
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_CLIENT_ID", "lineageweave-web")
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_CLIENT_SECRET", "fixture-secret")
    monkeypatch.setenv(
        "LINEAGEWEAVE_OIDC_REDIRECT_URI", "http://127.0.0.1:5173/api/oidc/callback"
    )
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    settings = app._keyverse_settings()
    assert settings["issuer"] == "http://127.0.0.1:8080"
    assert settings["redirect_uri"] == "http://127.0.0.1:5173/api/oidc/callback"
    assert "Secure" not in server._cookie_header("lw_oidc_state", "fixture", 60)
    monkeypatch.setenv("LINEAGEWEAVE_COOKIE_SECURE", "1")
    with pytest.raises(RuntimeError, match="must_be_https_url"):
        app._keyverse_settings()
    assert "Secure" in server._cookie_header("lw_oidc_state", "fixture", 60)
    monkeypatch.setenv("LINEAGEWEAVE_COOKIE_SECURE", "0")
    assert server._https_url("http://host.docker.internal:8080", "KEYVERSE_ISSUER") == (
        "http://host.docker.internal:8080"
    )
    with pytest.raises(RuntimeError, match="must_be_https_url"):
        server._https_url("http://lineage-http-standin:8080", "KEYVERSE_ISSUER")
    monkeypatch.delenv("LINEAGEWEAVE_DEV_MODE")
    with pytest.raises(RuntimeError, match="must_be_https_url"):
        app._keyverse_settings()


def test_keyverse_oidc_requires_an_explicit_https_issuer(monkeypatch) -> None:
    monkeypatch.delenv("KEYVERSE_ISSUER", raising=False)
    monkeypatch.setenv("KEYVERSE_BASE_URL", "https://legacy.example/realms/cwl")
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_CLIENT_ID", "lineageweave-web")
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_CLIENT_SECRET", "fixture-secret")
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_REDIRECT_URI", "https://lineageweave.example/api/oidc/callback")
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    with pytest.raises(RuntimeError, match="keyverse_oidc_configuration_required"):
        app._keyverse_settings()


def test_server_accepts_bare_development_actor_contract() -> None:
    actor = server._actor_from_value(
        {
            "account_id": "acct-fixture",
            "corp_code": "CWL1",
            "pu_code": "PU01",
            "roles": ["reader"],
        }
    )
    assert actor["account_id"] == "acct-fixture"
    assert actor["corp_code"] == "CWL1"


def test_keyverse_oidc_pkce_exchanges_and_introspects_verified_claims(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class Response:
        def __init__(self, body: dict[str, object]) -> None:
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return json.dumps(self.body).encode("utf-8")

    def fake_urlopen(request, timeout=None, context=None):
        fields = urllib.parse.parse_qs(request.data.decode("utf-8"), keep_blank_values=True)
        calls.append(
            {
                "url": request.full_url,
                "fields": fields,
                "timeout": timeout,
                "context": context,
                "authorization": request.get_header("Authorization"),
            }
        )
        if request.full_url.endswith("/token"):
            return Response({"access_token": "fixture-access-token", "token_type": "Bearer"})
        return Response(_keyverse_claims())

    app = server.LineageApplication("postgresql://fixture", "schema.table")
    metadata = _keyverse_metadata()
    monkeypatch.setattr(app, "_keyverse_metadata", lambda *_args, **_kwargs: metadata)
    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)

    location, state = app.begin_keyverse_login(email_address="member@example.com")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == [metadata["client_id"]]
    assert query["scope"] == ["openid profile email"]
    assert query["login_hint"] == ["member@example.com"]
    assert query["state"] == [state]
    assert query["code_challenge_method"] == ["S256"]
    assert "code_verifier" not in query
    assert metadata["client_secret"] not in location
    code_verifier = app._keyverse_states[state]["code_verifier"]

    session_token, actor, ttl = app.complete_keyverse_login("fixture-code", state, state)
    assert actor == {
        "account_id": "acct-fixture-1",
        "corp_code": "CWL1",
        "pu_code": "PU01",
        "roles": ["reader"],
        "corp_name": None,
        "pu_name": None,
    }
    assert 0 < ttl <= 300
    assert app.actor_for_request(type("Request", (), {"headers": {"Cookie": f"lw_session={session_token}"}})()) == actor
    assert calls[0]["url"] == metadata["token_endpoint"]
    assert calls[0]["fields"] == {
        "grant_type": ["authorization_code"],
        "code": ["fixture-code"],
        "redirect_uri": [metadata["redirect_uri"]],
        "code_verifier": [code_verifier],
    }
    assert calls[0]["context"].verify_mode == ssl.CERT_REQUIRED
    assert calls[0]["context"].check_hostname is True
    assert calls[0]["authorization"].startswith("Basic ")
    assert calls[1]["url"] == metadata["introspection_endpoint"]
    assert calls[1]["fields"] == {"token": ["fixture-access-token"], "token_type_hint": ["access_token"]}


def test_keyverse_oidc_rejects_state_mismatch_and_wrong_audience(monkeypatch) -> None:
    app = server.LineageApplication("postgresql://fixture", "schema.table")
    metadata = _keyverse_metadata()
    monkeypatch.setattr(app, "_keyverse_metadata", lambda *_args, **_kwargs: metadata)
    _location, state = app.begin_keyverse_login(email_address="member@example.com")
    with pytest.raises(RuntimeError, match="keyverse_callback_invalid"):
        app.complete_keyverse_login("fixture-code", state, "different-state")
    assert state in app._keyverse_states
    monkeypatch.setattr(
        app,
        "_keyverse_form_post",
        lambda *_args, **_kwargs: _keyverse_claims(aud=["another-client"]),
    )
    with pytest.raises(RuntimeError, match="keyverse_token_invalid"):
        app._actor_from_keyverse_access_token("fixture-access-token", metadata)


def test_abac_rbac_allow_versus_deny() -> None:
    reader = server._actor_from_value(
        {"sub": "acct-fixture-1", "org": "CWL1", "workspace": "PU01", "role": "reader"}
    )
    assert reader is not None
    public_doc = {"corp_code": "CWL1", "owner_pu": "PU02", "visibility": lw.VISIBILITY_PUBLIC}
    private_other_pu = {"corp_code": "CWL1", "owner_pu": "PU02", "visibility": lw.VISIBILITY_PRIVATE}
    other_corp = {"corp_code": "DEMO", "owner_pu": "PU10", "visibility": lw.VISIBILITY_PUBLIC}
    assert lw.authorize_access(actor=reader, resource=public_doc, action="read")["allowed"] is True
    assert lw.authorize_access(actor=reader, resource=private_other_pu, action="read")["allowed"] is False
    assert lw.authorize_access(actor=reader, resource=other_corp, action="read")["allowed"] is False
    author = dict(reader)
    author["roles"] = ["author"]
    author["pu_code"] = "PU02"
    assert lw.authorize_access(actor=author, resource=private_other_pu, action="read")["allowed"] is True
    assert lw.authorize_access(actor=reader, resource=public_doc, action="publish")["allowed"] is False


def test_tenant_actor_can_read_own_tenant_but_other_cannot() -> None:
    payload = lw.build_payload(
        [
            _row(guid="g1", docno="D1", acthguid="T1", date="2026-01-01"),
            {
                **_row(guid="g2", docno="D2", acthguid="T2", date="2026-01-02"),
                "bukrs_field": "DEMO",
                "pucode_field": "PU10",
            },
        ]
    )
    tenant_doc = next(node for node in payload["nodes"] if node["document_no"] == "D1")
    other_doc = next(node for node in payload["nodes"] if node["document_no"] == "D2")
    assert tenant_doc["corp_code"] == "CWL1"
    assert tenant_doc["owner_pu"] == "PU01"
    assert other_doc["corp_code"] == "DEMO"
    tenant = {"corp_code": "CWL1", "pu_code": "PU01", "roles": ["reader"]}
    outsider = {"corp_code": "DEMO", "pu_code": "PU10", "roles": ["reader"]}
    assert lw.authorize_access(actor=tenant, resource=tenant_doc, action="read")["allowed"] is True
    assert lw.authorize_access(actor=outsider, resource=tenant_doc, action="read")["allowed"] is False
    assert lw.filter_payload_for_actor(payload, tenant)["analytics"]["total_documents"] == 1
    outsider_docs = {
        node["document_no"]
        for node in lw.filter_payload_for_actor(payload, outsider)["nodes"]
        if node["type"] == "document"
    }
    assert outsider_docs == {"D2"}


def test_admin_cannot_cross_corp_boundary() -> None:
    admin = {"corp_code": "CWL1", "pu_code": "PU01", "roles": ["admin"]}
    other_corp = {"corp_code": "DEMO", "owner_pu": "PU10", "visibility": lw.VISIBILITY_PUBLIC}
    decision = lw.authorize_access(actor=admin, resource=other_corp, action="read")
    assert decision == {"allowed": False, "reason": "abac_corp"}


def test_payload_uses_source_corp_and_pu_attributes() -> None:
    payload = lw.build_payload(
        [_row(guid="g1", docno="D1", acthguid="T1", date="2026-01-01")]
    )
    document = next(node for node in payload["nodes"] if node["type"] == "document")
    assert document["corp_code"] == "CWL1"
    assert document["owner_pu"] == "PU01"
    assert payload["access_directory"]["CWL1"]["units"]["PU01"] == "PU PU01"


def test_filter_payload_for_actor_removes_other_tenant_nodes_and_edges() -> None:
    payload = lw.build_payload(
        [
            _row(guid="g1", docno="D1", acthguid="T1", date="2026-01-01"),
            {
                **_row(guid="g2", docno="D2", acthguid="T2", date="2026-01-02"),
                "bukrs_field": "DEMO",
                "pucode_field": "PU10",
            },
        ]
    )
    actor = {"corp_code": "CWL1", "pu_code": "PU01", "roles": ["reader"]}
    filtered = lw.filter_payload_for_actor(payload, actor)
    assert {node["document_no"] for node in filtered["nodes"] if node["type"] == "document"} == {"D1"}
    assert all(edge["source"].startswith("doc:D1") or edge["source"].startswith("row:g1") for edge in filtered["edges"])
    assert filtered["metadata"]["authorization_boundary"] == "filtered_for_verified_actor"
    assert filtered["analytics"]["total_documents"] == 1


def test_visibility_public_versus_private() -> None:
    resource = {"corp_code": "CWL1", "owner_pu": "PU01", "visibility": lw.VISIBILITY_PUBLIC}
    author = {"corp_code": "CWL1", "pu_code": "PU01", "roles": ["author"]}
    updated = lw.apply_visibility(resource, lw.VISIBILITY_PRIVATE, author)
    assert updated["visibility"] == lw.VISIBILITY_PRIVATE
    outsider = {"corp_code": "CWL1", "pu_code": "PU02", "roles": ["reader"]}
    assert lw.authorize_access(actor=outsider, resource=updated, action="read")["allowed"] is False
    assert lw.authorize_access(actor=author, resource=updated, action="read")["allowed"] is True


def test_entity_role_tags() -> None:
    assert lw.classify_entity_role("고객의 고객 납품 이슈") == "고객의 고객"
    assert lw.classify_entity_role("경쟁사 입찰 동향") == "경쟁사"
    assert lw.classify_entity_role("파트너 계약 갱신") == "파트너"
    assert lw.classify_entity_role("발주 고객 미팅") == "고객"
    assert lw.classify_entity_role("유럽 시장 전망") == "시장"
    assert lw.classify_entity_role("end customer shipment") == "고객의 고객"


def test_document_neighbor_ranking_uses_title_overlap_before_stable_order() -> None:
    """Predicted relatedness must prefer an actually similar title."""
    ranked = lw._rank_neighbors_by_title_similarity(
        "한전 변전소 점검",
        [
            {"document_no": "unrelated", "title_sample": "시장 전망 보고서"},
            {"document_no": "related", "title_sample": "한전 변전소 점검 결과"},
            {"document_no": "untitled"},
            {"document_no": "", "title_sample": "한전 변전소 점검"},
        ],
        limit=2,
    )
    assert [item["document_no"] for item in ranked] == ["related", "unrelated"]
    assert ranked[0]["title_similarity"] > 0
    assert ranked[1]["title_similarity"] == 0.0
    assert lw._rank_neighbors_by_title_similarity(None, [], limit=0) == []
    assert lw._rank_neighbors_by_title_similarity("short", [], limit=1) == []
    assert lw._rank_neighbors_by_title_similarity("........", [], limit=1) == []


def test_entity_role_binds_ontology_term_uri() -> None:
    assert lw.entity_role_ontology_uri("파트너") == "urn:lineageweave:ontology:concept/entity-role/partner"
    assert lw.entity_role_ontology_uri("고객의 고객") == (
        "urn:lineageweave:ontology:concept/entity-role/customer-customer"
    )
    document = {"title_sample": "파트너 계약 갱신"}
    lw.attach_product_fields(document)
    assert document["entity_role"] == "파트너"
    assert document["entity_role_uri"] == lw.entity_role_ontology_uri("파트너")


def test_semantic_layer_records_have_stable_uris_and_relation_rules() -> None:
    graph = {
        "nodes": [
            {"id": "doc:A", "type": "document", "entity_role": "고객"},
            {"id": "doc:B", "type": "document", "entity_role": "파트너"},
        ],
        "edges": [
            {
                "source": "doc:A",
                "target": "doc:B",
                "relation": "affiliate_affinity",
                "evidence_status": lw.EVIDENCE_INFERRED,
            }
        ],
    }
    records = lw.semantic_layer_records(graph)
    uris = {term["standard_uri"] for term in records["terms"]}
    assert "https://schema.org/CreativeWork" in uris
    assert "urn:lineageweave:ontology:concept/entity-role/customer" in uris
    assert "http://www.w3.org/2004/02/skos/core#related" in uris
    assert records["rules"]
    assert all(row["source_term_id"] and row["predicate_term_id"] and row["target_term_id"] for row in records["rules"])
    assert lw.semantic_predicate_uri("affiliate_affinity") == "http://www.w3.org/2004/02/skos/core#related"
    assert "affiliate_affinity" not in lw.TRANSITION_RELATIONS

    guarded = lw.semantic_layer_records(
        {
            "nodes": [
                {"id": "kg:custom", "type": "Custom Widget"},
                {"id": "kg:missing-type"},
                {"type": "document"},
            ],
            "edges": [
                {"source": "kg:custom", "target": "kg:custom", "relation": "custom_link"},
                {"source": "kg:missing-type", "target": "kg:custom", "relation": "custom_link"},
                {"source": "kg:custom", "target": "", "relation": "custom_link"},
            ],
        }
    )
    assert any(term["standard_uri"] == "urn:lineageweave:ontology:class/custom_widget" for term in guarded["terms"])
    assert len(guarded["edge_assertions"]) == 1


def test_factor_item_catalog_parser_is_evidence_bound_and_deduplicated() -> None:
    """Accept only allowed factors, stems, and source writings from the model."""
    factors = lw.default_factor_definitions()
    factor_id = factors[0]["factor_id"]
    parsed = lw.parse_factor_item_catalog(
        {
            "items": [
                {
                    "factor_id": factor_id,
                    "item_stem": "  납기 근거가 명시되었는가  ",
                    "polarity_code": "unexpected",
                    "evidence_document_nos": "DOC-1",
                },
                {"factor_id": factor_id, "item_stem": "납기 근거가 명시되었는가", "document_nos": ["DOC-1"]},
                {"factor_id": "unknown", "item_stem": "충분히 긴 질문이지만 잘못된 요인", "document_nos": ["DOC-1"]},
                {"factor_id": factor_id, "item_stem": "짧음", "document_nos": ["DOC-1"]},
                {"factor_id": factor_id, "item_stem": "근거 없는 질문을 추정하지 않는가", "document_nos": ["DOC-X"]},
                None,
            ]
        },
        factors,
        ["DOC-1"],
    )
    assert len(parsed) == 1
    assert parsed[0]["polarity_code"] == "neutral"
    assert parsed[0]["item_status_code"] == "candidate"
    assert parsed[0]["evidence_document_nos"] == ["DOC-1"]
    mapped = lw.parse_factor_item_catalog(
        {"items": {"one": {"factor_id": factor_id, "item_stem": "다른 근거가 문서에 있는가", "document_nos": ["DOC-1"]}}},
        factors,
        ["DOC-1"],
    )
    assert len(mapped) == 1
    assert lw.parse_factor_item_catalog({"factor_items": "invalid"}, factors, ["DOC-1"]) == []
    assert lw.parse_factor_item_catalog(None, factors, ["DOC-1"]) == []

    capped = lw.parse_factor_item_catalog(
        {
            "items": [
                {"factor_id": factor_id, "item_stem": f"고유한 문항 근거가 존재하는가 {index}", "document_nos": ["DOC-1"]}
                for index in range(lw.MAX_FACTOR_CATALOG_ITEMS + 1)
            ]
        },
        factors,
        ["DOC-1"],
    )
    assert len(capped) == lw.MAX_FACTOR_CATALOG_ITEMS


def test_factor_item_catalog_uses_multiple_report_writings_and_fails_closed() -> None:
    """Send bounded multi-report writing evidence and preserve live transport errors."""
    reports = [
        {"report_id": "R-1", "document_count": 2, "slice_kind": "pu", "slice_key": "PU-1", "document_nos": ["DOC-1", "DOC-2"]},
        {"report_id": "R-2", "document_count": 1, "slice_kind": "team", "slice_key": "TEAM-1", "document_nos": ["DOC-2"]},
    ]
    documents = [
        {"document_no": "DOC-1", "title_sample": "납기 검토", "korean_summary": "납기 약속이 확인되었다."},
        {"document_no": "DOC-2", "title_sample": "영업 기회", "korean_summary": "후속 제안 일정이 논의되었다."},
    ]
    calls: list[dict] = []

    def transport(body: dict) -> dict:
        calls.append(body)
        return {
            "items": [{
                "factor_id": lw.default_factor_definitions()[0]["factor_id"],
                "item_stem": "납기 약속이 여러 문서에서 확인되는가",
                "evidence_document_nos": ["DOC-1", "DOC-X"],
                "rationale": "두 문서의 요약에 근거가 있다",
            }]
        }

    catalog = lw.derive_factor_item_catalog_via_llm(reports, documents, transport=transport)
    assert catalog["source"] == "llm"
    assert catalog["request"] == {"task": "factor_item_catalog", "report_count": 2, "writing_count": 2}
    assert catalog["items"][0]["evidence_links"] == [{"report_id": "R-1", "document_no": "DOC-1"}]
    assert calls[0]["task"] == "factor_item_catalog"
    assert {item["document_no"] for item in calls[0]["writings"]} == {"DOC-1", "DOC-2"}
    assert lw.derive_factor_item_catalog_via_llm([], documents, transport=transport)["source"] == "empty"
    with pytest.raises(RuntimeError, match="factor_item_catalog_transport_failed"):
        lw.derive_factor_item_catalog_via_llm(reports, documents, transport=lambda _body: (_ for _ in ()).throw(OSError("offline")))

    many_reports = [
        {
            "report_id": f"R-{index}",
            "document_count": 8,
            "slice_kind": "pu",
            "slice_key": f"PU-{index}",
            "document_nos": [f"DOC-{index}-{offset}" for offset in range(8)],
        }
        for index in range(9)
    ]
    many_documents = [
        {"document_no": f"DOC-{index}-{offset}", "title_sample": "업무 기록", "korean_summary": "근거 요약"}
        for index in range(9)
        for offset in range(8)
    ]
    bounded = lw.derive_factor_item_catalog_via_llm(many_reports, many_documents, transport=lambda _body: {"items": []})
    assert bounded["request"]["writing_count"] == lw.MAX_FACTOR_CATALOG_WRITINGS


def test_factor_item_catalog_persistence_keeps_item_and_evidence_rows_separate(monkeypatch) -> None:
    """Persist candidates through the normalized item/evidence boundary."""
    class Cursor:
        def __init__(self):
            self.calls = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def executemany(self, sql, rows):
            self.calls.append((sql, list(rows)))

    class Connection:
        def __init__(self):
            self.cursor_instance = Cursor()

        def cursor(self):
            return self.cursor_instance

    monkeypatch.setattr(lw, "_ensure_operational_tables", lambda _connection: None)
    connection = Connection()
    item = {
        "item_id": "item-generated",
        "factor_id": "gm-pos-delivery",
        "item_stem": "납기 근거가 있는가",
        "evidence_links": [{"report_id": "R-1", "document_no": "DOC-1"}],
    }
    assert lw.persist_factor_item_catalog(connection, {"items": [None, {}, item]}) == 1
    assert len(connection.cursor_instance.calls) == 2
    assert connection.cursor_instance.calls[1][1] == [("item-generated", "R-1", "DOC-1", "llm_catalog")]
    assert lw.persist_factor_item_catalog(
        connection,
        {"items": [{"item_id": "item-no-evidence", "factor_id": "factor", "item_stem": "근거가 없는 후보인가"}]},
        ensure_schema=False,
    ) == 1
    assert lw.persist_factor_item_catalog(connection, {"items": []}, ensure_schema=False) == 0


def test_local_fast_mlsirm_transport_resolves_when_sibling_install_exists() -> None:
    python = lw.discover_fast_mlsirm_python()
    if not python:
        pytest.skip("sibling fast-mlsirm interpreter is not installed")
    transport, mode = lw.resolve_mlsirm_transport()
    assert mode == "fast_mlsirm_local"
    assert transport is not None
    payload = {
        "responses": [
            {"item_id": "item-gm-pos-1", "person_or_group": "D02", "response": 1},
            {"item_id": "item-gm-neg-1", "person_or_group": "D02", "response": 0},
        ],
        "items": lw.default_factor_items(),
    }
    result = lw.try_fast_mlsirm_link(payload, transport=transport)
    assert result["scores"]
    assert result["source"] == "fast_mlsirm"
    assert all(score.get("calibration_source") == "fast_mlsirm" for score in result["scores"])


def test_mlsirm_calibration_parser_rejects_untrusted_rows() -> None:
    """Accept finite package calibration rows and ignore malformed output."""
    items = [{"item_id": "item-1"}, {"item_id": "item-2"}]
    response = {
        "calibration_rows": [
            {
                "calibration_run_id": "run-1",
                "item_id": "item-1",
                "factor_id": "factor-1",
                "discrimination": 1.2,
                "difficulty": -0.1,
                "report_count": 4,
            },
            {"item_id": "missing", "factor_id": "factor-1", "discrimination": 1, "difficulty": 0, "report_count": 1},
            {"item_id": "item-2", "factor_id": "factor-1", "discrimination": 0, "difficulty": 0, "report_count": 1},
            {"item_id": "item-2", "factor_id": "factor-1", "discrimination": "bad", "difficulty": 0, "report_count": 1},
            "malformed",
        ]
    }
    parsed = lw.parse_mlsirm_calibration_rows(response, items)
    assert parsed[0]["engine_name"] == "fast_mlsirm"
    assert parsed[0]["estimator_name"] == "mmle_fipc"
    assert lw.parse_mlsirm_calibration_rows({}, items) == []
    assert lw.parse_mlsirm_calibration_rows({"calibration_rows": "invalid"}, items) == []


def test_predicted_relatedness_stays_non_transition() -> None:
    document = {"id": "doc:A", "acthguid": "thread-a", "entity_role": "시장"}
    edges = lw._predicted_entity_role_edges(
        document,
        [{"id": "doc:B", "acthguid": "thread-b", "entity_role": "시장"}],
    )
    assert edges[0]["evidence_status"] == lw.EVIDENCE_PREDICTED
    assert edges[0]["relation"] == "entity_role_affinity"
    assert edges[0]["relation"] not in lw.TRANSITION_RELATIONS
    with pytest.raises(ValueError, match="cannot be promoted"):
        lw.make_lineage_edge(
            source="doc:A",
            target="doc:B",
            relation="row_successor",
            reason="illegal",
            evidence_status=lw.EVIDENCE_PREDICTED,
        )


def test_event_lineage_separates_observed_order_from_relatedness() -> None:
    lineage = lw.build_event_lineage(
        {
            "id": "doc:A",
            "document_no": "A",
            "document_events": [
                {"guid": "row-1", "event": "VOC", "timestamp": "2026-01-01"},
                {"guid": "row-2", "event": "review", "timestamp": "2026-01-02"},
                {"guid": "row-3", "event": "close", "timestamp": "2026-01-03"},
            ],
        },
        [
            {
                "source": "row:row-1",
                "target": "row:row-2",
                "relation": "row_successor",
                "evidence_status": lw.EVIDENCE_OBSERVED,
            },
            {
                "source": "doc:A",
                "target": "doc:B",
                "relation": "topic_affinity",
                "evidence_status": lw.EVIDENCE_INFERRED,
            },
            {
                "source": "doc:UNRELATED-1",
                "target": "doc:UNRELATED-2",
                "relation": "topic_affinity",
                "evidence_status": lw.EVIDENCE_INFERRED,
            },
        ],
    )
    assert lineage["inferred_count"] == 1
    assert lineage["beads"][0]["kind"] == "event"
    assert len(lineage["beads"]) == 3
    assert [item["connects_to_next"] for item in lineage["beads"]] == [True, False, False]
    assert lineage["has_observed_transition"] is True
    assert lw.build_event_lineage(
        {"document_no": "B", "document_events": [{"guid": "row-4", "event": "open"}, {"guid": "row-5", "event": "close"}]},
        [],
    )["has_observed_transition"] is False
    assert lineage["relatedness"][0]["kind"] == "relatedness"
    assert all(item["kind"] != "relatedness" for item in lineage["beads"])
    react = Path("web/src/App.jsx").read_text(encoding="utf-8")
    assert 'renderEventLineage("popupLineage")' in react
    assert "lineage-chain" in react
    assert "event_lineage" in react
    assert "const lineageBeads = selectedDocument?.document_no === selectedNo" in react
    assert "detail?.event_lineage?.beads || []" in react
    assert "detail?.event_lineage?.relatedness || []" in react
    assert "lineageRelatedness" in react
    assert "partitionLineageBeads" in react
    assert "lineage-segments" in react
    assert "전이 근거가 없는 사건은 독립적으로 표시합니다." in react
    assert "확인된 사건 전이가 없어 Lineage로 연결하지 않습니다." in react
    assert "독립 관측" in react
    assert "documentRows.slice(0, 24)" not in react
    lineage_panel = react.split("<span>글 자체의 Lineage</span>", 1)[1].split("</section>", 1)[0]
    assert "documentRows" not in lineage_panel
    assert "bead.connects_to_next === true" in react
    assert "has_observed_transition === true" in react
    assert "사건 간 전이 근거가 확인되지 않아 Lineage로 연결하지 않습니다." in react
    assert 'bead.kind === "event" && beads[index + 1]?.kind === "event"' not in react
    browser_check = Path("web/e2e/lineageweave.mjs").read_text(encoding="utf-8")
    assert "bead.connects_to_next === true" in browser_check
    assert 'bead.kind === "event" && beads[index + 1]?.kind === "event"' not in browser_check
    assert "일반 경영" in react
    assert "산업별" in react
    assert "영업 Lead" in react
    assert "report-factors" in react
    assert "visibilityLabel(selectedDocument.visibility)" in react


def test_event_chat_cites_ontology_or_semantic_layer_identifier() -> None:
    result = lw.normalize_event_chat_response(
        {"answer": "고객 계열 단서로 이어집니다.", "evidence_ids": ["row-1"]},
        [{"guid": "row-1", "title": "VOC"}],
        "D1",
        semantic_context={
            "node_terms": [
                {
                    "standard_uri": "urn:lineageweave:ontology:concept/entity-role/customer",
                    "term_label": "Customer",
                }
            ]
        },
    )
    uris = {item.get("term_uri") or item.get("guid") for item in result["citations"]}
    assert "row-1" in uris
    assert "urn:lineageweave:ontology:concept/entity-role/customer" in uris
    assert result["evidence_ids"] == ["row-1"]
    assert result["semantic_term_uris"] == [
        "urn:lineageweave:ontology:concept/entity-role/customer"
    ]


def test_affiliate_tree_parent_child() -> None:
    tree = lw.build_affiliate_tree(["Acme", "Acme Korea", "Acme Korea Gwangju"])
    assert lw.affiliate_parent_child("Acme", "Acme Korea", tree) is True
    assert lw.affiliate_parent_child("Acme Korea", "Acme Korea Gwangju", tree) is True
    assert lw.affiliate_parent_child("Acme Korea Gwangju", "Acme", tree) is False


def test_org_unit_affiliate_tree_links_corp_to_pu_and_is_lineage_clue() -> None:
    documents = [
        {
            "id": "doc:A",
            "type": "document",
            "document_no": "A",
            "title_sample": "Grid meeting",
            "corp_code": "CWL1",
            "owner_pu": "PU01",
            "keyman_our_side": [{"person_name": "Ana", "org_name": "North Grid"}],
            "keyman_counterpart_side": [],
        },
        {
            "id": "doc:B",
            "type": "document",
            "document_no": "B",
            "title_sample": "PU handoff",
            "corp_code": "CWL1",
            "owner_pu": "PU02",
            "keyman_our_side": [],
            "keyman_counterpart_side": [{"person_name": "Bo", "org_name": "North Grid"}],
        },
    ]
    tree = lw.build_org_unit_affiliate_tree(documents)
    assert lw.affiliate_parent_child("Corp CWL1", "Corp CWL1 PU PU01", tree) is True
    assert lw.affiliate_parent_child("Corp CWL1", "Corp CWL1 PU PU02", tree) is True
    assert lw.affiliate_parent_child("Corp CWL1", "North Grid", tree) is True
    inferred = lw._inferred_affiliate_edges(documents, tree)
    assert inferred
    assert all(edge["relation"] == "affiliate_affinity" for edge in inferred)
    assert all(edge["evidence_status"] == lw.EVIDENCE_INFERRED for edge in inferred)
    assert all(edge["relation"] not in lw.TRANSITION_RELATIONS for edge in inferred)


def test_keyman_affinity_edges_are_inferred_and_not_transitions() -> None:
    documents = [
        {
            "id": "doc:A",
            "document_no": "A",
            "keyman_our_side": [{"person_name": "Mark Hill", "org_name": "OMEXOM"}],
            "keyman_counterpart_side": [{"person_name": "", "org_name": "SPEN"}],
        },
        {
            "id": "doc:B",
            "document_no": "B",
            "keyman_our_side": [{"person_name": "Mark Hill", "org_name": "OMEXOM"}],
            "keyman_counterpart_side": [{"person_name": "", "org_name": "SPEN"}],
        },
        {
            "id": "doc:C",
            "document_no": "C",
            "keyman_our_side": [],
            "keyman_counterpart_side": [{"person_name": "Other Person", "org_name": "Other Co"}],
        },
    ]
    inferred = lw._inferred_keyman_affinity_edges(documents)
    pairs = {(edge["source"], edge["target"]) for edge in inferred}
    assert ("doc:A", "doc:B") in pairs
    assert all(edge["relation"] == "keyman_affinity" for edge in inferred)
    assert all(edge["evidence_status"] == lw.EVIDENCE_INFERRED for edge in inferred)
    assert all(edge["relation"] not in lw.TRANSITION_RELATIONS for edge in inferred)
    assert all("doc:C" not in (edge["source"], edge["target"]) for edge in inferred)


def test_build_payload_attaches_product_fields() -> None:
    payload = lw.build_payload(
        [
            _row(
                guid="g1",
                docno="D1",
                acthguid="T1",
                date="2026-01-01",
                title="파트너 계약 갱신 — Mr. Jordan Gil 미팅",
            )
        ],
        keyman_transport=_keyman_fixture_transport,
    )
    docs = [node for node in payload["nodes"] if node["type"] == "document"]
    assert len(docs) == 1
    assert docs[0]["entity_role"] == "파트너"
    assert docs[0]["visibility"] in {lw.VISIBILITY_PUBLIC, lw.VISIBILITY_PRIVATE}
    assert docs[0]["keymen"] == ["Fixture analyst", "Fixture partner", "Fixture stakeholder"]
    assert docs[0]["keyman_our_side"][0]["person_name"] == "Fixture analyst"
    assert docs[0]["keyman_counterpart_side"][0]["org_name"] == "Fixture partner org"
    assert docs[0]["keyman_source"] == "llm"
    assert docs[0]["keyman_status"] == "orchestrator"
    assert docs[0]["created_by"] == "fixture-user"
    assert docs[0]["korean_summary"]
    assert docs[0]["roles_and_responsibilities"]
    assert "affiliate_tree" in payload
    assert "access_directory" in payload
    actor = server._actor_from_value(
        {"sub": "acct-fixture-1", "org": "CWL1", "workspace": "PU01", "role": "reader"}
    )
    assert actor is not None
    assert lw.authorize_access(actor=actor, resource=docs[0], action="read")["allowed"] is True


def test_keyman_comes_from_llm_transport_not_regex() -> None:
    calls: list[dict] = []

    def transport(body: dict) -> dict:
        calls.append(body)
        return {"keymen": ["Lee Min"]}

    result = lw.derive_keymen_via_llm(
        "파트너 계약 갱신 — Mr. Jordan Gil 미팅",
        transport=transport,
        authors={"created_by": "fixture-user", "changed_by": "fixture-user", "user_id": "fixture-user"},
    )
    assert result["our_side"] == [{"person_name": "fixture-user", "org_name": ""}]
    assert result["counterpart_side"] == [{"person_name": "Lee Min", "org_name": ""}]
    assert result["names"] == ["fixture-user", "Lee Min"]
    assert result["source"] == "llm"
    assert result["status"] == "orchestrator"
    assert "Jordan Gil" in result["request"]["hints"]
    assert result["request"]["authors"]["created_by"] == "fixture-user"
    assert calls[0]["orchestration"]["conductor_role"] == "worker"
    assert calls[0]["orchestration"]["fugu_routing_vs_composition"] == "single_model_routing"
    assert calls[0]["orchestration"]["trinity_test_time_compute"] == "budgeted"
    fixture_result = lw.derive_keymen_via_llm("any title", transport=_keyman_fixture_transport)
    assert fixture_result["names"] == ["Fixture analyst", "Fixture partner", "Fixture stakeholder"]
    assert fixture_result["our_side"][0]["person_name"] == "Fixture analyst"
    assert len(fixture_result["counterpart_side"]) == 2
    assert fixture_result["source"] == "llm"
    assert fixture_result["status"] == "orchestrator"


def test_separate_keyman_sides_keeps_title_org_on_counterpart_only() -> None:
    """A duplicated LLM person/org pair must not appear on both popup sides."""
    our, counterpart = lw.separate_keyman_sides(
        [{"person_name": "Mark Hill", "org_name": "SPEN"}],
        [{"person_name": "Mark Hill", "org_name": "SPEN"}],
        title="[SPEN] Mark Hill STATCOM  Tender Meeting",
        authors={"created_by": "Kim"},
    )
    assert our == [{"person_name": "Kim", "org_name": ""}]
    assert counterpart == [{"person_name": "Mark Hill", "org_name": "SPEN"}]
    derived = lw.derive_keymen_via_llm(
        "[SPEN] Mark Hill STATCOM  Tender Meeting",
        transport=lambda _body: {
            "our_side": [{"person_name": "Mark Hill", "org_name": "SPEN"}],
            "counterpart_side": [{"person_name": "Mark Hill", "org_name": "SPEN"}],
        },
        authors={"created_by": "Kim"},
    )
    assert derived["our_side"] == [{"person_name": "Kim", "org_name": ""}]
    assert derived["counterpart_side"] == [{"person_name": "Mark Hill", "org_name": "SPEN"}]


def test_keyman_llm_response_includes_both_sides() -> None:
    def transport(body: dict) -> dict:
        assert body["shape"] == "two_sided"
        return {
            "our_side": [
                {"person_name": "Kim", "org_name": "Plant A"},
                {"person_name": "Lee", "org_name": "Plant B"},
            ],
            "counterpart_side": [
                {"person_name": "Gil", "org_name": "Buyer"},
                {"person_name": "Chen", "org_name": "EPC"},
            ],
        }

    result = lw.derive_keymen_via_llm("협력사 방문", transport=transport)
    assert result["source"] == "llm"
    assert {row["org_name"] for row in result["our_side"]} == {"Plant A", "Plant B"}
    assert {row["org_name"] for row in result["counterpart_side"]} == {"Buyer", "EPC"}


def test_live_keyman_http_posts_request_shape(monkeypatch) -> None:
    captured: dict = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": json.dumps({"keymen": ["Example Keyman"]})}}]}
            ).encode("utf-8")

    def fake_urlopen(request, timeout=None, context=None):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setenv("LLM_GATEWAY_URL", "https://example.test")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "test-token")
    monkeypatch.delenv("ORCHESTRATOR_BASE_URL", raising=False)
    monkeypatch.setattr(lw.urllib.request, "urlopen", fake_urlopen)
    transport = lw.make_live_keyman_transport()
    result = transport(
        {
            "task": "keyman_extract",
            "title": "협력사 방문",
            "authors": {"created_by": "fixture-user"},
            "orchestration": dict(lw.KEYMAN_PAPER_VARIABLES),
        }
    )
    assert result["keymen"] == ["Example Keyman"]
    assert captured["url"].endswith("/v1/chat/completions")
    user_content = json.loads(captured["payload"]["messages"][1]["content"])
    assert user_content["task"] == "keyman_extract"
    assert user_content["authors"]["created_by"] == "fixture-user"
    assert user_content["orchestration"]["conductor_role"] == "worker"


def test_persist_analysis_payload_writes_postgres_tables() -> None:
    payload = lw.build_payload(
        [_row(guid="g1", docno="D1", acthguid="T1", date="2026-01-01", title="파트너 미팅")],
        keyman_transport=_keyman_fixture_transport,
    )
    with lw.psycopg.connect(_test_dsn()) as connection:
        connection.autocommit = False
        lw.persist_knowledge_graph_additions(
            connection,
            {
                "nodes": [
                    {"id": "kg:organization_alias:fixture", "type": "organization_alias", "label": "Alias"},
                    {"id": "kg:organization:fixture", "type": "organization", "label": "Canonical"},
                ],
                "edges": [
                    {
                        "source": "kg:organization_alias:fixture",
                        "target": "kg:organization:fixture",
                        "relation": "organization_alias",
                        "evidence_id": "fixture-review",
                        "evidence_status": lw.EVIDENCE_INFERRED,
                    }
                ],
            },
        )
        written = lw.persist_analysis_payload(connection, payload)
        rows = lw._database_query(
            connection,
            "SELECT document_no, keyman_source, jsonb_array_length(keyman_our_side) AS our_count "
            f"FROM {lw.ANALYSIS_DOCUMENT_TABLE} WHERE document_no = %s",
            ("D1",),
        )
        alias_rows = lw._database_query(
            connection,
            f"SELECT source_node FROM {lw.ANALYSIS_KG_EDGE_TABLE} WHERE relation_name = %s",
            ("organization_alias",),
        )
        connection.rollback()
    assert written["document_rows"] >= 1
    assert rows[0]["document_no"] == "D1"
    assert rows[0]["keyman_source"] == "llm"
    assert int(rows[0]["our_count"] or 0) >= 1
    assert alias_rows == [{"source_node": "kg:organization_alias:fixture"}]


def test_event_lineage_chat_uses_http_transport() -> None:
    document = {
        "document_no": "D1",
        "title_sample": "파트너 미팅",
        "document_events": [
            {"guid": "g1", "event": "VOC", "title": "초안", "timestamp": "2026-01-01"},
            {"guid": "g2", "event": "REV", "title": "수정", "timestamp": "2026-01-02"},
        ],
    }
    result = lw.derive_event_lineage_chat(
        document,
        "무슨 일이 있었나",
        transport=lambda body: {
            "answer": "초안에서 수정으로 이어졌습니다.",
            "citations": [{"guid": "g1", "label": "초안"}],
            "model": "fixture-narrator",
        },
    )
    assert "수정" in result["answer"]
    assert result["citations"][0]["guid"] == "g1"
    assert result["citations"][0]["evidence_id"] == "g1"
    assert result["citations"][0]["citation_kind"] == "voc"


def test_voc_evidence_candidates_skip_document_numbers() -> None:
    """A document number is not a VOC guid; use the observed event guid instead."""
    assert lw.voc_evidence_guid_candidates(
        "DOC-1",
        "DOC-1",
        [{"guid": "row-1", "title": "근거"}],
    ) == ["row-1"]
    assert lw.voc_evidence_guid_candidates("https://example.test/term", "DOC-1", []) == []


def test_event_chat_citations_are_authorized_and_nonempty() -> None:
    result = lw.normalize_event_chat_response(
        {"answer": "관찰된 변경입니다.", "evidence_ids": ["hidden-guid"]},
        [{"guid": "visible-guid", "title": "근거"}],
        "D1",
    )
    assert result["citations"] == [
        {"guid": "visible-guid", "evidence_id": "visible-guid", "citation_kind": "voc", "label": "근거"}
    ]
    assert result["evidence_ids"] == ["visible-guid"]


def test_keyman_prefers_newest_list_documents() -> None:
    rows = [
        _row(guid="a1", docno="A1", acthguid="SMALL", date="2026-01-01", title="작은 스레드"),
        _row(guid="b1", docno="B1", acthguid="BIG", date="2026-01-01", title="큰 스레드 1"),
        _row(guid="b2", docno="B2", acthguid="BIG", date="2026-01-02", title="큰 스레드 2"),
        _row(guid="b3", docno="B3", acthguid="BIG", date="2026-01-03", title="큰 스레드 3"),
    ]
    payload = lw.build_payload(rows, keyman_transport=_keyman_fixture_transport, keyman_limit=2)
    keyed = {
        node["document_no"]: node
        for node in payload["nodes"]
        if node["type"] == "document"
    }
    assert keyed["B3"]["keyman_source"] == "llm"
    assert keyed["B2"]["keyman_source"] == "llm"
    assert keyed["A1"]["keyman_source"] == "pending"
    assert keyed["B3"]["document_events"]


def test_common_enum_table_is_two_word_snake_case() -> None:
    assert lw.assert_common_table_name(lw.COMMON_ENUM_TABLE) == "common_enum_values"
    with pytest.raises(ValueError):
        lw.assert_common_table_name("enums")
    with pytest.raises(ValueError, match="invalid table identifier"):
        lw.assert_common_table_name("common_values;drop")
    families = lw.load_common_enum_values(lw.DEFAULT_ENUM_ROWS)
    assert "파트너" in families["entity_role"]
    assert "고객의 고객" in families["entity_role"]
    assert "public" in families["visibility"]
    assert families["ticket_status"] == ["open", "in_progress", "resolved"]
    assert lw.validate_ticket_status("resolved") == "resolved"
    with pytest.raises(ValueError, match="unknown ticket status"):
        lw.validate_ticket_status("not_a_ticket_status")
    assert lw.classify_entity_role("파트너 계약 갱신", families) == "파트너"


def test_web_page_uses_verified_session_and_real_api() -> None:
    react = Path("web/src/App.jsx").read_text(encoding="utf-8")
    ui_model = Path("web/src/ui-model.js").read_text(encoding="utf-8")
    login_e2e = Path("web/e2e/login-gate.mjs").read_text(encoding="utf-8")
    browser_e2e = Path("web/e2e/lineageweave.mjs").read_text(encoding="utf-8")
    styles = Path("web/src/styles.css").read_text(encoding="utf-8")
    server_source = Path("lineageweave_server.py").read_text(encoding="utf-8")
    assert 'id="popupKeymanOur"' in react
    assert 'id="popupKeymanCounterpart"' in react
    assert "분석 상태" in react
    assert "관리 상태" in react
    assert 'const canManage = (session?.roles || []).some((role) => ["author", "editor", "admin"].includes(role));' in react
    assert 'const keymanEditor = modal.locator(".modal-keyman-editor");' in browser_e2e
    assert "if (!canManageVisibility)" in browser_e2e
    assert "keyman_editor_visible" in browser_e2e
    assert "자동 도출" in react
    assert "사용자 관리" in react
    assert "source: {selectedDocument.keyman_source" not in react
    assert "status: {selectedDocument.keyman_status" not in react
    assert "document.getElementById" not in react
    assert "const selectedDocument" in react
    assert "ticketStatusOptions" in react
    assert "updateTicketStatus" in react
    assert "/tickets/${encodeURIComponent(ticket.ticket_id)}" in react
    assert 'api("/api/session")' in react
    assert 'api("/api/session", {' not in react
    assert "form.accountId.value" not in react
    assert "form.accountSecret.value" not in react
    assert 'id="accountId"' not in react
    assert 'id="accountSecret"' not in react
    assert 'id="loginBtn"' in react
    assert 'id="loginForm"' in react
    assert 'id="loginEmail"' in react
    assert 'href="/api/login"' not in react
    assert 'api("/api/login", {' in react
    assert "window.location.assign(result.authorization_url)" in react
    login_handler = react.split("async function startKeyverseLogin", 1)[1].split(
        "async function loadMore", 1
    )[0]
    assert "const email = validatedEmailAddress();" in login_handler
    assert login_handler.index("const email = validatedEmailAddress();") < login_handler.index('api("/api/login", {')
    assert "emailValidationMessage" in react
    assert "업무 이메일을 입력해 주세요." in ui_model
    assert "올바른 업무 이메일 주소를 입력해 주세요." in ui_model
    assert "로그인을 시작할 수 없습니다. 잠시 후 다시 시도하거나 관리자에게 문의해 주세요." in react
    assert 'id="registerForm"' not in react
    assert 'id="registerBtn"' not in react
    assert "글 자체의 Lineage" in react
    assert "업무 이메일을 입력하고 계속하세요." in react
    assert "법인·PU는 인증된 Keyverse 계정 속성으로 적용됩니다. 이 화면에서 직접 입력하지 않습니다." in react
    assert ">Keyverse로 계속<" not in react
    assert ">패스키 등록 요청<" not in react
    assert ">계속하기<" in react
    assert "처음 이용하기" not in react
    assert "OIDC" not in react
    assert "PKCE" not in react
    assert "SSO" not in react
    assert "글 자체의 Lineage" in react
    assert "LINEAGEWEAVE_E2E_LOGIN_EXPECT_UNAVAILABLE" in login_e2e
    assert "member@example.com" in login_e2e
    assert "OIDC|PKCE|SSO" in login_e2e
    assert "법인 코드와 PU 코드는 인증된 계정 속성입니다." not in react
    assert "패스키가 있으면 Keyverse SSO로 로그인합니다." not in react
    assert 'type="password"' not in react
    assert "/api/register" not in react
    assert "/api/register/complete" not in react
    browser_check = Path("web/e2e/lineageweave.mjs").read_text(encoding="utf-8")
    assert "LINEAGEWEAVE_E2E_ENROLL_PASSKEY" not in browser_check
    assert "/api/register" not in browser_check
    assert 'const isIdentityForm = Boolean(loginResponse?.ok())' in browser_check
    assert "if (isIdentityForm &&" in browser_check
    assert 'reached_identity_authority: false' in browser_check
    assert 'preauthenticated_session: true' in browser_check
    assert "a preauthenticated development session cannot prove Keyverse login acceptance" in browser_check
    assert 'result.keyman_llm_status = "not_authorized"' in browser_check
    assert 'if (await derive.count() > 0)' in browser_check
    assert 'chat_citation_count' in browser_check
    assert 'the live lineage chat returned no answer text' in browser_check
    assert 'chat_source' in browser_check
    assert 'fetch("/api/admin/lineage/edges?limit=3"' in browser_check
    assert "payload?.items?.length || 0" in browser_check
    assert "edge_parent" in browser_check
    assert "customerRelationEvidenceLinkCount" in browser_check
    assert "the customer relation rendered no source-document link" in browser_check
    assert '계정별 권한 편집' in browser_check
    assert "navigator.credentials.create" not in react
    assert "window.PublicKeyCredential" not in react
    assert "window.location.assign(result.enrollment_url)" not in react
    assert "http://localhost:5173/" not in react
    assert 'href="/api/logout"' in react
    assert '"login_hint": email' in server_source
    assert "api/v1/session" not in server_source
    assert "keyverse_oidc_redirect_required" in server_source
    assert "start_keyverse_enrollment" not in server_source
    assert "complete_keyverse_enrollment" not in server_source
    assert "KEYVERSE_REGISTRATION_URL" not in server_source
    assert 'method: "POST"' in react
    assert "/api/analytics" in react
    assert "/api/documents/" in react
    assert "관련도순으로 표시합니다." in react
    assert "관련도 ${Math.round(Number(item.similarity || 0) * 100)}% · 원문과 타임라인 보기" in react
    assert 'className={semanticSearch ? "search-result-detail" : ""}' in react
    assert ".search-result-detail" in styles
    assert "/evidence/" in react
    assert "/knowledge?" in react
    assert "/chat" in react
    assert "글 목록" in react
    assert 'id="popupRoles"' in react
    assert 'id="affiliateTree"' in react
    assert 'id="popupChat"' in react
    assert 'id="popupKnowledge"' in react
    assert 'id="popupKnowledgeEdges"' in react
    assert "function openKnowledgeNode" in react
    assert "knowledge-node-link" in react
    assert ".knowledge-node-link" in styles
    assert "knowledgeEdgeRows" in react
    assert "function knowledgeEdgeRows" in ui_model
    assert "연결 관계와 방향" in react
    assert "관계 유형:" in react
    assert "(knowledge.nodes || []).map" in react
    assert 'id="popupTodos"' in react
    assert 'id="popupCalendar"' in react
    assert 'id="popupAppointments"' in react
    assert 'id="periodReports"' in react
    assert 'id="reportDetail"' in react
    assert "function reportBusinessTitle" in react
    assert "function reportVerdictLabel" in react
    assert "function reportLinkingLabel" in react
    assert "function reportJudgeSourceLabel" in react
    assert "function customerTierLabel" in react
    assert "function customerRelationSourceLabel" in react
    assert "function customerRelationLabel" in react
    assert "report?.slice_label" in react
    assert "reportBusinessTitle(report)" in react
    assert "reportVerdictLabel(report.judge?.verdict)" in react
    assert "reportLinkingLabel(score.linking_method)" in react
    assert "reportJudgeSourceLabel(selectedReport.judge?.source)" in react
    assert "customerTierLabel(account.tier)" in react
    assert "customerRelationSourceLabel(edge.source)" in react
    assert "customerRelationLabel(edge.relation)" in react
    assert "edge.document_nos.map" in react
    assert "의미 관계:" in react
    assert "report.period_kind} · {report.slice_key" not in react
    assert 'account.tier || "hq"' not in react
    assert 'className="report-document-link"' in react
    assert 'aria-label="리포트 품질 평가 지표"' in react
    assert "품질 평가 지표" in react
    assert "LLM Judge · RAGAS 지표" not in react
    assert "selectedReport.judge?.source ||" not in react
    assert 'score.linking_method || "linked"' not in react
    assert "reportMetricLabels" in react
    assert 'className="report-metric"' in react
    assert 'className="report-metric-evidence"' in react
    assert 'className="report-metric-list"' in react
    assert ".report-metric-verdict.pass" in styles
    assert 'api("/api/queue/health")' in react
    assert 'id="metricQueue"' in react
    assert 'id="userHome"' in react
    assert "업무 홈" in react
    assert "WORKSPACE HOME" not in react
    assert "RECENT WORK" not in react
    assert "CUSTOMER MASTER" not in react
    assert "SOURCE EVIDENCE" not in react
    assert "CUSTOMER INTELLIGENCE" not in react
    assert "CUSTOMER ACCOUNT" not in react
    assert "오늘의 고객·업무 인사이트" in react
    assert 'useState("home")' in react
    assert 'const [documentLoadState, setDocumentLoadState] = useState("loading")' in react
    assert 'const [customerLoadState, setCustomerLoadState] = useState("loading")' in react
    assert "현재 권한 범위에서 확인할 업무 글이 없습니다." in react
    assert "업무 글을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요." in react
    assert "현재 권한 범위에서 연결된 고객 마스터가 없습니다." in react
    assert "고객 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요." in react
    assert "검색 결과가 없습니다." in react
    assert ".home-metrics" in styles
    assert ".home-columns" in styles
    assert 'id="customerScreen"' in react
    assert "고객 화면" in react
    assert "근거 연결" in react
    assert "공개</option>" in react
    assert "비공개</option>" in react
    assert "source ·" not in react
    assert "heuristic" not in react
    assert ">public<" not in react
    assert ">private<" not in react
    assert "displayCustomerTotal}개 고객" in react
    assert "고객 정보를 불러오는 중입니다." in react
    assert "customerTreeRows" in react
    assert "function customerTreeRows" in ui_model
    assert 'aria-label="고객 계열 관계"' in react
    assert 'role="treeitem"' in react
    assert 'api(`/api/customers?limit=100${query}`)' in react
    assert 'id="adminMode"' in react
    assert "관리자 모드" in react
    assert 'api(`/api/admin/keyverse/accounts?limit=50${query}`)' in react
    assert '/api/admin/keyverse/accounts/${encodeURIComponent(selectedAdminId)}/claims' in react
    assert "Keyverse 원장에 저장" in react
    assert "계정 원장이 연결되지 않아 계정별 권한 편집을 사용할 수 없습니다" in react
    assert "게시글 권한 통제와 Lineage 검토는 계속 사용할 수 있습니다" in react
    assert 'id="accessPolicyScreen"' in react
    assert 'const [adminDocuments, setAdminDocuments] = useState([])' in react
    assert 'api(`/api/documents?limit=20&offset=0${query}`)' in react
    assert 'aria-label="게시글 권한 검색"' in react
    assert 'loadMoreAdminDocuments' in react
    assert 'adminDocumentTotal' in react
    assert '.admin-document-policy-list > input' in styles
    assert 'id="lineageReviewScreen"' in react
    assert 'id="enrichmentScreen"' in react
    assert 'api("/api/admin/enrichment/status")' in react
    assert '"/api/admin/enrichment/run"' in react
    assert 'api("/api/admin/reports/refresh"' in react
    assert 'id="refreshReportsBtn"' in react
    assert 'id="teppScreen"' in react
    assert 'api("/api/admin/tepp/status")' in react
    assert '"/api/admin/tepp/analysis-runs"' in react
    assert "TEPP 분석 접수" in react
    assert "TEPP endpoint unavailable" in react
    assert '/api/admin/lineage/edges?limit=100${query}' in react
    assert '"/api/admin/lineage/edges/override"' in react
    assert ".policy-rule-grid" in styles
    assert "const canAdmin" in react
    assert '["api", "customers"]' in server_source
    assert "keyverse_admin_accounts" in server_source
    assert '["api", "admin", "lineage", "edges"]' in server_source
    assert '["api", "admin", "enrichment", "status"]' in server_source
    assert '["api", "admin", "enrichment", "run"]' in server_source
    assert '["api", "admin", "reports", "refresh"]' in server_source
    assert "refresh_reports" in server_source
    assert "update_lineage_edge_override" in server_source


def test_document_detail_has_a_focused_primary_and_follow_up_rail() -> None:
    """Keep the detailed workflow in the two-column shape of the target reference."""
    react = Path("web/src/App.jsx").read_text(encoding="utf-8")
    styles = Path("web/src/styles.css").read_text(encoding="utf-8")
    for class_name in (
        "modal-summary",
        "modal-timeline",
        "modal-lineage-card",
        "modal-knowledge",
        "modal-tickets",
        "modal-appointments",
    ):
        assert class_name in react
        assert f".detail-card.{class_name}" in styles
    assert "width: min(1240px" in styles
    assert "grid-template-columns: minmax(0, 1.65fr) minmax(300px, .9fr)" in styles
    assert "border-top: 4px solid var(--blue)" in styles


def test_chat_events_prefer_rows_then_persisted_document_events() -> None:
    from_rows = lw.chat_events_from_document_detail(
        {
            "rows": [{"guid": "row-guid", "event": "observed_row", "title": "row title"}],
            "document": {
                "document_events": [{"guid": "persisted-guid", "event": "stale", "title": "old"}]
            },
        }
    )
    assert from_rows[0]["evidence_id"] == "row-guid"
    from_persist = lw.chat_events_from_document_detail(
        {
            "rows": [],
            "document": {
                "title_sample": "OMEXOM Meeting",
                "document_events": [{"guid": "src-guid", "event": "Z", "title": "OMEXOM Meeting"}],
            },
        }
    )
    assert from_persist[0]["evidence_id"] == "src-guid"
    assert from_persist[0]["title"] == "OMEXOM Meeting"


def test_filter_payload_reconciles_persisted_run_metrics() -> None:
    payload = {
        "metadata": {"row_count": 43814, "document_count": 43707, "thread_count": 42467},
        "analytics": {},
        "nodes": [
            {
                "id": "doc:D1",
                "type": "document",
                "document_no": "D1",
                "corp_code": "CWL1",
                "owner_pu": "PU01",
                "visibility": lw.VISIBILITY_PUBLIC,
            }
        ],
        "edges": [],
        "affiliate_tree": {"nodes": [], "edges": []},
        "knowledge_graph": {"nodes": [], "edges": []},
    }
    filtered = lw.filter_payload_for_actor(
        payload, {"corp_code": "CWL1", "pu_code": "PU01", "roles": ["reader"]}
    )
    assert filtered["analytics"]["total_rows"] == 43814
    assert filtered["analytics"]["total_documents"] == 1
    assert filtered["analytics"]["multi_document_threads"] == 42467


def test_live_keyman_config_rejects_compose_standin(monkeypatch) -> None:
    monkeypatch.setattr(lw, "load_runtime_env", lambda path=None: None)
    monkeypatch.setenv("ORCHESTRATOR_BASE_URL", lw.COMPOSE_STANDIN_URL)
    monkeypatch.setenv("ORCHESTRATOR_TOKEN", "standin")
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    monkeypatch.delenv("LLM_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="LLM_GATEWAY_URL"):
        lw.live_http_config()


def test_compose_worker_url_can_use_the_compose_network(monkeypatch) -> None:
    monkeypatch.setenv("LINEAGEWEAVE_COMPOSE_STANDIN_URL", "http://lineage-http-standin:8080/")
    assert lw.compose_standin_url() == "http://lineage-http-standin:8080"


def test_compose_worker_has_no_default_bearer_token(monkeypatch) -> None:
    import os

    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{}'

    def fake_urlopen(request, **_kwargs):
        captured.append(request)
        return Response()

    monkeypatch.setenv("ORCHESTRATOR_BASE_URL", "http://worker.example")
    monkeypatch.delenv("ORCHESTRATOR_TOKEN", raising=False)
    monkeypatch.setattr(lw.urllib.request, "urlopen", fake_urlopen)
    assert lw.compose_standin_transport({"task": "event_lineage_chat"}) == {}
    assert captured[-1].get_header("Authorization") is None

    monkeypatch.setenv("ORCHESTRATOR_TOKEN", "operator-worker-token")
    lw.compose_standin_transport({"task": "content_inspection"})
    assert captured[-1].get_header("Authorization") == "Bearer operator-worker-token"

    monkeypatch.delenv("ORCHESTRATOR_TOKEN")
    monkeypatch.setattr(lw, "load_runtime_env", lambda path=None: None)
    assert lw.ensure_compose_standin() == "live_url_present"
    assert "ORCHESTRATOR_TOKEN" not in os.environ


def test_persist_keeps_existing_llm_keyman_on_structure_rebuild() -> None:
    first = lw.build_payload(
        [_row(guid="g1", docno="D-KEEP", acthguid="T1", date="2026-01-01", title="파트너 미팅")],
        keyman_transport=_keyman_fixture_transport,
        keyman_limit=1,
    )
    rebuilt = lw.build_payload(
        [_row(guid="g1", docno="D-KEEP", acthguid="T1", date="2026-01-01", title="파트너 미팅")],
        keyman_limit=0,
    )
    with lw.psycopg.connect(_test_dsn()) as connection:
        connection.autocommit = False
        lw.persist_analysis_payload(connection, first)
        lw.persist_analysis_payload(connection, rebuilt)
        rows = lw._database_query(
            connection,
            f"SELECT keyman_source, keyman_our_side, keyman_counterpart_side FROM {lw.ANALYSIS_DOCUMENT_TABLE} WHERE document_no = %s",
            ("D-KEEP",),
        )
        people = lw._database_query(
            connection,
            f"SELECT label FROM {lw.ANALYSIS_KG_NODE_TABLE} WHERE node_type = 'person'",
        )
        affiliates = lw._database_query(
            connection,
            f"SELECT parent_label, child_label FROM {lw.ANALYSIS_AFFILIATE_TABLE}",
        )
        connection.rollback()
    assert any("Fixture analyst" in str(row.get("label")) for row in people)
    assert any(
        row.get("parent_label") == "Corp CWL1" and "PU" in str(row.get("child_label"))
        for row in affiliates
    )
    assert rows[0]["keyman_source"] == "llm"
    our = rows[0]["keyman_our_side"]
    counterpart = rows[0]["keyman_counterpart_side"]
    if isinstance(our, str):
        our = json.loads(our)
    if isinstance(counterpart, str):
        counterpart = json.loads(counterpart)
    assert our[0]["person_name"] == "Fixture analyst"
    assert counterpart[0]["person_name"] == "Fixture partner"


def test_persist_keeps_llm_keyman_after_limited_then_full_rebuild() -> None:
    """A later limited persist must not drop llm Keyman that is absent from the subset."""
    first = lw.build_payload(
        [_row(guid="g1", docno="D-KEEP", acthguid="T1", date="2026-01-01", title="파트너 미팅")],
        keyman_transport=_keyman_fixture_transport,
        keyman_limit=1,
    )
    limited = lw.build_payload(
        [_row(guid="g2", docno="D-OTHER", acthguid="T2", date="2026-01-02", title="다른 글")],
        keyman_limit=0,
    )
    rebuilt = lw.build_payload(
        [
            _row(guid="g1", docno="D-KEEP", acthguid="T1", date="2026-01-01", title="파트너 미팅"),
            _row(guid="g2", docno="D-OTHER", acthguid="T2", date="2026-01-02", title="다른 글"),
        ],
        keyman_limit=0,
    )
    with lw.psycopg.connect(_test_dsn()) as connection:
        connection.autocommit = False
        lw.persist_analysis_payload(connection, first)
        lw.persist_analysis_payload(connection, limited)
        lw.persist_analysis_payload(connection, rebuilt)
        rows = lw._database_query(
            connection,
            f"SELECT keyman_source, keyman_our_side, keyman_counterpart_side FROM {lw.ANALYSIS_DOCUMENT_TABLE} WHERE document_no = %s",
            ("D-KEEP",),
        )
        connection.rollback()
    assert rows[0]["keyman_source"] == "llm"
    our = rows[0]["keyman_our_side"]
    counterpart = rows[0]["keyman_counterpart_side"]
    if isinstance(our, str):
        our = json.loads(our)
    if isinstance(counterpart, str):
        counterpart = json.loads(counterpart)
    assert our[0]["person_name"] == "Fixture analyst"
    assert counterpart[0]["person_name"] == "Fixture partner"


def test_limited_persist_does_not_truncate_existing_documents() -> None:
    """A --limit persist must upsert the subset without wiping the live snapshot."""
    first = lw.build_payload(
        [_row(guid="g1", docno="D-KEEP", acthguid="T1", date="2026-01-01", title="파트너 미팅")],
        keyman_transport=_keyman_fixture_transport,
        keyman_limit=1,
    )
    limited = lw.build_payload(
        [_row(guid="g2", docno="D-OTHER", acthguid="T2", date="2026-01-02", title="다른 글")],
        keyman_limit=0,
    )
    with lw.psycopg.connect(_test_dsn()) as connection:
        connection.autocommit = False
        lw.persist_analysis_payload(connection, first)
        lw.persist_analysis_payload(connection, limited, replace_missing=False)
        kept = lw._database_query(
            connection,
            f"SELECT keyman_source, keyman_our_side, keyman_counterpart_side FROM {lw.ANALYSIS_DOCUMENT_TABLE} WHERE document_no = %s",
            ("D-KEEP",),
        )
        extra = lw._database_query(
            connection,
            f"SELECT document_no FROM {lw.ANALYSIS_DOCUMENT_TABLE} WHERE document_no = %s",
            ("D-OTHER",),
        )
        total = lw._database_query(
            connection,
            f"SELECT count(*) AS n FROM {lw.ANALYSIS_DOCUMENT_TABLE}",
        )
        connection.rollback()
    assert kept[0]["keyman_source"] == "llm"
    our = kept[0]["keyman_our_side"]
    counterpart = kept[0]["keyman_counterpart_side"]
    if isinstance(our, str):
        our = json.loads(our)
    if isinstance(counterpart, str):
        counterpart = json.loads(counterpart)
    assert our[0]["person_name"] == "Fixture analyst"
    assert counterpart[0]["person_name"] == "Fixture partner"
    assert extra[0]["document_no"] == "D-OTHER"
    assert int(total[0]["n"]) == 2


def test_persist_keeps_predicted_entity_role_affinity_on_rebuild() -> None:
    """CLI persist must keep popup-written predicted relatedness across rebuilds."""
    first = lw.build_payload(
        [
            _row(guid="g1", docno="D-PRED-1", acthguid="T-A", date="2026-01-01", title="파트너 미팅"),
            _row(guid="g2", docno="D-PRED-2", acthguid="T-B", date="2026-01-02", title="파트너 미팅"),
        ],
        keyman_limit=0,
    )
    rebuilt = lw.build_payload(
        [
            _row(guid="g1", docno="D-PRED-1", acthguid="T-A", date="2026-01-01", title="파트너 미팅"),
            _row(guid="g2", docno="D-PRED-2", acthguid="T-B", date="2026-01-02", title="파트너 미팅"),
        ],
        keyman_limit=0,
    )
    predicted = lw._predicted_entity_role_edges(
        {"id": "doc:D-PRED-1", "acthguid": "T-A", "entity_role": "파트너"},
        [{"id": "doc:D-PRED-2", "acthguid": "T-B", "entity_role": "파트너"}],
    )
    assert predicted
    assert not any(edge.get("relation") == "entity_role_affinity" for edge in rebuilt.get("edges") or [])
    with lw.psycopg.connect(_test_dsn()) as connection:
        connection.autocommit = False
        lw.persist_analysis_payload(connection, first)
        assert lw.persist_lineage_relatedness_edges(connection, predicted) >= 1
        lw.persist_analysis_payload(connection, rebuilt)
        rows = lw._database_query(
            connection,
            f"""
            SELECT source_node, target_node, relation_name, evidence_status
            FROM {lw.ANALYSIS_EDGE_TABLE}
            WHERE relation_name = %s
            """,
            ("entity_role_affinity",),
        )
        connection.rollback()
    assert rows
    assert all(row["evidence_status"] == lw.EVIDENCE_PREDICTED for row in rows)
    assert all(row["relation_name"] not in lw.TRANSITION_RELATIONS for row in rows)


def test_editor_can_publish_and_persist_visibility() -> None:
    editor = {"account_id": "acct-editor", "corp_code": "CWL1", "pu_code": "PU01", "roles": ["editor"]}
    resource = {"document_no": "D1", "corp_code": "CWL1", "owner_pu": "PU01", "visibility": lw.VISIBILITY_PUBLIC}
    updated = lw.apply_visibility(resource, lw.VISIBILITY_PRIVATE, editor)
    assert updated["visibility"] == lw.VISIBILITY_PRIVATE
    payload = lw.build_payload(
        [_row(guid="g1", docno="D1", acthguid="T1", date="2026-01-01", title="파트너 미팅")],
        keyman_transport=_keyman_fixture_transport,
    )
    with lw.psycopg.connect(_test_dsn()) as connection:
        connection.autocommit = False
        lw.persist_analysis_payload(connection, payload)
        lw.persist_visibility(connection, "D1", lw.VISIBILITY_PRIVATE, "acct-editor")
        rows = lw._database_query(
            connection,
            f"SELECT visibility_code FROM {lw.ANALYSIS_DOCUMENT_TABLE} WHERE document_no = %s",
            ("D1",),
        )
        overrides = lw._database_query(
            connection,
            f"SELECT visibility_code, updated_by FROM {lw.ANALYSIS_OVERRIDE_TABLE} WHERE document_no = %s",
            ("D1",),
        )
        connection.rollback()
    assert rows[0]["visibility_code"] == lw.VISIBILITY_PRIVATE
    assert overrides[0]["updated_by"] == "acct-editor"


def test_keyman_knowledge_graph_links_group_corp_and_pu() -> None:
    rows = [
        _row(guid="a1", docno="A1", acthguid="T1", date="2026-01-01", title="파트너 미팅"),
        _row(guid="a2", docno="A1", acthguid="T1", date="2026-01-02", title="파트너 미팅"),
    ]
    rows[0]["bukrs_field"] = "CWL1"
    rows[0]["pucode_field"] = "PU01"
    rows[0]["ernam_field"] = "alice"
    rows[0]["aenam_field"] = "alice"
    rows[0]["userid_field"] = "alice"
    rows[1]["bukrs_field"] = "CWL1"
    rows[1]["pucode_field"] = "PU02"
    rows[1]["ernam_field"] = "bob"
    rows[1]["aenam_field"] = "bob"
    rows[1]["userid_field"] = "bob"
    payload = lw.build_payload(rows, keyman_transport=_keyman_fixture_transport, keyman_limit=2)
    graph = payload["knowledge_graph"]
    relations = {edge["relation"] for edge in graph["edges"]}
    assert "cross_pu_transaction" in relations
    neighborhood = lw.related_keyman_graph(graph, "alice")
    assert neighborhood["nodes"]
    assert any(node.get("type") == "person" for node in neighborhood["nodes"])


def test_keyman_knowledge_graph_links_cross_corp_and_same_pu() -> None:
    rows = [
        _row(guid="c1", docno="C1", acthguid="T2", date="2026-01-01", title="그룹 거래"),
        _row(guid="c2", docno="C1", acthguid="T2", date="2026-01-02", title="그룹 거래"),
        _row(guid="c3", docno="C1", acthguid="T2", date="2026-01-03", title="그룹 거래"),
    ]
    for index, (corp, pu, actor) in enumerate(
        [("CWL1", "PU01", "alice"), ("CWL1", "PU02", "bob"), ("DEMO", "PU02", "charlie")]
    ):
        rows[index].update(
            {
                "bukrs_field": corp,
                "pucode_field": pu,
                "ernam_field": actor,
                "aenam_field": actor,
                "userid_field": actor,
            }
        )
    graph = lw.build_payload(rows)["knowledge_graph"]
    relations = {edge["relation"] for edge in graph["edges"]}
    assert "cross_pu_transaction" in relations
    assert "cross_corp_same_pu_transaction" in relations
    assert "cross_corp_transaction" in relations
    assert "cross_pu_thread" in relations
    assert "cross_corp_same_pu_thread" in relations


def test_knowledge_graph_filter_does_not_leak_hidden_documents() -> None:
    payload = lw.build_payload(
        [
            _row(guid="visible", docno="VISIBLE", acthguid="TV", date="2026-01-01"),
            {
                **_row(guid="hidden", docno="HIDDEN", acthguid="TH", date="2026-01-02"),
                "bukrs_field": "DEMO",
                "pucode_field": "PU10",
            },
        ]
    )
    filtered = lw.filter_payload_for_actor(
        payload, {"corp_code": "CWL1", "pu_code": "PU01", "roles": ["reader"]}
    )
    graph_document_ids = {
        node["id"] for node in filtered["knowledge_graph"]["nodes"] if node.get("type") == "document"
    }
    assert "kg:document:VISIBLE" in graph_document_ids
    assert "kg:document:HIDDEN" not in graph_document_ids
    assert all(
        "HIDDEN" not in {str(value) for value in node.get("document_nos") or []}
        for node in filtered["knowledge_graph"]["nodes"]
    )


def test_knowledge_neighborhood_uses_node_specific_depths() -> None:
    graph = {
        "nodes": [
            {"id": "doc", "type": "document", "label": "doc", "kg_depth": 3},
            {"id": "person", "type": "person", "label": "person", "kg_depth": 3},
            {"id": "org", "type": "organization", "label": "org", "kg_depth": 1},
            {"id": "pu", "type": "pu", "label": "pu", "kg_depth": 1},
        ],
        "edges": [
            {"source": "doc", "target": "person", "relation": "document_person"},
            {"source": "person", "target": "org", "relation": "member_of"},
            {"source": "org", "target": "pu", "relation": "org_pu"},
        ],
    }
    adaptive = lw.knowledge_neighborhood(graph, {"doc"})
    assert {node["id"] for node in adaptive["nodes"]} == {"doc", "person", "org"}
    by_name = lw.related_keyman_graph(graph, "person")
    assert any(node["id"] == "person" for node in by_name["nodes"])
    synthesized = lw.build_knowledge_graph(
        [
            {
                "type": "document",
                "document_no": "D-KG",
                "title_sample": "OMEXOM Meeting",
                "corp_code": "CWL1",
                "owner_pu": "PU01",
                "keyman_our_side": [{"person_name": "Mark Hill", "org_name": "OMEXOM"}],
                "keyman_counterpart_side": [{"person_name": "Mark Hill", "org_name": "SPEN"}],
            }
        ],
        [],
    )
    named = lw.related_keyman_graph(synthesized, "Mark Hill")
    assert any(node.get("type") == "person" and "Mark Hill" in str(node.get("label")) for node in named["nodes"])
    assert any(node.get("type") == "organization" for node in named["nodes"])
    assert adaptive["depths"]["org"] == 2
    capped = lw.knowledge_neighborhood(graph, {"doc"}, depth=1)
    assert {node["id"] for node in capped["nodes"]} == {"doc", "person"}


def test_knowledge_neighborhood_depths_serialize_as_json_object() -> None:
    """HTTP KG responses must not carry tuple keys in the depths map."""
    graph = {
        "nodes": [
            {"id": "doc", "type": "document", "label": "doc", "kg_depth": 3},
            {"id": ("person", "alice"), "type": "person", "label": "alice", "kg_depth": 3},
        ],
        "edges": [{"source": "doc", "target": ("person", "alice"), "relation": "mentions"}],
    }
    result = lw.knowledge_neighborhood(graph, {"doc", ("person", "alice")})
    encoded = json.dumps(result)
    parsed = json.loads(encoded)
    assert parsed["depths"]
    assert all(isinstance(key, str) for key in parsed["depths"])
    assert any(key.endswith("alice") for key in parsed["depths"])
    encoded_http = server._json_bytes({("same", "corp"): 1, "depths": result["depths"]})
    assert json.loads(encoded_http.decode("utf-8"))["same:corp"] == 1


def test_persisted_keyman_neighborhood_walks_people_orgs_events_and_posts() -> None:
    """Keyman click must walk the precomputed KG, not the single-document VOC snippet."""
    nodes = [
        {"id": "test-kg:doc-a", "type": "document", "label": "Doc A", "document_no": "D-A", "corp_code": "CWL1", "owner_pu": "PU01", "kg_depth": 3},
        {"id": "test-kg:doc-b", "type": "document", "label": "Doc B", "document_no": "D-B", "corp_code": "CWL1", "owner_pu": "PU02", "kg_depth": 3},
        {"id": "test-kg:doc-c", "type": "document", "label": "Doc C", "document_no": "D-C", "corp_code": "CWL2", "owner_pu": "PU01", "kg_depth": 3},
        {"id": "test-kg:alice", "type": "person", "label": "Alice Keyman", "document_no": "D-A", "corp_code": "CWL1", "owner_pu": "PU01", "kg_depth": 3},
        {"id": "test-kg:bob", "type": "person", "label": "Bob OtherPU", "document_no": "D-B", "corp_code": "CWL1", "owner_pu": "PU02", "kg_depth": 3},
        {"id": "test-kg:carol", "type": "person", "label": "Carol CrossCorp", "document_no": "D-C", "corp_code": "CWL2", "owner_pu": "PU01", "kg_depth": 3},
        {"id": "test-kg:org", "type": "organization", "label": "Group Co", "kg_depth": 2},
        {"id": "test-kg:event", "type": "event", "label": "VOC kickoff", "document_no": "D-A", "kg_depth": 2},
    ]
    edges = [
        {"source": "test-kg:doc-a", "target": "test-kg:alice", "relation": "keyman_our_side"},
        {"source": "test-kg:alice", "target": "test-kg:org", "relation": "member_of"},
        {"source": "test-kg:alice", "target": "test-kg:event", "relation": "person_event"},
        {"source": "test-kg:alice", "target": "test-kg:bob", "relation": "same_corp_other_pu"},
        {"source": "test-kg:alice", "target": "test-kg:carol", "relation": "cross_corp"},
        {"source": "test-kg:bob", "target": "test-kg:doc-b", "relation": "keyman_our_side"},
        {"source": "test-kg:carol", "target": "test-kg:doc-c", "relation": "keyman_counterpart"},
    ]
    with lw.psycopg.connect(_test_dsn()) as connection:
        connection.autocommit = False
        lw.persist_knowledge_graph_snapshot(connection, {"nodes": [], "edges": []})
        with connection.cursor() as cursor:
            cursor.executemany(
                f"""
                INSERT INTO {lw.ANALYSIS_KG_NODE_TABLE}
                    (node_id, node_type, label, document_no, metadata_payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    (
                        node["id"],
                        node["type"],
                        node["label"],
                        node.get("document_no"),
                        Json({key: value for key, value in node.items() if key not in {"id", "type", "label", "document_no"}}),
                    )
                    for node in nodes
                ],
            )
            cursor.executemany(
                f"""
                INSERT INTO {lw.ANALYSIS_KG_EDGE_TABLE}
                    (source_node, target_node, relation_name, evidence_id)
                VALUES (%s, %s, %s, %s)
                """,
                [(edge["source"], edge["target"], edge["relation"], None) for edge in edges],
            )
        neighborhood = lw.load_persisted_keyman_neighborhood(connection, "Alice Keyman")
        connection.rollback()
    types = {node.get("type") for node in neighborhood["nodes"]}
    labels = {str(node.get("label")) for node in neighborhood["nodes"]}
    assert types >= {"person", "organization", "event", "document"}
    assert {"Alice Keyman", "Bob OtherPU", "Carol CrossCorp", "Group Co", "VOC kickoff", "Doc A"} <= labels
    assert neighborhood["person_name"] == "Alice Keyman"
    assert any(node.get("owner_pu") == "PU02" or node.get("label") == "Bob OtherPU" for node in neighborhood["nodes"])
    assert any(node.get("corp_code") == "CWL2" or node.get("label") == "Carol CrossCorp" for node in neighborhood["nodes"])
    assert neighborhood["depths"]
    react = Path("web/src/App.jsx").read_text(encoding="utf-8")
    assert 'className="keyman-link"' in react
    assert "person=${encodeURIComponent(personName)}" in react


def test_kg_snapshot_advisory_lock_serializes_writers() -> None:
    """A second direct-PostgreSQL writer cannot enter the same KG replacement."""
    with lw.psycopg.connect(_test_dsn()) as first, lw.psycopg.connect(_test_dsn()) as second:
        first.autocommit = False
        second.autocommit = False
        lw._lock_knowledge_graph_snapshot(first)
        with second.cursor() as cursor:
            cursor.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                (lw.KNOWLEDGE_GRAPH_SNAPSHOT_LOCK_NAME,),
            )
            assert cursor.fetchone()[0] is False
        first.rollback()
        second.rollback()


def test_react_opens_popup_even_if_content_route_fails() -> None:
    react = Path("web/src/App.jsx").read_text(encoding="utf-8")
    assert "api(`/api/documents/${encodeURIComponent(selectedNo)}`)" in react
    assert "setContent({ document_no: selectedNo, assets: [], asset_count: 0, inspections: [] })" in react
    assert "Promise.all([\n      api(`/api/documents/${encodeURIComponent(selectedNo)}`)," not in react


def test_vite_dev_proxy_targets_product_api() -> None:
    config = Path("web/vite.config.js").read_text(encoding="utf-8")
    assert 'http://127.0.0.1:18082' in config
    assert 'http://127.0.0.1:8000' not in config


def test_compose_contract_has_no_identity_provider_or_model_answer() -> None:
    compose = Path("compose/http_standin.py").read_text(encoding="utf-8")
    compose_config = Path("compose.yaml").read_text(encoding="utf-8")
    assert "demo-pass" not in compose
    assert "analyst@" not in compose
    assert "issue_session" not in compose
    assert "KEYVERSE_STANDIN" not in compose
    assert "keyverse_oidc" not in compose
    assert "live_model_gateway_required" in compose
    assert "local-event-narrator" not in compose
    assert 'task == "content_inspection"' in compose
    assert "create_unverified_context" not in compose
    assert "LINEAGEWEAVE_SEARXNG_URL: ${LINEAGEWEAVE_SEARXNG_URL:-http://searxng:8080}" in compose_config
    assert "LINEAGEWEAVE_PRODUCT_LLM_TIMEOUT: ${LINEAGEWEAVE_PRODUCT_LLM_TIMEOUT:-120}" in compose_config
    assert "LINEAGEWEAVE_REPORT_JUDGE_TIMEOUT: ${LINEAGEWEAVE_REPORT_JUDGE_TIMEOUT:-15}" in compose_config
    assert "LINEAGEWEAVE_REPORT_REFRESH_MAX_SLICES: ${LINEAGEWEAVE_REPORT_REFRESH_MAX_SLICES:-3}" in compose_config
    assert "LINEAGEWEAVE_REPORT_REFRESH_MAX_ATTEMPTS: ${LINEAGEWEAVE_REPORT_REFRESH_MAX_ATTEMPTS:-1}" in compose_config
    assert "SEARXNG_CA_BUNDLE: ${SEARXNG_CA_BUNDLE:-}" in compose_config
    assert "build: ./compose/searxng" in compose_config
    searxng_image = Path("compose/searxng/Dockerfile").read_text(encoding="utf-8")
    assert "FROM searxng/searxng@sha256:" in searxng_image
    searxng_entrypoint = Path("compose/searxng/entrypoint.sh").read_text(encoding="utf-8")
    assert "export SEARXNG_SECRET=" in searxng_entrypoint
    searxng = Path("compose/searxng/settings.yml").read_text(encoding="utf-8")
    assert "- json" in searxng
    assert "keep_only:" in searxng and "- bing" in searxng
    assert "path: ${LINEAGEWEAVE_ENV_FILE:-${HOME}/.env}" in compose_config
    assert "required: false" in compose_config
    assert "valkey_data:/data" in compose_config


def test_compose_content_inspection_forwards_to_live_gateway(monkeypatch) -> None:
    import importlib

    module = importlib.reload(importlib.import_module("compose.http_standin"))
    captured: dict = {}

    def fake_post(path: str, payload: dict):
        captured[path] = payload
        if path == "/api/v1/content_inspection":
            return None
        return {
            "choices": [{"message": {"content": json.dumps({"ocr_text": "fixture text", "object_labels": []})}}],
            "model": "fixture-vision",
        }

    monkeypatch.setattr(module, "_gateway", lambda: ("https://gateway.example", "token", "fixture-vision"))
    monkeypatch.setattr(module, "_post_gateway", fake_post)
    result = module._forward_task(
        {
            "task": "content_inspection",
            "mime_type": "image/png",
            "image_data_uri": "data:image/png;base64,Zm9v",
        }
    )
    assert result["ocr_text"] == "fixture text"
    message = captured["/v1/chat/completions"]["messages"][1]["content"]
    assert message[1]["image_url"]["url"].startswith("data:image/png")
    assert "image_data_uri" not in message[0]["text"]


def test_resolve_keyman_transport_is_live_gateway_only(monkeypatch) -> None:
    monkeypatch.setattr(lw, "load_runtime_env", lambda path=None: None)
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://gateway.example")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "token")
    transport, mode = lw.resolve_keyman_transport()
    assert mode == "live_http"
    assert transport.__name__ == "live_keyman_http_transport"


def test_event_queue_uses_valkey_stream_and_transactional_outbox_name() -> None:
    assert lw.VALKEY_EVENT_STREAM == "lineageweave_events"
    assert lw.ANALYSIS_EVENT_OUTBOX_TABLE == "analysis_event_outbox"
    assert lw.DEFAULT_VALKEY_URL.startswith("redis://")


def test_apply_visibility_denied_for_reader() -> None:
    resource = {"corp_code": "CWL1", "owner_pu": "PU01", "visibility": lw.VISIBILITY_PUBLIC}
    reader = {"corp_code": "CWL1", "pu_code": "PU01", "roles": ["reader"]}
    with pytest.raises(PermissionError):
        lw.apply_visibility(resource, lw.VISIBILITY_PRIVATE, reader)


def _png_asset() -> dict:
    return {
        "asset_index": 0,
        "source_position": 12,
        "row_guid": "fixture-guid",
        "source_row_number": "7",
        "mime_type": "image/png",
        "data_uri": (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL5JwAAAABJRU5ErkJggg=="
        ),
    }


def test_content_inspection_validates_raster_bytes_and_normalizes_labels(monkeypatch) -> None:
    asset = _png_asset()
    prepared = lw.prepare_content_inspection_asset(asset)
    assert prepared["asset_sha256"] == lw.content_asset_sha256(asset)
    assert prepared["mime_type"] == "image/png"
    result = lw.derive_content_inspection_via_llm(
        asset,
        transport=lambda body: {
            "ocr_text": "  도면 번호 17  ",
            "object_labels": [
                {"label": "diagram", "description": "process diagram"},
                {"label": "Diagram", "description": "duplicate"},
                {"name": "table", "detail": "small data table"},
            ],
            "model": "fixture-vision",
        },
    )
    assert result["ocr_text"] == "도면 번호 17"
    assert result["object_labels"] == [
        {"label": "diagram", "description": "process diagram"},
        {"label": "table", "description": "small data table"},
    ]
    monkeypatch.setattr(lw, "MAX_VISION_REQUEST_BYTES", 1)
    with pytest.raises(ValueError, match="exceeds"):
        lw.prepare_content_inspection_asset(asset)
    with pytest.raises(ValueError, match="unsupported"):
        lw.prepare_content_inspection_asset({**asset, "mime_type": "image/svg+xml"})


def test_content_inspection_http_uses_verified_tls_and_multimodal_shape(monkeypatch) -> None:
    captured: list[dict] = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "model": "fixture-vision",
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"ocr_text": "fixture OCR", "object_labels": [{"label": "chart"}]}
                                )
                            }
                        }
                    ],
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout=None, context=None, **kwargs):
        assert context is not None
        assert context.verify_mode == lw.ssl.CERT_REQUIRED
        assert context.check_hostname is True
        captured.append({"url": request.full_url, "payload": json.loads(request.data.decode("utf-8"))})
        if request.full_url.endswith("/api/v1/content_inspection"):
            raise lw.urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
        return Response()

    monkeypatch.setattr(lw.urllib.request, "urlopen", fake_urlopen)
    response = lw.post_content_inspection_http(
        {
            "task": "content_inspection",
            "mime_type": "image/png",
            "image_data_uri": _png_asset()["data_uri"],
        },
        base_url="https://gateway.example",
        token="fixture-token",
        model="fixture-vision",
    )
    assert response["ocr_text"] == "fixture OCR"
    assert captured[-1]["url"].endswith("/v1/chat/completions")
    content = captured[-1]["payload"]["messages"][1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/png")
    assert "image_data_uri" not in content[0]["text"]


def test_content_inspection_persists_normalized_labels_in_postgres() -> None:
    payload = lw.build_payload(
        [_row(guid="g-inspection", docno="D-INSPECTION", acthguid="T1", date="2026-01-01")]
    )
    asset = _png_asset()
    inspection = lw.derive_content_inspection_via_llm(
        asset,
        transport=lambda _body: {
            "ocr_text": "fixture OCR",
            "object_labels": [{"label": "diagram", "description": "fixture diagram"}],
            "model": "fixture-vision",
        },
    )
    with lw.psycopg.connect(_test_dsn()) as connection:
        lw.persist_analysis_payload(connection, payload)
        lw.persist_content_inspection(connection, "D-INSPECTION", asset, inspection, "acct-fixture")
        rows = lw._database_query(
            connection,
            f"SELECT ocr_text, asset_sha256 FROM {lw.ANALYSIS_INSPECTION_TABLE} WHERE document_no = %s",
            ("D-INSPECTION",),
        )
        labels = lw._database_query(
            connection,
            f"""
            SELECT catalog.label_name, link.label_description
            FROM {lw.ANALYSIS_INSPECTION_LABEL_TABLE} AS link
            JOIN {lw.ANALYSIS_OBJECT_LABEL_TABLE} AS catalog ON catalog.label_name = link.label_name
            WHERE link.document_no = %s
            """,
            ("D-INSPECTION",),
        )
        connection.rollback()
    assert rows == [{"ocr_text": "fixture OCR", "asset_sha256": inspection["asset_sha256"]}]
    assert labels == [{"label_name": "diagram", "label_description": "fixture diagram"}]


def test_content_inspection_keeps_label_descriptions_per_asset_relation() -> None:
    payload = lw.build_payload(
        [_row(guid="g-inspection-2", docno="D-INSPECTION-2", acthguid="T1", date="2026-01-01")]
    )
    first_asset = _png_asset()
    second_asset = {**_png_asset(), "asset_index": 1, "source_position": 24}
    first = lw.derive_content_inspection_via_llm(
        first_asset,
        transport=lambda _body: {"object_labels": [{"label": "diagram", "description": "first view"}]},
    )
    second = lw.derive_content_inspection_via_llm(
        second_asset,
        transport=lambda _body: {"object_labels": [{"label": "diagram", "description": "second view"}]},
    )
    with lw.psycopg.connect(_test_dsn()) as connection:
        lw.persist_analysis_payload(connection, payload)
        lw.persist_content_inspection(connection, "D-INSPECTION-2", first_asset, first, "acct-fixture")
        lw.persist_content_inspection(connection, "D-INSPECTION-2", second_asset, second, "acct-fixture")
        labels = lw._database_query(
            connection,
            f"""
            SELECT asset_index, label_description
            FROM {lw.ANALYSIS_INSPECTION_LABEL_TABLE}
            WHERE document_no = %s AND label_name = %s
            ORDER BY asset_index
            """,
            ("D-INSPECTION-2", "diagram"),
        )
        connection.rollback()
    assert labels == [
        {"asset_index": 0, "label_description": "first view"},
        {"asset_index": 1, "label_description": "second view"},
    ]


def test_content_inspection_requires_author_role_and_react_routes() -> None:
    resource = {"corp_code": "CWL1", "owner_pu": "PU01", "visibility": lw.VISIBILITY_PUBLIC}
    reader = {"corp_code": "CWL1", "pu_code": "PU01", "roles": ["reader"]}
    author = {"corp_code": "CWL1", "pu_code": "PU01", "roles": ["author"]}
    assert not lw.authorize_access(actor=reader, resource=resource, action="manage_content_inspections")["allowed"]
    assert lw.authorize_access(actor=author, resource=resource, action="manage_content_inspections")["allowed"]
    react = Path("web/src/App.jsx").read_text(encoding="utf-8")
    assert "/assets/${asset.asset_index}/inspect" in react
    assert "/api/images/search" in react
    assert "OCR·객체 분석" in react
    assert 'role="region" aria-label="이미지 검색 결과"' in react
    assert 'aria-label="글 자체의 Lineage 질문"' in react
    assert 'aria-label="게시글 공개 범위"' in react
    assert "</strong>에서 <strong>" in react


def test_issue_maps_to_todo_and_calendar_with_llm_content() -> None:
    ticket = {"ticket_id": "tkt-D1", "title": "고객 이슈 후속", "status": "open"}
    document = {"document_no": "D1", "title_sample": "고객 이슈 후속", "korean_summary": "고객의 확인이 필요합니다."}
    mapped = lw.derive_issue_work_items_via_llm(
        ticket,
        document,
        transport=lambda body: {
            "task": body["task"],
            "todo_body": "견적 회신 초안 작성",
            "calendar_body": "고객 점검 일정",
            "due_on": "2026-04-20",
        },
    )
    assert mapped["request"]["task"] == "issue_work_items"
    assert mapped["request"]["korean_summary"] == "고객의 확인이 필요합니다."
    assert mapped["todo"]["source"] == "llm"
    assert mapped["todo"]["body"] == "견적 회신 초안 작성"
    assert mapped["calendar"]["source"] == "llm"
    assert mapped["calendar"]["occurred_on"] == "2026-04-20"
    assert mapped["calendar"]["body"] == "고객 점검 일정"
    from_envelope = lw.parse_issue_work_content(
        {
            "choices": [
                {"message": {"content": '{"todo_body":"견적 회신","calendar_body":"방문 일정"}'}}
            ]
        }
    )
    assert from_envelope["todo_body"] == "견적 회신"
    assert "due_on" not in from_envelope
    assert "due_on" not in lw.parse_issue_work_content(
        {"todo_body": "견적 회신", "calendar_body": "고객 점검", "due_on": "다음 주"}
    )
    unscheduled = lw.map_issue_to_work_items(
        ticket,
        document,
        content={"todo_body": "견적 회신 초안 작성", "calendar_body": "고객 점검 일정"},
    )
    assert unscheduled["todo"]["source"] == "llm"
    assert unscheduled["calendar"]["occurred_on"] is None
    assert lw._normalize_issue_due_date("2026/04/20") == "2026-04-20"
    assert lw._normalize_issue_due_date("2026-02-30") == ""
    assert lw._normalize_issue_due_date("다음 주") == ""
    document = {
        "document_no": "D1",
        "title_sample": "고객 이슈 후속",
        "issue_tickets": [ticket],
        "todo_items": [{"todo_id": "todo-tkt-D1", "source": "pending_llm", "body": "고객 이슈 후속 후속 조치"}],
        "calendar_items": [{"calendar_id": "cal-tkt-D1", "source": "pending_llm", "body": "고객 이슈 후속"}],
    }
    enriched = lw.enrich_pending_document_work(
        document,
        transport=lambda body: {
            "todo_body": "견적 회신 초안 작성",
            "calendar_body": "고객 점검 일정",
            "due_on": "2026-04-20",
        },
    )
    assert enriched["todo_items"][0]["source"] == "llm"
    assert enriched["todo_items"][0]["body"] == "견적 회신 초안 작성"
    assert enriched["calendar_items"][0]["source"] == "llm"


def test_appointment_extract_returns_dated_promise() -> None:
    body = "고객 방문 약속 2026-04-15 14:00 본사 회의"
    extracted = lw.extract_appointments(body)
    assert extracted
    assert extracted[0]["occurred_on"] == "2026-04-15"
    assert extracted[0]["label"] == "고객 약속"
    parsed = lw.parse_appointment_llm_response(
        {"appointments": [{"occurred_on": "2026-05-02", "excerpt": "킥오프 미팅"}]}
    )
    assert parsed[0]["occurred_on"] == "2026-05-02"
    assert parsed[0]["source"] == "llm"
    wrapped = lw.parse_appointment_llm_response(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"appointments": [{"occurred_on": "2026-05-03", "excerpt": "현장 미팅"}]}
                        )
                    }
                }
            ]
        }
    )
    assert wrapped[0]["occurred_on"] == "2026-05-03"
    assert wrapped[0]["source"] == "llm"


def test_appointment_extract_uses_document_number_date_for_meeting_title() -> None:
    """A meeting title without an in-text date still yields a dated 약속 on the popup path."""
    document = {
        "document_no": "260220-0010-01",
        "title_sample": "[SPEN] Mark Hill STATCOM  Tender Meeting",
        "korean_summary": "입찰 미팅 관찰 요약",
    }
    extracted = lw.extract_appointments(
        document["title_sample"], document_no=document["document_no"]
    )
    assert extracted[0]["occurred_on"] == "2026-02-20"
    assert extracted[0]["label"] == "고객 약속"
    assert "Meeting" in extracted[0]["excerpt"]
    assert lw.extract_appointments("status update", document_no="260220-0010-01") == []
    resolved = lw.resolve_document_appointments(document)
    assert resolved[0]["occurred_on"] == "2026-02-20"
    persisted = lw.resolve_document_appointments(
        document,
        persisted=[
            {
                "appointment_id": "apt-live",
                "occurred_on": "2026-02-21",
                "label": "고객 약속",
                "excerpt": "현장 방문",
                "content_source": "llm",
            }
        ],
    )
    assert persisted[0]["appointment_id"] == "apt-live"
    assert persisted[0]["source"] == "llm"


def test_customer_master_llm_tree_is_lineage_clue_not_transition() -> None:
    documents = [
        {
            "id": "doc:A",
            "type": "document",
            "document_no": "A",
            "title_sample": "Acme Korea Plant visit",
            "corp_code": "CWL1",
            "owner_pu": "PU01",
        },
        {
            "id": "doc:B",
            "type": "document",
            "document_no": "B",
            "title_sample": "Acme Group HQ review",
            "corp_code": "CWL1",
            "owner_pu": "PU02",
        },
    ]

    def transport(body: dict) -> dict:
        assert body["task"] == "customer_master"
        return {
            "accounts": [
                {"account_name": "Acme Group", "tier": "group"},
                {"account_name": "Acme Korea", "tier": "national", "parent_name": "Acme Group"},
                {"account_name": "Acme Korea Plant", "tier": "plant", "parent_name": "Acme Korea"},
            ]
        }

    master = lw.derive_customer_master_via_llm(documents, transport=transport)
    assert master["source"] == "llm"
    assert lw.affiliate_parent_child("Acme Group", "Acme Korea", master) is True
    stubs = lw.parse_customer_master_response(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "accounts": [
                                    {"account_name": "고객", "tier": "group"},
                                    {"account_name": "시장", "tier": "national"},
                                    {
                                        "account_name": "SPEN",
                                        "tier": "group",
                                        "document_nos": ["260220-0009-01"],
                                    },
                                    {
                                        "account_name": "SPEN UK",
                                        "tier": "national",
                                        "parent_name": "SPEN",
                                        "document_nos": ["260220-0009-01"],
                                    },
                                ],
                                "edges": [{"parent": "SPEN", "child": "SPEN UK"}],
                            }
                        )
                    }
                }
            ]
        }
    )
    assert {row["account_name"] for row in stubs["accounts"]} == {"SPEN", "SPEN UK"}
    assert stubs["parent_of"]["SPEN UK"] == "SPEN"
    assert lw.affiliate_parent_child("SPEN", "SPEN UK", stubs) is True
    prefix_tree = lw.parse_customer_master_response(
        {
            "accounts": [
                {"account_name": "Acme Group", "tier": "group"},
                {"account_name": "Acme Group Korea Plant", "tier": "plant"},
            ]
        }
    )
    assert prefix_tree["parent_of"]["Acme Group Korea"] == "Acme Group"
    assert prefix_tree["parent_of"]["Acme Group HQ"] == "Acme Group Korea"
    assert prefix_tree["parent_of"]["Acme Group Korea Plant"] == "Acme Group HQ"
    assert {row["tier"] for row in prefix_tree["accounts"]} >= {"group", "national", "hq", "plant"}
    shallow = {
        "accounts": [{"account_name": "Short Co", "tier": "group", "document_nos": ["B"]}],
        "edges": [{"parent": "Short Co", "child": "Short Plant", "relation": "customer_affiliate", "source": "llm"}],
        "parent_of": {"Short Plant": "Short Co"},
        "source": "llm",
    }
    tree = lw.merge_customer_master_into_tree(lw.build_org_unit_affiliate_tree(documents), master)
    tree = lw.merge_customer_master_into_tree(tree, shallow)
    assert any(edge.get("parent") == "Acme Group" and edge.get("child") == "Acme Korea" for edge in tree["edges"][:6])
    assert tree["edges"][0].get("source") == "llm" or tree["edges"][0].get("relation") == "customer_affiliate"
    first_parents = [edge.get("parent") for edge in tree["edges"][:3]]
    assert first_parents[:2] == ["Acme Group", "Acme Korea"] or "Acme Group" in first_parents
    inferred = lw._inferred_affiliate_edges(documents, tree)
    assert inferred
    assert all(edge["evidence_status"] == lw.EVIDENCE_INFERRED for edge in inferred)
    assert all(edge["relation"] not in lw.TRANSITION_RELATIONS for edge in inferred)


def test_parse_dichotomous_judge_unwraps_chat_completion_envelope() -> None:
    judged = lw.parse_dichotomous_judge(
        {
            "choices": [
                {"message": {"content": json.dumps({"verdict": "fail", "rationale": "일정 지연"})}}
            ],
            "model": "fixture-judge",
        }
    )
    assert judged["verdict"] == "fail"
    assert judged["source"] == "llm_judge"
    assert judged["metric"] == "ragas_discrete_metric"
    captured: list[dict] = []

    def judge(body: dict) -> dict:
        captured.append(body)
        if body["task"] == "report_judge":
            return {
                "task": body["task"],
                "choices": [{"message": {"content": '{"verdict":"pass","rationale":"납기 준수"}'}}],
                "item_scores": [{"item_id": "item-gm-pos-1", "response": 1}],
            }
        return {"item_scores": [{"item_id": "item-gm-neg-1", "response": 0}]}

    via_task = lw.derive_dichotomous_judge_via_llm(
        {
            "report_id": "rpt-1",
            "period_kind": "weekly",
            "slice_kind": "pu",
            "slice_key": "PU01",
            "title": "weekly pu PU01",
            "document_nos": ["D1"],
        },
        documents=[
            {
                "document_no": "D1",
                "title_sample": "고객 이슈 납기",
                "korean_summary": "납기를 지켰다",
                "entity_role": "고객",
            }
        ],
        transport=judge,
    )
    assert "item_scores" in lw.PRODUCT_LLM_SYSTEM_PROMPTS["report_judge"]
    assert "writings" in lw.PRODUCT_LLM_SYSTEM_PROMPTS["report_judge"]
    assert "item_scores" in lw.PRODUCT_LLM_SYSTEM_PROMPTS["report_item_scores"]
    assert via_task["request"]["task"] == "report_judge"
    assert via_task["request"]["orchestration"]["conductor_role"] == "verifier"
    assert via_task["request"]["report"]["body"]
    assert via_task["request"]["writings"][0]["title"] == "고객 이슈 납기"
    assert via_task["request"]["items"]
    assert via_task["verdict"] == "pass"
    assert via_task["item_responses"] == [{"item_id": "item-gm-pos-1", "response": 1}]


def test_period_reports_weekly_monthly_slices_and_judge() -> None:
    documents = [
        {
            "type": "document",
            "document_no": "D1",
            "owner_pu": "PU01",
            "acthguid": "PROJ-1",
            "title_sample": "고객 이슈 납기",
            "entity_role": "고객",
        }
    ]
    slices = lw.build_period_report_slices(documents, as_of=datetime(2026, 4, 15, tzinfo=timezone.utc))
    kinds = {(item["period_kind"], item["slice_kind"]) for item in slices}
    assert ("weekly", "pu") in kinds
    assert ("monthly", "pu") in kinds
    assert ("weekly", "team") in kinds
    assert ("monthly", "project") in kinds

    def judge(body: dict) -> dict:
        assert body["task"] == "report_judge"
        assert body["metric"] == "ragas_discrete_metric"
        assert body["writings"]
        assert "고객 이슈 납기" in body["report"]["body"]
        assert body["items"]
        return {
            "verdict": "pass",
            "rationale": "납기 준수 근거가 본문에 있다",
            "item_scores": [
                {"item_id": item["item_id"], "response": 0 if item["item_id"] == "item-gm-neg-1" else 1}
                for item in body["items"]
            ],
        }

    scored = lw.score_period_reports(slices, documents, judge_transport=judge)
    judged = [item for item in scored if item["judge"].get("verdict") in {"pass", "fail"}]
    assert len(judged) == len(scored)
    assert all(item["judge"]["source"] == "llm_judge" for item in judged)
    assert judged[0]["judge"]["source"] == "llm_judge"
    assert judged[0]["linked_scores"] == []
    assert judged[0]["linking_status"] == "unavailable"
    assert judged[0]["linking_source"] == "unavailable"
    # Title contains 이슈 tokens, but the judge scored the delay item as 0.
    delay_scores = [
        item
        for item in judged[0]["judge"]["item_responses"]
        if item["item_id"] == "item-gm-neg-1"
    ]
    assert delay_scores == [{"item_id": "item-gm-neg-1", "response": 0}]
    assert {item["factor_family"] for item in judged[0]["factor_definitions"]} == {
        "general_management",
        "industry",
        "sales_lead",
    }
    with pytest.raises(ValueError, match="recorded_judge_must_not_be_labeled_live"):
        lw.parse_dichotomous_judge({"verdict": "pass", "source": "recorded_same_path", "live": True})


def test_period_report_linking_keeps_temporal_observation_units_separate() -> None:
    """Do not calibrate identical PU labels across different report windows together."""
    documents = [
        {
            "type": "document",
            "document_no": "D-TIME",
            "owner_pu": "PU01",
            "title_sample": "시간축 검증",
            "entity_role": "고객",
        }
    ]
    slices = [
        {
            "report_id": "report-week",
            "period_kind": "weekly",
            "period_start": "2026-04-06",
            "period_end": "2026-04-12",
            "slice_kind": "pu",
            "slice_key": "PU01",
            "document_count": 1,
            "document_nos": ["D-TIME"],
            "title": "weekly pu PU01",
        },
        {
            "report_id": "report-month",
            "period_kind": "monthly",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "slice_kind": "pu",
            "slice_key": "PU01",
            "document_count": 1,
            "document_nos": ["D-TIME"],
            "title": "monthly pu PU01",
        },
    ]
    observed_groups: list[str] = []

    def judge(_body: dict) -> dict:
        return {
            "verdict": "pass",
            "item_scores": [
                {"item_id": item["item_id"], "response": 1}
                for item in lw.default_factor_items()
            ],
        }

    def connector(body: dict) -> dict:
        responses = body["payload"]["responses"]
        observed_groups.extend(sorted({str(row["person_or_group"]) for row in responses}))
        return {
            "linked_scores": [
                {
                    "person_or_group": group,
                    "factor_id": factor["factor_id"],
                    "theta": 0.25,
                    "standard_error": 0.5,
                    "linking_method": "fipc",
                    "calibration_source": "fast_mlsirm",
                }
                for group in sorted({str(row["person_or_group"]) for row in responses})
                for factor in lw.default_factor_definitions()
            ],
            "calibration_rows": [{
                "calibration_run_id": "cal-fixture",
                "item_id": lw.default_factor_items()[0]["item_id"],
                "factor_id": lw.default_factor_items()[0]["factor_id"],
                "discrimination": 1.1,
                "difficulty": 0.0,
                "report_count": 2,
            }],
            "longitudinal_state": {"status": "computed", "engine": "fixture"},
        }

    scored = lw.score_period_reports(
        slices,
        documents,
        judge_transport=judge,
        mlsirm_transport=connector,
    )
    assert observed_groups == ["report-month", "report-week"]
    assert all(report["linked_scores"] for report in scored)
    assert {
        score["report_id"]
        for report in scored
        for score in report["linked_scores"]
    } == {"report-week", "report-month"}
    assert all(report["longitudinal_state"]["engine"] == "fixture" for report in scored)


def test_fast_mlsirm_link_requires_package_produced_scores() -> None:
    items = lw.default_factor_items()
    responses = [
        {"item_id": item["item_id"], "person_or_group": "PU01", "response": 1}
        for item in items
    ]
    recorded = lw.try_fast_mlsirm_link(
        {"responses": responses, "items": items},
        transport=lambda body: {"responses": body["payload"]["responses"], "items": body["payload"]["items"]},
    )
    assert recorded == {
        "status": "unavailable",
        "reason": "fast_mlsirm_response_missing_linked_scores",
        "scores": [],
        "source": "unavailable",
    }
    recorded_with_state = lw.try_fast_mlsirm_link(
        {"responses": responses, "items": items},
        transport=lambda body: {
            "responses": body["payload"]["responses"],
            "items": body["payload"]["items"],
            "longitudinal_state": {"status": "computed"},
        },
    )
    assert recorded_with_state["status"] == "unavailable"
    assert "longitudinal_state" not in recorded_with_state
    connector_without_state = lw.try_fast_mlsirm_link(
        {"responses": responses, "items": items},
        transport=lambda _body: {
            "linked_scores": [{
                "person_or_group": "PU01",
                "factor_id": "gm-pos-delivery",
                "theta": 0.0,
                "standard_error": 1.0,
            }]
        },
    )
    assert "longitudinal_state" not in connector_without_state
    assert connector_without_state["status"] == "connector"
    assert connector_without_state["source"] == "fast_mlsirm"
    assert connector_without_state["scores"][0]["calibration_source"] == "fast_mlsirm"
    diagnostics_only = lw.try_fast_mlsirm_link(
        {"responses": responses, "items": items},
        transport=lambda _body: {"ok": True, "fipc_best": "two_parameter_logistic"},
    )
    assert diagnostics_only["status"] == "unavailable"
    assert diagnostics_only["source"] == "unavailable"
    assert diagnostics_only["scores"] == []
