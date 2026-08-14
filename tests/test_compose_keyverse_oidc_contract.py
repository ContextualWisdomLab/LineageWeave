"""Exercise the retained offline Keyverse-shaped OIDC utility end to end."""

from __future__ import annotations

import base64
import importlib
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest


OIDC = importlib.import_module("compose.keyverse_oidc")


class _Handler(BaseHTTPRequestHandler):
    """Delegate HTTP methods to the offline utility without writing logs."""

    def do_GET(self) -> None:  # noqa: N802
        OIDC.handle(self)

    def do_POST(self) -> None:  # noqa: N802
        OIDC.handle(self)

    def do_PUT(self) -> None:  # noqa: N802
        OIDC.handle(self)

    def log_message(self, _format: str, *_args: object) -> None:
        """Keep test output deterministic and free of query credentials."""


@pytest.fixture
def oidc_origin() -> str:
    """Run the utility behind a real loopback HTTP server for contract tests."""
    with OIDC._OIDC_LOCK:
        OIDC._AUTH_CODES.clear()
        OIDC._ACCESS_TOKENS.clear()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Expose the authorization response instead of following its callback."""

    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _request(
    origin: str,
    path: str,
    *,
    method: str = "GET",
    form: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], Any]:
    """Make one request and decode either JSON or a redirect response."""
    data = urllib.parse.urlencode(form or {}).encode("utf-8") if form is not None else None
    request = urllib.request.Request(
        origin + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/x-www-form-urlencoded", **(headers or {})},
    )
    try:
        response = _OPENER.open(request, timeout=5)
        status = response.status
        response_headers = {key: value for key, value in response.headers.items()}
        body = response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        response_headers = {key: value for key, value in error.headers.items()}
        body = error.read()
    if not body:
        return status, response_headers, None
    try:
        return status, response_headers, json.loads(body)
    except json.JSONDecodeError:
        return status, response_headers, body.decode("utf-8")


def _authorization_path(origin: str, *, challenge: str, state: str = "state-1") -> str:
    """Build one valid authorization request for the local utility."""
    query = urllib.parse.urlencode(
        {
            "client_id": OIDC.client_id(),
            "redirect_uri": origin + "/callback",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return "/protocol/openid-connect/auth?" + query


def test_configured_claims_and_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured issuer, client, account, organization, PU, and role claims survive shaping."""
    monkeypatch.setenv("OIDC_ISSUER", "https://identity.example/realms/lineage")
    monkeypatch.setenv("OIDC_CLIENT_ID", "lineageweave-test")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "secret-value")
    monkeypatch.setenv("OIDC_ACCOUNT_SUB", "account-42")
    monkeypatch.setenv("OIDC_ORG", "CORP_TEST")
    monkeypatch.setenv("OIDC_WORKSPACE", "PU_TEST")
    monkeypatch.setenv("OIDC_ROLE", "reader, ,admin")

    assert OIDC.client_id() == "lineageweave-test"
    assert OIDC.client_secret() == "secret-value"
    claims = OIDC.oidc_claims()
    assert claims["iss"] == "https://identity.example/realms/lineage"
    assert claims["sub"] == "account-42"
    assert claims["org"] == "CORP_TEST"
    assert claims["workspace"] == "PU_TEST"
    assert claims["role"] == ["reader", "admin"]
    assert OIDC.discovery_document()["jwks_uri"].endswith("/protocol/openid-connect/certs")


def test_module_guard_rejects_compose_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """The retained utility refuses to load when the Compose worker flag is set."""
    monkeypatch.setenv("LINEAGEWEAVE_COMPOSE_STANDIN", "1")
    with pytest.raises(RuntimeError, match="compose_keyverse_oidc_module_is_not_runnable_in_compose"):
        importlib.reload(OIDC)
    monkeypatch.delenv("LINEAGEWEAVE_COMPOSE_STANDIN")
    importlib.reload(OIDC)


def test_pkce_token_and_introspection_flow(oidc_origin: str) -> None:
    """A valid S256 authorization-code flow issues and introspects one live token."""
    verifier = "verifier-for-contract"
    status, headers, _ = _request(
        oidc_origin,
        _authorization_path(oidc_origin, challenge=OIDC.s256(verifier)),
    )
    assert status == 302
    location = urllib.parse.urlsplit(headers["Location"])
    callback = urllib.parse.parse_qs(location.query)
    code = callback["code"][0]
    assert callback["state"] == ["state-1"]

    basic = base64.b64encode(f"{OIDC.client_id()}:{OIDC.client_secret()}".encode()).decode()
    token_status, _token_headers, token = _request(
        oidc_origin,
        "/protocol/openid-connect/token",
        method="POST",
        form={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": oidc_origin + "/callback",
            "code_verifier": verifier,
        },
        headers={"Authorization": f"Basic {basic}"},
    )
    assert token_status == 200
    assert token["token_type"] == "Bearer"

    introspection_status, _headers, claims = _request(
        oidc_origin,
        "/protocol/openid-connect/token/introspect",
        method="POST",
        form={
            "client_id": OIDC.client_id(),
            "client_secret": OIDC.client_secret(),
            "token": token["access_token"],
        },
    )
    assert introspection_status == 200
    assert claims["active"] is True
    assert claims["sub"] == "acct-local-1"

    inactive_status, _headers, inactive = _request(
        oidc_origin,
        "/protocol/openid-connect/token/introspect",
        method="POST",
        form={
            "client_id": OIDC.client_id(),
            "client_secret": OIDC.client_secret(),
            "token": "missing-token",
        },
    )
    assert inactive_status == 200
    assert inactive == {"active": False}

    bad_client_status, _headers, bad_client = _request(
        oidc_origin,
        "/protocol/openid-connect/token/introspect",
        method="POST",
        form={"client_id": "wrong", "client_secret": "wrong", "token": token["access_token"]},
    )
    assert (bad_client_status, bad_client) == (401, {"error": "invalid_client"})


