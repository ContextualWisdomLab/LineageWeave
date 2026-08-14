"""Keyverse-shaped OIDC handlers kept as an offline test utility.

This module does not provide the compose runtime Identity service and is only
loaded for test/dev utility checks.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler
from typing import Any

_OIDC_LOCK = threading.Lock()
_AUTH_CODES: dict[str, dict[str, Any]] = {}
_ACCESS_TOKENS: dict[str, dict[str, Any]] = {}

OIDC_GET_PATHS = (
    "/.well-known/openid-configuration",
    "/protocol/openid-connect/auth",
)
OIDC_POST_PATHS = (
    "/protocol/openid-connect/token",
    "/protocol/openid-connect/token/introspect",
)

_COMPOSE_FORBIDDEN_ERROR = "compose_keyverse_oidc_module_is_not_runnable_in_compose"
_COMPOSE_STANDIN_FLAG = "LINEAGEWEAVE_COMPOSE_STANDIN"
_COMPOSE_CONTAINER_MARKERS = ("/.dockerenv", "/run/.containerenv")

if (
    os.environ.get(_COMPOSE_STANDIN_FLAG) == "1"
    or any(os.path.exists(marker) for marker in _COMPOSE_CONTAINER_MARKERS)
):
    # ponytail: hard-disable mock IdP bootstrap in compose worker runtime.
    raise RuntimeError(_COMPOSE_FORBIDDEN_ERROR)


def write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    """Write a compact JSON response without logging secrets."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def write_redirect(handler: BaseHTTPRequestHandler, location: str) -> None:
    """Send a 302 without logging PKCE query values."""
    handler.send_response(302)
    handler.send_header("Location", location)
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()


def client_id() -> str:
    """Return the confidential OIDC client identifier."""
    return os.environ.get("OIDC_CLIENT_ID") or "lineageweave-web"


def client_secret() -> str:
    """Return the confidential OIDC client secret."""
    return os.environ.get("OIDC_CLIENT_SECRET") or "compose-dev-only"


def issuer() -> str:
    """Return the issuer URL this process advertises."""
    configured = (os.environ.get("OIDC_ISSUER") or "").strip().rstrip("/")
    if configured:
        return configured
    return f"http://127.0.0.1:{os.environ.get('STANDIN_PORT') or '8080'}"


def oidc_claims() -> dict[str, Any]:
    """Return the single local development account mapped into OIDC claims."""
    roles = [
        item.strip()
        for item in (os.environ.get("OIDC_ROLE") or "author,editor,reader").split(",")
        if item.strip()
    ]
    subject = os.environ.get("OIDC_ACCOUNT_SUB") or "acct-local-1"
    return {
        "iss": issuer(),
        "aud": client_id(),
        "client_id": client_id(),
        "active": True,
        "sub": subject,
        "preferred_username": subject,
        "org": os.environ.get("OIDC_ORG") or "ORG_A",
        "workspace": os.environ.get("OIDC_WORKSPACE") or "D02",
        "role": roles,
        "realm_access": {"roles": roles},
    }


