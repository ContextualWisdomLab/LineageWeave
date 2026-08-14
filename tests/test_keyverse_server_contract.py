"""Exercise Keyverse OIDC and server runtime paths with verified-contract doubles."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse

import pytest

import lineageweave as lw
import lineageweave_server as server


def test_loopback_oidc_url_uses_localhost_not_ip() -> None:
    """Browser redirects use localhost while preserving the configured issuer path."""
    rewritten = server.loopback_oidc_url(
        "http://127.0.0.1:28080/realms/cwl/protocol/openid-connect/auth?state=abc"
    )
    parsed = urllib.parse.urlsplit(rewritten)
    assert parsed.hostname == "localhost"
    assert parsed.port == 28080
    assert urllib.parse.parse_qs(parsed.query)["state"] == ["abc"]
    assert server.loopback_oidc_url("https://identity.example/authorize") == "https://identity.example/authorize"


ACTOR = {"account_id": "account-1", "corp_code": "CORP_A", "pu_code": "PU_A", "roles": ["admin"]}
METADATA = {
    "issuer": "https://identity.example",
    "authorization_endpoint": "https://identity.example/authorize",
    "token_endpoint": "https://identity.example/token",
    "introspection_endpoint": "https://identity.example/introspect",
    "client_id": "lineage-client",
    "client_secret": "fixture-secret",
    "redirect_uri": "https://product.example/api/oidc/callback",
}


class _Response:
    """Provide a minimal JSON HTTP response context."""

    def __init__(self, value: dict[str, object]) -> None:
        self.value = value

    def __enter__(self) -> "_Response":
        """Enter the response context."""
        return self

    def __exit__(self, *_args: object) -> bool:
        """Do not hide transport failures."""
        return False

    def read(self) -> bytes:
        """Serialize the configured JSON response."""
        return json.dumps(self.value).encode("utf-8")


class _RawResponse:
    """Provide deterministic raw HTTP response bytes for admin API contracts."""

    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    def __enter__(self) -> "_RawResponse":
        """Enter the response context."""
        return self

    def __exit__(self, *_args: object) -> bool:
        """Do not hide transport failures."""
        return False

    def read(self) -> bytes:
        """Return the configured raw response."""
        return self.raw


class _Connection:
    """Support the direct database context-manager boundary in server methods."""

    def __enter__(self) -> "_Connection":
        """Enter the connection context."""
        return self

    def __exit__(self, *_args: object) -> bool:
        """Do not suppress direct database failures."""
        return False


class _Handler:
    """Expose only headers required by actor resolution."""

    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


def _application() -> server.LineageApplication:
    """Create a product application with a valid non-sensitive source identifier."""
    return server.LineageApplication("postgresql://fixture", "schema.table")


def _configure_keyverse(monkeypatch) -> None:
    """Install the minimum confidential-client configuration used by OIDC tests."""
    monkeypatch.setenv("KEYVERSE_ISSUER", METADATA["issuer"])
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_CLIENT_ID", METADATA["client_id"])
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_CLIENT_SECRET", METADATA["client_secret"])
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_REDIRECT_URI", METADATA["redirect_uri"])
    monkeypatch.delenv("LINEAGEWEAVE_DEV_MODE", raising=False)
    monkeypatch.delenv("LINEAGEWEAVE_COOKIE_SECURE", raising=False)


def test_keyverse_url_cookie_and_actor_guards(monkeypatch) -> None:
    """Reject insecure endpoint shapes while keeping the explicit local exception narrow."""
    assert json.loads(server._json_bytes({None: ("fixture",)})) == {"null": ["fixture"]}
    assert server._actor_from_value(["not-a-claim"]) is None
    assert server._actor_from_value({"attributes": "malformed"}) is None
    assert server._actor_from_value({"sub": "account-1", "org": "CORP_A", "workspace": "PU_A", "role": "member"})["roles"] == ["member"]
    assert server._actor_from_value({"attributes": {"corp_code": "CORP_A", "pu_code": "PU_A", "roles": ["reader"]}, "account_id": "account-1"})["pu_code"] == "PU_A"
    assert server._actor_from_value({"sub": "account-1", "org": "CORP_A"}) is None
    assert server._actor_from_value(
        {"sub": "account-1", "org": "CORP_A", "workspace": "PU_A", "roles": []}
    ) is None
    monkeypatch.setenv("LINEAGEWEAVE_SESSION_TTL_SECONDS", "not-an-int")
    assert server._session_ttl_seconds() == 3600
    monkeypatch.setenv("LINEAGEWEAVE_SESSION_TTL_SECONDS", "1")
    assert server._session_ttl_seconds() == 60
    assert server._cookie_value({"Cookie": "a=1; lw_session=ok"}, "lw_session") == "ok"
    assert "Secure" in server._cookie_header("lw_session", "ok", 10)
    _configure_keyverse(monkeypatch)
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_REDIRECT_URI", "{origin}/api/oidc/callback")
    monkeypatch.setenv("LINEAGEWEAVE_PUBLIC_ORIGIN", "https://app.example:18443")
    app = _application()
    rendered = app._keyverse_settings({"Host": "attacker.example", "X-Forwarded-Proto": "http"})
    assert rendered["redirect_uri"] == "https://app.example:18443/api/oidc/callback"
    monkeypatch.delenv("LINEAGEWEAVE_PUBLIC_ORIGIN")
    with pytest.raises(RuntimeError, match="must_be_https"):
        app._keyverse_settings({"Host": "app.example:18443", "X-Forwarded-Proto": "https"})
    with pytest.raises(RuntimeError, match="must_be_https"):
        server._https_url("http://identity.example", "KEYVERSE_ISSUER")
    with pytest.raises(RuntimeError, match="must_be_https"):
        server._https_url("https://user:pass@identity.example", "KEYVERSE_ISSUER")
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_COOKIE_SECURE", "0")
    assert server._https_url("http://localhost:8080", "KEYVERSE_ISSUER") == "http://localhost:8080"
    assert "Secure" not in server._cookie_header("lw_session", "ok", 10)
    assert server._transport_context("http://localhost:8080") is None


def test_keyverse_discovery_token_validation_and_callback(monkeypatch) -> None:
    """Run discovery, PKCE, token validation, and opaque session issuance as one RP contract."""
    _configure_keyverse(monkeypatch)
    app = _application()
    requests: list[object] = []

    def urlopen(request, **_kwargs):  # noqa: ANN001
        requests.append(request)
        return _Response({key: value for key, value in METADATA.items() if key.endswith("endpoint") or key == "issuer"})

    monkeypatch.setattr(server.urllib.request, "urlopen", urlopen)
    discovered = app._keyverse_metadata()
    assert discovered["issuer"] == METADATA["issuer"]
    assert app._keyverse_metadata() == discovered
    assert len(requests) == 1

    posted: list[object] = []
    monkeypatch.setattr(server.urllib.request, "urlopen", lambda request, **_kwargs: posted.append(request) or _Response({"active": True}))
    assert app._keyverse_form_post(discovered["introspection_endpoint"], {"token": "access"}, discovered, failure="failed") == {"active": True}
    assert posted[0].get_header("Authorization").startswith("Basic ")

    claims = {
        "active": True,
        "iss": METADATA["issuer"],
        "aud": [METADATA["client_id"]],
        "client_id": METADATA["client_id"],
        "exp": time.time() + 180,
        "sub": "account-1",
        "org": "CORP_A",
        "workspace": "PU_A",
        "role": ["member", "editor"],
    }
    monkeypatch.setattr(app, "_keyverse_form_post", lambda *_args, **_kwargs: claims)
    actor, expires_at = app._actor_from_keyverse_access_token("access", discovered)
    assert actor["roles"] == ["reader", "editor"]
    assert expires_at > time.time()
    bad_claims = {**claims, "aud": ["another-client"]}
    monkeypatch.setattr(app, "_keyverse_form_post", lambda *_args, **_kwargs: bad_claims)
    with pytest.raises(RuntimeError, match="token_invalid"):
        app._actor_from_keyverse_access_token("access", discovered)

    location, state = app.begin_keyverse_login(email_address="member@example.com")
    parsed = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
    assert parsed["code_challenge_method"] == ["S256"]
    assert parsed["login_hint"] == ["member@example.com"]
    assert parsed["state"] == [state]
    monkeypatch.setattr(
        app,
        "_keyverse_form_post",
        lambda endpoint, *_args, **_kwargs: {"token_type": "Bearer", "access_token": "access"} if endpoint == METADATA["token_endpoint"] else claims,
    )
    monkeypatch.setattr(app, "_actor_from_keyverse_access_token", lambda *_args: (ACTOR, time.time() + 120))
    session, returned_actor, ttl = app.complete_keyverse_login("code", state, state)
    assert returned_actor == ACTOR
    assert 0 < ttl <= 120
    assert app._sessions[session]["actor"] == ACTOR
    with pytest.raises(RuntimeError, match="callback_invalid"):
        app.complete_keyverse_login("code", state, state)


@pytest.mark.parametrize("missing_claim", ("org", "workspace"))
def test_keyverse_relying_party_failure_paths_fail_closed(
    monkeypatch, missing_claim: str
) -> None:
    """Reject discovery, token, callback, and development-state failures at the RP boundary."""
    _configure_keyverse(monkeypatch)
    app = _application()

    def unavailable(*_args, **_kwargs):  # noqa: ANN002,ANN003
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(server.urllib.request, "urlopen", unavailable)
    with pytest.raises(RuntimeError, match="keyverse_discovery_failed"):
        app._keyverse_metadata()
    monkeypatch.setattr(
        server.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response({
            "issuer": "https://other.example",
            "authorization_endpoint": METADATA["authorization_endpoint"],
            "token_endpoint": METADATA["token_endpoint"],
            "introspection_endpoint": METADATA["introspection_endpoint"],
        }),
    )
    with pytest.raises(RuntimeError, match="keyverse_discovery_invalid"):
        app._keyverse_metadata()
    monkeypatch.setattr(
        server.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                **METADATA,
                "authorization_endpoint": "http://identity.example/authorize",
            }
        ),
    )
    with pytest.raises(RuntimeError, match="keyverse_discovery_invalid"):
        app._keyverse_metadata()
    monkeypatch.setattr(
        server.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                **METADATA,
                "authorization_endpoint": "https://other.example/authorize",
            }
        ),
    )
    with pytest.raises(RuntimeError, match="keyverse_discovery_invalid"):
        app._keyverse_metadata()

    metadata = dict(METADATA)
    monkeypatch.setattr(server.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response([]))
    with pytest.raises(RuntimeError, match="form_failed"):
        app._keyverse_form_post(metadata["token_endpoint"], {"code": "fixture"}, metadata, failure="form_failed")
    monkeypatch.setattr(server.urllib.request, "urlopen", unavailable)
    with pytest.raises(RuntimeError, match="form_failed"):
        app._keyverse_form_post(metadata["token_endpoint"], {"code": "fixture"}, metadata, failure="form_failed")

    claims = {
        "active": True,
        "iss": METADATA["issuer"],
        "aud": [METADATA["client_id"]],
        "client_id": METADATA["client_id"],
        "exp": time.time() + 180,
        "sub": "account-1",
        "org": "CORP_A",
        "workspace": "PU_A",
        "role": "member",
    }
    for invalid in (
        {**claims, "active": False},
        {**claims, "iss": "https://other.example"},
        {**claims, "client_id": "other-client"},
        {**claims, "exp": "not-a-timestamp"},
        {**claims, "exp": time.time() - 1},
    ):
        monkeypatch.setattr(app, "_keyverse_form_post", lambda *_args, invalid=invalid, **_kwargs: invalid)
        with pytest.raises(RuntimeError, match="keyverse_token_invalid"):
            app._actor_from_keyverse_access_token("access", metadata)
    missing_dimension = {
        key: value for key, value in claims.items() if key != missing_claim
    }
    monkeypatch.setattr(
        app, "_keyverse_form_post", lambda *_args, **_kwargs: missing_dimension
    )
    with pytest.raises(RuntimeError, match="keyverse_claims_invalid"):
        app._actor_from_keyverse_access_token("access", metadata)
    alias_only_claims = {
        key: value for key, value in claims.items() if key not in {"org", "workspace"}
    }
    alias_only_claims.update({"corp_code": "CORP_A", "pu_code": "PU_A"})
    monkeypatch.setattr(
        app, "_keyverse_form_post", lambda *_args, **_kwargs: alias_only_claims
    )
    with pytest.raises(RuntimeError, match="keyverse_claims_invalid"):
        app._actor_from_keyverse_access_token("access", metadata)
    with pytest.raises(RuntimeError, match="keyverse_token_invalid"):
        app._actor_from_keyverse_access_token("x" * 16_385, metadata)

    monkeypatch.setattr(app, "_keyverse_metadata", lambda *_args, **_kwargs: metadata)
    app._keyverse_states = {
        str(index): {"expires_at": time.time() + 60}
        for index in range(server.MAX_KEYVERSE_PENDING_STATES)
    }
    with pytest.raises(RuntimeError, match="keyverse_login_capacity"):
        app.begin_keyverse_login(email_address="member@example.com")
    app._keyverse_states = {
        "state": {
            "code_verifier": "verifier",
            "issuer": metadata["issuer"],
            "client_id": metadata["client_id"],
            "redirect_uri": metadata["redirect_uri"],
            "expires_at": time.time() + 60,
        }
    }
    monkeypatch.setattr(app, "_keyverse_form_post", lambda *_args, **_kwargs: {"token_type": "mac", "access_token": "access"})
    with pytest.raises(RuntimeError, match="keyverse_token_exchange_failed"):
        app.complete_keyverse_login("code", "state", "state")
    with pytest.raises(RuntimeError, match="keyverse_callback_invalid"):
        app.complete_keyverse_login("code", "non-ascii-한", "state")

    app._keyverse_states = {
        "configuration-drift": {
            "code_verifier": "verifier",
            "issuer": metadata["issuer"],
            "client_id": metadata["client_id"],
            "redirect_uri": metadata["redirect_uri"],
            "expires_at": time.time() + 60,
        }
    }
    monkeypatch.setattr(
        app,
        "_keyverse_metadata",
        lambda *_args, **_kwargs: {**metadata, "redirect_uri": "https://product.example/changed-callback"},
    )
    with pytest.raises(RuntimeError, match="keyverse_callback_invalid"):
        app.complete_keyverse_login(
            "code", "configuration-drift", "configuration-drift"
        )

    app._keyverse_states = {
        "expired-token": {
            "code_verifier": "verifier",
            "issuer": metadata["issuer"],
            "client_id": metadata["client_id"],
            "redirect_uri": metadata["redirect_uri"],
            "expires_at": time.time() + 60,
        }
    }
    monkeypatch.setattr(app, "_keyverse_metadata", lambda *_args, **_kwargs: metadata)
    monkeypatch.setattr(
        app,
        "_keyverse_form_post",
        lambda *_args, **_kwargs: {"token_type": "Bearer", "access_token": "access"},
    )
    monkeypatch.setattr(app, "_actor_from_keyverse_access_token", lambda *_args: (ACTOR, time.time() - 1))
    with pytest.raises(RuntimeError, match="keyverse_token_invalid"):
        app.complete_keyverse_login("code", "expired-token", "expired-token")

    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", "not-json")
    assert app._development_actor() is None
    expected_actor = {**ACTOR, "corp_name": None, "pu_name": None}
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", '"' + json.dumps(ACTOR) + '"')
    assert app._development_actor() == expected_actor
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", "'" + json.dumps(ACTOR) + "'")
    assert app._development_actor() == expected_actor
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", json.dumps(json.dumps(ACTOR)))
    assert app._development_actor() == expected_actor
    monkeypatch.delenv("LINEAGEWEAVE_DEV_ACTOR_JSON")
    assert app._development_actor() is None
    monkeypatch.delenv("LINEAGEWEAVE_DEV_MODE")
    monkeypatch.setattr(app, "_actor_from_keyverse_access_token", lambda *_args: (_ for _ in ()).throw(RuntimeError("bad")))
    assert app.actor_for_request(_Handler({"Authorization": "Bearer rejected"})) is None
    assert app.actor_for_request(_Handler({})) is None
    app._sessions["session"] = {"actor": ACTOR, "expires_at": time.time() + 60}
    app.logout("session")
    assert "session" not in app._sessions
    app.logout("")


def test_keyverse_relying_party_parses_dev_actor_unicode_escape(monkeypatch) -> None:
    """Unicode-escaped development payload should still decode to a valid actor."""
    app = _application()
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    unicode_actor = {**ACTOR, "account_id": "acct-한글"}
    expected = {**unicode_actor, "corp_name": None, "pu_name": None}
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", json.dumps(json.dumps(unicode_actor)))
    assert app._development_actor() == expected
    monkeypatch.delenv("LINEAGEWEAVE_DEV_MODE")
    monkeypatch.delenv("LINEAGEWEAVE_DEV_ACTOR_JSON")


def test_keyverse_relying_party_rejects_malformed_dev_actor_compatibility_shapes(monkeypatch) -> None:
    """Compatibility decoding must fail closed for invalid and malformed actor claims."""
    app = _application()
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    invalid_actor = {"sub": "account-1", "org": "CORP_A", "workspace": "PU_A", "roles": []}

    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", "'" + json.dumps(invalid_actor) + "'")
    assert app._development_actor() is None

    escaped_invalid = '{\\"sub\\":\\"account-1\\",\\"org\\":\\"CORP_A\\",\\"workspace\\":\\"PU_A\\",\\"roles\\":[]}'
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", escaped_invalid)
    assert app._development_actor() is None

    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", r'{\"sub\":}')
    assert app._development_actor() is None


def test_server_actor_queue_and_payload_paths(monkeypatch) -> None:
    """Resolve local/session/bearer actors, drain the outbox, and use both payload paths."""
    app = _application()
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    app._sessions["session"] = {"actor": ACTOR, "expires_at": time.time() + 60}
    assert app.actor_for_request(_Handler({"Cookie": "lw_session=session"})) == ACTOR
    monkeypatch.setattr(app, "_keyverse_metadata", lambda *_args, **_kwargs: METADATA)
    monkeypatch.setattr(app, "_actor_from_keyverse_access_token", lambda *_args: (ACTOR, time.time() + 60))
    app._sessions.clear()
    assert app.actor_for_request(_Handler({"Authorization": "Bearer access"})) == ACTOR
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    expected_actor = {**ACTOR, "corp_name": None, "pu_name": None}
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", json.dumps(ACTOR))
    assert app.actor_for_request(_Handler({})) == expected_actor
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", '"' + json.dumps(ACTOR) + '"')
    assert app.actor_for_request(_Handler({})) == expected_actor
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", "'" + json.dumps(ACTOR) + "'")
    assert app.actor_for_request(_Handler({})) == expected_actor
    monkeypatch.setenv("LINEAGEWEAVE_DEV_ACTOR_JSON", json.dumps(json.dumps(ACTOR)))
    assert app.actor_for_request(_Handler({})) == expected_actor
    monkeypatch.delenv("LINEAGEWEAVE_DEV_MODE")

    events = [
        {"event_id": "event-1", "event_type": "visibility", "document_no": "DOC-1", "actor_id": "account-1", "payload": {}},
        {"event_id": "event-2", "event_type": "ticket", "document_no": "DOC-1", "actor_id": "account-1", "payload": {}},
    ]
    marked: list[str] = []
    monkeypatch.setattr(lw, "pending_event_outbox", lambda *_args: events)
    monkeypatch.setattr(lw, "publish_valkey_event", lambda _event: "1-0")
    monkeypatch.setattr(lw, "mark_event_published", lambda _connection, event_id: marked.append(event_id))
    assert app._flush_event_outbox() == 2
    assert marked == ["event-1", "event-2"]
    monkeypatch.setattr(lw, "valkey_ping", lambda: True)
    assert app.event_queue_health()["ready"] is True

    persisted = {"metadata": {}, "nodes": [{"id": "doc:DOC-1", "type": "document", "document_no": "DOC-1"}], "edges": [], "knowledge_graph": {"nodes": [], "edges": []}}
    monkeypatch.setattr(lw, "load_persisted_analysis_payload", lambda *_args, **_kwargs: persisted)
    monkeypatch.setattr(lw, "load_database_overrides", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lw, "build_knowledge_graph", lambda *_args, **_kwargs: {"nodes": [{"id": "kg:DOC-1"}], "edges": []})
    monkeypatch.setattr(lw, "persist_knowledge_graph_snapshot", lambda *_args, **_kwargs: {})
    assert app.payload()["knowledge_graph"]["nodes"]

    fallback = _application()
    built = {"metadata": {}, "nodes": [], "edges": []}
    monkeypatch.setattr(lw, "load_persisted_analysis_payload", lambda *_args, **_kwargs: {"nodes": []})
    monkeypatch.setattr(lw, "_database_query", lambda *_args, **_kwargs: [{"guid_field": "row-1"}])
    monkeypatch.setattr(lw, "ensure_common_enum_table", lambda *_args: {"entity_role": ["시장"]})
    monkeypatch.setattr(lw, "resolve_keyman_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "resolve_product_transport", lambda: (lambda _body: {}, "live_http"))
    monkeypatch.setattr(lw, "build_payload", lambda *_args, **_kwargs: built)
    monkeypatch.setattr(lw, "persist_analysis_payload", lambda *_args, **_kwargs: {})
    assert fallback.payload()["metadata"]["keyman_transport"] == "live_http"


def test_keyverse_admin_rest_and_password_grant_fail_closed(monkeypatch) -> None:
    """Keep admin REST and the short-lived admin token bounded and opaque."""
    requests: list[object] = []

    def urlopen(request, **_kwargs):  # noqa: ANN001
        requests.append(request)
        return _RawResponse(b'{"ok": true}')

    monkeypatch.setattr(server.urllib.request, "urlopen", urlopen)
    assert server._admin_json(
        "https://identity.example/admin", "fixture-token", method="PUT", body={"enabled": True}
    ) == {"ok": True}
    request = requests[-1]
    assert request.get_method() == "PUT"
    assert request.get_header("Authorization") == "Bearer fixture-token"
    assert json.loads(request.data.decode("utf-8")) == {"enabled": True}

    monkeypatch.setattr(server.urllib.request, "urlopen", lambda *_args, **_kwargs: _RawResponse(b""))
    assert server._admin_json("https://identity.example/admin", "fixture-token") is None
    monkeypatch.setattr(
        server.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            urllib.error.HTTPError("https://identity.example/admin", 503, "down", {}, None)
        ),
    )
    with pytest.raises(RuntimeError, match="keyverse_admin_503"):
        server._admin_json("https://identity.example/admin", "fixture-token")
    monkeypatch.setattr(
        server.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")),
    )
    with pytest.raises(RuntimeError, match="keyverse_admin_unavailable"):
        server._admin_json("https://identity.example/admin", "fixture-token")

    for name in ("KEYVERSE_ADMIN_TOKEN_URL", "KEYVERSE_ADMIN_USERNAME", "KEYVERSE_ADMIN_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="keyverse_registration_unavailable"):
        server._keyverse_admin_token()
    monkeypatch.setenv("KEYVERSE_ADMIN_TOKEN_URL", "https://identity.example/token")
    monkeypatch.setenv("KEYVERSE_ADMIN_USERNAME", "fixture-admin")
    monkeypatch.setenv("KEYVERSE_ADMIN_PASSWORD", "fixture-password")
    monkeypatch.setattr(
        server.urllib.request, "urlopen", lambda *_args, **_kwargs: _RawResponse(b'{"access_token": "short-token"}')
    )
    assert server._keyverse_admin_token() == "short-token"
    monkeypatch.setattr(server.urllib.request, "urlopen", lambda *_args, **_kwargs: _RawResponse(b"{}"))
    with pytest.raises(RuntimeError, match="keyverse_registration_unavailable"):
        server._keyverse_admin_token()
    monkeypatch.setattr(
        server.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")),
    )
    with pytest.raises(RuntimeError, match="keyverse_registration_unavailable"):
        server._keyverse_admin_token()


def test_keyverse_admin_account_listing_is_scoped_and_secret_free(monkeypatch) -> None:
    """Expose only same-corp or unassigned accounts and only the reviewed client roles."""
    app = _application()
    _configure_keyverse(monkeypatch)
    monkeypatch.setenv("KEYVERSE_ISSUER", "https://identity.example/realms/main")
    monkeypatch.setattr(server, "_keyverse_admin_token", lambda: "short-admin-token")
    calls: list[tuple[str, str, object | None]] = []

    users = [
        {
            "id": "same-corp",
            "username": "same-user",
            "email": "same@example.com",
            "enabled": True,
            "attributes": {"org": ["CORP_A"], "workspace": ["PU_OLD"], "private": ["hidden"]},
            "credentials": [{"secretData": "must-not-return"}],
        },
        {
            "id": "unassigned",
            "username": "new-user",
            "email": "new@example.com",
            "enabled": False,
            "attributes": {},
        },
        {
            "id": "other-corp",
            "username": "other-user",
            "email": "other@example.com",
            "enabled": True,
            "attributes": {"org": ["CORP_B"], "workspace": ["PU_B"]},
        },
    ]

    def admin_json(url: str, _token: str, *, method: str = "GET", body: object | None = None) -> object:
        calls.append((url, method, body))
        if "/clients?" in url:
            return [{"id": "client-1", "clientId": "lineage-client"}]
        if url.endswith("/clients/client-1/roles?max=100"):
            return [
                {"id": "role-member", "name": "member", "description": "reader"},
                {"id": "role-admin", "name": "admin", "description": "administrator"},
            ]
        if "/users?" in url:
            return users
        if url.endswith("/users/same-corp/role-mappings/clients/client-1"):
            return [{"id": "role-member", "name": "member"}]
        if url.endswith("/users/unassigned/role-mappings/clients/client-1"):
            return []
        if url.endswith("/users/other-corp/role-mappings/clients/client-1"):
            return [{"id": "role-member", "name": "member"}]
        raise AssertionError(url)

    monkeypatch.setattr(server, "_admin_json", admin_json)
    result = app.keyverse_admin_accounts(ACTOR, query="  user  ", limit=500)
    assert result["corp_code"] == "CORP_A"
    assert result["available_roles"] == [
        {"id": "role-admin", "name": "admin", "description": "administrator"},
        {"id": "role-member", "name": "member", "description": "reader"},
    ]
    assert [account["account_id"] for account in result["accounts"]] == ["same-corp", "unassigned"]
    assert result["accounts"][0]["org"] == "CORP_A"
    assert result["accounts"][0]["roles"] == ["member"]
    assert "credentials" not in result["accounts"][0]
    user_query = next(url for url, method, _body in calls if method == "GET" and "/users?" in url)
    assert urllib.parse.parse_qs(urllib.parse.urlsplit(user_query).query) == {
        "first": ["0"],
        "max": ["50"],
        "search": ["user"],
    }
    monkeypatch.setattr(server, "_keyverse_admin_token", lambda: (_ for _ in ()).throw(RuntimeError("keyverse_registration_unavailable")))
    with pytest.raises(RuntimeError, match="keyverse_admin_unavailable"):
        app.keyverse_admin_accounts(ACTOR)


def test_keyverse_admin_account_update_reconciles_only_same_client_roles(monkeypatch) -> None:
    """Update reviewed account attributes and same-client roles without credential mutation."""
    app = _application()
    _configure_keyverse(monkeypatch)
    monkeypatch.setenv("KEYVERSE_ISSUER", "https://identity.example/realms/main")
    monkeypatch.setattr(server, "_keyverse_admin_token", lambda: "short-admin-token")
    calls: list[tuple[str, str, object | None]] = []
    target = {
        "id": "same-corp",
        "username": "same-user",
        "email": "same@example.com",
        "enabled": True,
        "attributes": {"org": ["CORP_A"], "workspace": ["PU_OLD"], "department": ["sales"]},
        "credentials": [{"secretData": "must-not-send"}],
    }

    def admin_json(url: str, _token: str, *, method: str = "GET", body: object | None = None) -> object:
        calls.append((url, method, body))
        if "/clients?" in url:
            return [{"id": "client-1", "clientId": "lineage-client"}]
        if url.endswith("/clients/client-1/roles?max=100"):
            return [{"id": "role-member", "name": "member"}, {"id": "role-admin", "name": "admin"}]
        if url.endswith("/users/same-corp") and method == "GET":
            return target
        if url.endswith("/users/same-corp/role-mappings/clients/client-1") and method == "GET":
            return [{"id": "role-member", "name": "member"}]
        if url.endswith("/users/same-corp") and method == "PUT":
            assert body == {
                "attributes": {"org": ["CORP_A"], "workspace": ["PU_NEW"], "department": ["sales"]}
            }
            assert "credentials" not in body
            return None
        if url.endswith("/users/same-corp/role-mappings/clients/client-1") and method == "POST":
            assert body == [{"id": "role-admin", "name": "admin"}]
            return None
        if url.endswith("/users/same-corp/role-mappings/clients/client-1") and method == "DELETE":
            assert body == [{"id": "role-member", "name": "member"}]
            return None
        if url.endswith("/users/other-corp") and method == "GET":
            return {"id": "other-corp", "attributes": {"org": ["CORP_B"]}}
        raise AssertionError((url, method, body))

    monkeypatch.setattr(server, "_admin_json", admin_json)
    result = app.update_keyverse_account(
        ACTOR,
        "same-corp",
        {"org": "CORP_A", "workspace": "PU_NEW", "roles": ["admin"]},
    )
    assert result == {
        "account_id": "same-corp",
        "username": "same-user",
        "email": "same@example.com",
        "enabled": True,
        "org": "CORP_A",
        "workspace": "PU_NEW",
        "roles": ["admin"],
    }
    assert [method for _url, method, _body in calls] == ["GET", "GET", "GET", "GET", "PUT", "GET", "POST", "DELETE"]
    with pytest.raises(PermissionError, match="keyverse_account_cross_corp"):
        app.update_keyverse_account(ACTOR, "other-corp", {"workspace": "PU", "roles": []})
    with pytest.raises(ValueError, match="keyverse_role_unavailable"):
        app.update_keyverse_account(ACTOR, "same-corp", {"workspace": "PU", "roles": ["missing"]})
    with pytest.raises(ValueError, match="keyverse_workspace_required"):
        app.update_keyverse_account(ACTOR, "same-corp", {"workspace": "", "roles": []})
    with pytest.raises(PermissionError, match="keyverse_admin_required"):
        app.update_keyverse_account({**ACTOR, "roles": ["reader"]}, "same-corp", {})


def test_keyverse_admin_account_boundaries_fail_closed(monkeypatch) -> None:
    """Reject malformed issuer, user, role, and account inputs before mutation."""
    app = _application()
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_COOKIE_SECURE", "0")
    monkeypatch.delenv("KEYVERSE_ISSUER", raising=False)
    with pytest.raises(RuntimeError, match="keyverse_admin_configuration_required"):
        app.keyverse_admin_accounts(ACTOR)
    monkeypatch.setenv("KEYVERSE_ISSUER", "http://localhost:28080/realms/cwl/extra")
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_CLIENT_ID", "lineage-client")
    with pytest.raises(RuntimeError, match="keyverse_admin_configuration_required"):
        app.keyverse_admin_accounts(ACTOR)
    with pytest.raises(PermissionError, match="keyverse_admin_required"):
        app.keyverse_admin_accounts({**ACTOR, "roles": ["reader"]})
    monkeypatch.setenv("KEYVERSE_ISSUER", "https://identity.example/realms/main")
    monkeypatch.setattr(server, "_keyverse_admin_token", lambda: "short-admin-token")

    def malformed_admin_json(url: str, _token: str, *, method: str = "GET", body: object | None = None) -> object:
        del method, body
        if "/clients?" in url:
            return []
        raise AssertionError(url)

    monkeypatch.setattr(server, "_admin_json", malformed_admin_json)
    with pytest.raises(RuntimeError, match="keyverse_admin_client_not_found"):
        app.keyverse_admin_accounts(ACTOR)


def test_keyverse_admin_helpers_and_update_noop_cover_fail_closed_shapes(monkeypatch) -> None:
    """Cover malformed Keyverse representations and a role/claim update with no role delta."""
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_COOKIE_SECURE", "0")
    monkeypatch.setenv("KEYVERSE_ISSUER", "http://identity.example/realms/main")
    monkeypatch.setenv("LINEAGEWEAVE_OIDC_CLIENT_ID", "lineage-client")
    with pytest.raises(RuntimeError, match="keyverse_admin_configuration_required"):
        server._keyverse_admin_context()
    monkeypatch.setattr(server, "_keyverse_admin_token", lambda: (_ for _ in ()).throw(RuntimeError("other_failure")))
    with pytest.raises(RuntimeError, match="other_failure"):
        server._keyverse_admin_access_token()
    monkeypatch.setattr(server, "_keyverse_client_descriptor", lambda *_args: {"id": "client-1", "client_id": "lineage-client"})
    monkeypatch.setattr(server, "_admin_json", lambda *_args, **_kwargs: {})
    with pytest.raises(RuntimeError, match="keyverse_admin_roles_not_found"):
        server._keyverse_client_roles("https://identity.example/admin", "token", "lineage-client")
    monkeypatch.setattr(server, "_admin_json", lambda *_args, **_kwargs: [])
    with pytest.raises(RuntimeError, match="keyverse_admin_roles_not_found"):
        server._keyverse_client_roles("https://identity.example/admin", "token", "lineage-client")
    with pytest.raises(ValueError, match="keyverse_role_invalid"):
        server._keyverse_claim_value(1, "role", required=True)
    with pytest.raises(ValueError, match="keyverse_role_required"):
        server._keyverse_claim_value("", "role", required=True)
    assert server._keyverse_claim_value("", "role", required=False) == ""
    with pytest.raises(ValueError, match="keyverse_role_invalid"):
        server._keyverse_claim_value("bad\nvalue", "role", required=True)
    with pytest.raises(ValueError, match="keyverse_role_invalid"):
        server._keyverse_claim_value("x" * 65, "role", required=True)
    assert server._keyverse_scalar_attribute({}, "org") == ""
    assert server._keyverse_scalar_attribute({"attributes": {"org": "CORP_A"}}, "org") == "CORP_A"
    assert server._keyverse_scalar_attribute({"attributes": {"org": ["CORP_A"]}}, "org") == "CORP_A"
    assert server._keyverse_scalar_attribute({"attributes": {"org": ["A", "B"]}}, "org") == ""
    assert server._keyverse_account_view("not-a-user", []) is None
    assert server._keyverse_account_view({"username": "missing-id"}, []) is None
    monkeypatch.setattr(server, "_admin_json", lambda *_args, **_kwargs: {})
    with pytest.raises(RuntimeError, match="keyverse_admin_roles_invalid"):
        server._keyverse_role_mappings("https://identity.example/admin", "token", "user", "client")

    app = _application()
    monkeypatch.setenv("KEYVERSE_ISSUER", "https://identity.example/realms/main")
    monkeypatch.setattr(server, "_keyverse_admin_token", lambda: "short-admin-token")
    monkeypatch.setattr(
        server,
        "_keyverse_client_roles",
        lambda *_args: [{"id": "role-admin", "name": "admin", "description": ""}],
    )
    monkeypatch.setattr(
        server,
        "_keyverse_client_descriptor",
        lambda *_args: {"id": "client-1", "client_id": "lineage-client"},
    )
    monkeypatch.setattr(server, "_admin_json", lambda *_args, **_kwargs: {})
    with pytest.raises(ValueError, match="keyverse_account_query_too_long"):
        app.keyverse_admin_accounts(ACTOR, query="x" * 129)
    with pytest.raises(RuntimeError, match="keyverse_admin_accounts_invalid"):
        app.keyverse_admin_accounts(ACTOR)
    with pytest.raises(ValueError, match="keyverse_account_id_invalid"):
        app.update_keyverse_account(ACTOR, "bad/id", {})

    target = {
        "id": "same-corp",
        "username": "same-user",
        "email": "same@example.com",
        "enabled": True,
        "attributes": {"org": ["CORP_A"], "workspace": ["PU_OLD"]},
    }

    def noop_admin_json(url: str, _token: str, *, method: str = "GET", body: object | None = None) -> object:
        if url.endswith("/users/same-corp") and method == "GET":
            return target
        if url.endswith("/users/same-corp") and method == "PUT":
            return None
        if "role-mappings" in url:
            return [{"id": "role-admin", "name": "admin"}] if method == "GET" else None
        raise AssertionError((url, method, body))

    monkeypatch.setattr(server, "_admin_json", noop_admin_json)
    updated = app.update_keyverse_account(
        ACTOR,
        "same-corp",
        {"workspace": "PU_NEW", "roles": ["admin", "admin"]},
    )
    assert updated["roles"] == ["admin"]

    monkeypatch.setattr(server, "_admin_json", lambda *_args, **_kwargs: {"id": "different"})
    with pytest.raises(KeyError):
        app.update_keyverse_account(ACTOR, "same-corp", {"workspace": "PU", "roles": []})
    monkeypatch.setattr(server, "_admin_json", lambda *_args, **_kwargs: target)
    with pytest.raises(PermissionError, match="keyverse_account_cross_corp"):
        app.update_keyverse_account(ACTOR, "same-corp", {"org": "CORP_B", "workspace": "PU", "roles": []})
    with pytest.raises(ValueError, match="keyverse_roles_required"):
        app.update_keyverse_account(ACTOR, "same-corp", {"workspace": "PU"})