def test_rejection_paths_and_dispatch(oidc_origin: str) -> None:
    """Invalid PKCE, client, grant, method, and route inputs fail closed."""
    invalid = urllib.parse.urlencode(
        {
            "client_id": "wrong-client",
            "redirect_uri": oidc_origin + "/callback",
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
        }
    )
    status, _headers, payload = _request(oidc_origin, "/protocol/openid-connect/auth?" + invalid)
    assert (status, payload) == (400, {"error": "invalid_request"})

    status, _headers, payload = _request(
        oidc_origin,
        "/protocol/openid-connect/token",
        method="POST",
        form={"client_id": OIDC.client_id(), "client_secret": OIDC.client_secret(), "grant_type": "client_credentials"},
    )
    assert (status, payload) == (400, {"error": "unsupported_grant_type"})

    status, _headers, payload = _request(
        oidc_origin,
        "/protocol/openid-connect/token",
        method="POST",
        form={"client_id": "wrong", "client_secret": "wrong", "grant_type": "authorization_code"},
    )
    assert (status, payload) == (401, {"error": "invalid_client"})

    verifier = "rejection-verifier"
    status, headers, _ = _request(
        oidc_origin,
        _authorization_path(oidc_origin, challenge=OIDC.s256(verifier), state="bad-code"),
    )
    code = urllib.parse.parse_qs(urllib.parse.urlsplit(headers["Location"]).query)["code"][0]
    common = {"client_id": OIDC.client_id(), "client_secret": OIDC.client_secret(), "grant_type": "authorization_code", "code": code}
    status, _headers, payload = _request(
        oidc_origin,
        "/protocol/openid-connect/token",
        method="POST",
        form={**common, "redirect_uri": oidc_origin + "/wrong", "code_verifier": verifier},
    )
    assert (status, payload) == (400, {"error": "invalid_grant"})

    status, _headers, payload = _request(
        oidc_origin,
        "/protocol/openid-connect/token",
        method="POST",
        form={**common, "redirect_uri": oidc_origin + "/callback", "code_verifier": "wrong"},
    )
    assert (status, payload) == (400, {"error": "invalid_grant"})

    status, _headers, payload = _request(
        oidc_origin,
        "/protocol/openid-connect/token",
        method="POST",
        form={"client_id": OIDC.client_id(), "client_secret": OIDC.client_secret(), "grant_type": "authorization_code", "code": "used-or-missing"},
    )
    assert (status, payload) == (400, {"error": "invalid_grant"})

    verifier_status, verifier_headers, _ = _request(
        oidc_origin,
        _authorization_path(oidc_origin, challenge=OIDC.s256("right-verifier"), state="wrong-verifier"),
    )
    verifier_code = urllib.parse.parse_qs(urllib.parse.urlsplit(verifier_headers["Location"]).query)["code"][0]
    assert verifier_status == 302
    status, _headers, payload = _request(
        oidc_origin,
        "/protocol/openid-connect/token",
        method="POST",
        form={
            "client_id": OIDC.client_id(),
            "client_secret": OIDC.client_secret(),
            "grant_type": "authorization_code",
            "code": verifier_code,
            "redirect_uri": oidc_origin + "/callback",
            "code_verifier": "wrong-verifier",
        },
    )
    assert (status, payload) == (400, {"error": "invalid_grant"})

    status, _headers, payload = _request(oidc_origin, "/.well-known/openid-configuration")
    assert status == 200 and payload["response_types_supported"] == ["code"]
    status, _headers, payload = _request(oidc_origin, "/unknown")
    assert (status, payload) == (404, {"error": "not_found"})
    status, _headers, payload = _request(oidc_origin, "/health")
    assert status == 200 and payload["status"] == "ok"
    status, _headers, payload = _request(oidc_origin, "/unknown", method="PUT")
    assert (status, payload) == (404, {"error": "not_found"})
    status, _headers, payload = _request(oidc_origin, "/unknown", method="POST", form={})
    assert (status, payload) == (404, {"error": "not_found"})


def test_low_level_parsers_cover_empty_and_malformed_credentials() -> None:
    """Empty forms and malformed Basic headers are treated as unauthorised input."""

    class Headers:
        def __init__(self, value: str | None, length: str | None = None) -> None:
            self.value = value
            self.length = length

        def get(self, name: str) -> str | None:
            return self.value if name == "Authorization" else self.length

    class Body:
        def __init__(self, raw: bytes) -> None:
            self.raw = raw

        def read(self, _length: int) -> bytes:
            return self.raw

    class Handler:
        def __init__(self, auth: str | None, raw: bytes = b"", length: str | None = None) -> None:
            self.headers = Headers(auth, length)
            self.rfile = Body(raw)

    assert OIDC._read_form(Handler(None)) == {}
    assert OIDC._read_form(Handler(None, b"a=1&a=2", "7")) == {"a": "2"}
    assert OIDC._basic_client(Handler("Basic !!!")) == ("", "")
    assert OIDC._basic_client(Handler("Basic /w==")) == ("", "")
    assert OIDC._basic_client(Handler("Bearer value")) == ("", "")
    assert OIDC._client_authorized(Handler(None), {}) is False