def s256(verifier: str) -> str:
    """Return the S256 code challenge for one PKCE verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def discovery_document() -> dict[str, Any]:
    """Return a Keyverse-shaped OpenID Provider configuration."""
    base = issuer()
    return {
        "issuer": base,
        "authorization_endpoint": base + "/protocol/openid-connect/auth",
        "token_endpoint": base + "/protocol/openid-connect/token",
        "introspection_endpoint": base + "/protocol/openid-connect/token/introspect",
        "jwks_uri": base + "/protocol/openid-connect/certs",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic"],
        "scopes_supported": ["openid", "profile", "email"],
    }


def _read_form(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    """Parse one application/x-www-form-urlencoded body."""
    length = int(handler.headers.get("Content-Length") or "0")
    raw = handler.rfile.read(length) if length else b""
    parsed = urllib.parse.parse_qs(raw.decode("utf-8"), keep_blank_values=True)
    return {key: (values[-1] if values else "") for key, values in parsed.items()}


def _basic_client(handler: BaseHTTPRequestHandler) -> tuple[str, str]:
    """Decode HTTP Basic client credentials when present."""
    header = handler.headers.get("Authorization") or ""
    if not header.lower().startswith("basic "):
        return "", ""
    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return "", ""
    identity, _separator, secret = decoded.partition(":")
    return urllib.parse.unquote(identity), urllib.parse.unquote(secret)


def _client_authorized(handler: BaseHTTPRequestHandler, form: dict[str, str]) -> bool:
    """Accept client_secret_basic or a matching form-body client_secret."""
    header_id, header_secret = _basic_client(handler)
    if header_id and header_secret:
        return header_id == client_id() and header_secret == client_secret()
    return form.get("client_id") == client_id() and form.get("client_secret") == client_secret()


def authorize(handler: BaseHTTPRequestHandler) -> None:
    """Issue an authorization code after checking S256 PKCE parameters."""
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(handler.path).query)
    requested_client = (query.get("client_id") or [""])[0]
    redirect_uri = (query.get("redirect_uri") or [""])[0]
    state = (query.get("state") or [""])[0]
    challenge = (query.get("code_challenge") or [""])[0]
    method = (query.get("code_challenge_method") or [""])[0]
    if requested_client != client_id() or not redirect_uri or method != "S256" or not challenge:
        write_json(handler, 400, {"error": "invalid_request"})
        return
    code = secrets.token_urlsafe(24)
    with _OIDC_LOCK:
        _AUTH_CODES[code] = {
            "code_challenge": challenge,
            "redirect_uri": redirect_uri,
            "claims": oidc_claims(),
        }
    location = redirect_uri + ("&" if "?" in redirect_uri else "?")
    location += urllib.parse.urlencode({"code": code, "state": state})
    write_redirect(handler, location)


def token(handler: BaseHTTPRequestHandler) -> None:
    """Exchange an authorization code plus PKCE verifier for an access token."""
    form = _read_form(handler)
    if not _client_authorized(handler, form):
        write_json(handler, 401, {"error": "invalid_client"})
        return
    if form.get("grant_type") != "authorization_code":
        write_json(handler, 400, {"error": "unsupported_grant_type"})
        return
    with _OIDC_LOCK:
        record = _AUTH_CODES.pop(form.get("code") or "", None)
    if not record:
        write_json(handler, 400, {"error": "invalid_grant"})
        return
    if form.get("redirect_uri") != record["redirect_uri"]:
        write_json(handler, 400, {"error": "invalid_grant"})
        return
    if s256(form.get("code_verifier") or "") != record["code_challenge"]:
        write_json(handler, 400, {"error": "invalid_grant"})
        return
    access_token = secrets.token_urlsafe(32)
    claims = dict(record["claims"])
    claims["exp"] = time.time() + 3600
    with _OIDC_LOCK:
        _ACCESS_TOKENS[access_token] = claims
    write_json(
        handler,
        200,
        {"access_token": access_token, "token_type": "Bearer", "expires_in": 3600},
    )


def introspect(handler: BaseHTTPRequestHandler) -> None:
    """Return active claims for a previously issued access token."""
    form = _read_form(handler)
    if not _client_authorized(handler, form):
        write_json(handler, 401, {"error": "invalid_client"})
        return
    with _OIDC_LOCK:
        claims = _ACCESS_TOKENS.get(form.get("token") or "")
    if not claims:
        write_json(handler, 200, {"active": False})
        return
    write_json(handler, 200, dict(claims))


def handle_get(handler: BaseHTTPRequestHandler, path: str) -> bool:
    """Dispatch OIDC GET routes. True when this module served the request."""
    if path == "/.well-known/openid-configuration":
        write_json(handler, 200, discovery_document())
        return True
    if path == "/protocol/openid-connect/auth":
        authorize(handler)
        return True
    return False


def handle_post(handler: BaseHTTPRequestHandler, path: str) -> bool:
    """Dispatch OIDC POST routes. True when this module served the request."""
    if path == "/protocol/openid-connect/token":
        token(handler)
        return True
    if path == "/protocol/openid-connect/token/introspect":
        introspect(handler)
        return True
    return False


def handle(handler: BaseHTTPRequestHandler) -> None:
    """Dispatch OIDC and health routes through the local Keyverse-shaped mock."""
    path = handler.path.split("?", 1)[0]
    if handler.command == "GET":
        if path == "/health":
            write_json(
                handler,
                200,
                {"status": "ok", "issuer": issuer(), "client_id": client_id()},
            )
            return
        if handle_get(handler, path):
            return
    elif handler.command == "POST":
        if handle_post(handler, path):
            return
    write_json(handler, 404, {"error": "not_found"})


if __name__ in {"__main__", "<run_path>"}:
    # Composition runtime intentionally does not start this module as a service.
    raise RuntimeError(_COMPOSE_FORBIDDEN_ERROR)
