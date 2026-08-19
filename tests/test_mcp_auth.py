from __future__ import annotations

import json
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.algorithms import RSAAlgorithm

from backend.app import auth, config, mcp_auth
from backend.app.config import Settings


def settings() -> Settings:
    """Return one production-shaped local test configuration."""
    return Settings(
        database_url="postgresql://example",
        keycloak_base_url="https://issuer.example",
        keycloak_realm="realm",
        keycloak_client_id="lineageweave-frontend",
        keycloak_issuer="https://issuer.example/realms/realm",
        frontend_origins=["https://app.example"],
        orchestrator_base_url="",
        orchestrator_api_key="",
        vision_model="",
        valkey_url="redis://example",
        searxng_base_url="",
        tepp_transport_url="",
        rankweave_disabled=False,
        mcp_resource_url="https://lineage.example/mcp",
        mcp_audience="https://lineage.example/mcp",
        mcp_required_scopes=["lineageweave:ask"],
        mcp_allowed_hosts=["lineage.example"],
        mcp_allowed_origins=[],
    )


def signed_token(*, audience: str, include_kid: bool = True):
    """Create an RS256 token and matching public JWKS."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "key-1", "use": "sig", "alg": "RS256"})
    now = int(time.time())
    claims = {
        "iss": "https://issuer.example/realms/realm",
        "sub": "subject-1",
        "aud": audience,
        "azp": "codex-client",
        "scope": "openid lineageweave:ask",
        "exp": now + 600,
        "iat": now,
    }
    headers = {"kid": "key-1"} if include_kid else {}
    return jwt.encode(claims, private_key, algorithm="RS256", headers=headers), {
        "keys": [public_jwk]
    }


@pytest.fixture(autouse=True)
def clear_jwks_cache() -> None:
    """Keep key-rotation/cache assertions independent."""
    auth._jwks_cache.clear()


def test_load_settings_defaults_and_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "MCP_RESOURCE_URL",
        "MCP_AUDIENCE",
        "MCP_REQUIRED_SCOPES",
        "MCP_ALLOWED_HOSTS",
        "MCP_ALLOWED_ORIGINS",
        "RANKWEAVE_DISABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    defaults = config.load_settings()
    assert defaults.mcp_resource_url == "http://localhost:18001/mcp"
    assert defaults.mcp_audience == defaults.mcp_resource_url
    assert defaults.mcp_required_scopes == []
    assert defaults.keycloak_jwks_uri.endswith("/protocol/openid-connect/certs")

    monkeypatch.setenv("MCP_REQUIRED_SCOPES", " one, ,two ")
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example, 127.0.0.1:*")
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://codex.example")
    monkeypatch.setenv("MCP_AUDIENCE", "urn:lineageweave:mcp")
    monkeypatch.setenv("RANKWEAVE_DISABLED", "YES")
    custom = config.load_settings()
    assert custom.mcp_required_scopes == ["one", "two"]
    assert custom.mcp_allowed_hosts == ["mcp.example", "127.0.0.1:*"]
    assert custom.mcp_allowed_origins == ["https://codex.example"]
    assert custom.mcp_audience == "urn:lineageweave:mcp"
    assert custom.rankweave_disabled is True


def test_jwks_cache_fetch_validation_and_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = settings()
    calls = 0

    def fetch_ok(url: str, timeout: int):
        nonlocal calls
        calls += 1
        assert url == cfg.keycloak_jwks_uri
        assert timeout == 10
        return {"keys": []}

    monkeypatch.setattr(auth, "get_json", fetch_ok)
    assert auth._jwks(cfg) == {"keys": []}
    assert auth._jwks(cfg) == {"keys": []}
    assert calls == 1

    auth._jwks_cache.clear()
    monkeypatch.setattr(auth, "get_json", lambda *_args, **_kwargs: [])
    with pytest.raises(HTTPException, match="not an object"):
        auth._jwks(cfg)

    auth._jwks_cache.clear()

    def unavailable(*_args, **_kwargs):
        raise OSError("down")

    monkeypatch.setattr(auth, "get_json", unavailable)
    with pytest.raises(HTTPException, match="could not fetch JWKS"):
        auth._jwks(cfg)


def test_decode_access_token_requires_exact_kid_and_resource_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = settings()
    token, jwks = signed_token(audience=cfg.mcp_audience)
    monkeypatch.setattr(auth, "_jwks", lambda _: jwks)
    claims = auth.decode_access_token(token, cfg, audience=cfg.mcp_audience)
    assert claims["sub"] == "subject-1"
    assert auth._decode_access_token(token, cfg)["sub"] == "subject-1"

    missing_kid, missing_jwks = signed_token(audience=cfg.mcp_audience, include_kid=False)
    monkeypatch.setattr(auth, "_jwks", lambda _: missing_jwks)
    with pytest.raises(HTTPException, match="kid"):
        auth.decode_access_token(missing_kid, cfg, audience=cfg.mcp_audience)

    wrong_aud, wrong_jwks = signed_token(audience="https://other.example/mcp")
    monkeypatch.setattr(auth, "_jwks", lambda _: wrong_jwks)
    with pytest.raises(HTTPException, match="invalid token"):
        auth.decode_access_token(wrong_aud, cfg, audience=cfg.mcp_audience)


def test_signing_key_rejects_bad_headers_keys_and_ambiguity() -> None:
    with pytest.raises(HTTPException, match="header"):
        auth._signing_key_from_jwks({"keys": []}, "not-a-jwt")
    with pytest.raises(HTTPException, match="missing kid"):
        auth._signing_key_from_jwks({"keys": []}, "eyJhbGciOiJSUzI1NiJ9.e30.sig")
    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImsxIn0.e30.sig"
    with pytest.raises(auth._SigningKeyNotFound):
        auth._signing_key_from_jwks({"keys": []}, token)
    duplicate = {"kid": "k1", "kty": "RSA", "use": "sig"}
    with pytest.raises(auth._SigningKeyNotFound):
        auth._signing_key_from_jwks({"keys": [duplicate, duplicate]}, token)
    with pytest.raises(HTTPException, match="signing key"):
        auth._signing_key_from_jwks({"keys": [duplicate]}, token)


def test_decode_refreshes_jwks_once_then_rejects_unknown_kid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = settings()
    calls = 0

    def no_matching_key(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return {"keys": []}

    monkeypatch.setattr(auth, "get_json", no_matching_key)
    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6Im5ldy1rZXkifQ.e30.sig"
    with pytest.raises(HTTPException, match="expected one RSA signing key"):
        auth.decode_access_token(token, cfg, audience=cfg.mcp_audience)
    assert calls == 2


class Acquire:
    """Async context manager returned by the fake pool."""

    def __init__(self, conn) -> None:
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *_args):
        return False


class FakePool:
    """Minimal asyncpg-pool contract for account resolution."""

    def __init__(self, conn) -> None:
        self.conn = conn

    def acquire(self):
        return Acquire(self.conn)


class AccountConnection:
    """Deterministic user, affiliation, and permission result set."""

    def __init__(self, account_row) -> None:
        self.account_row = account_row

    async def fetchrow(self, _sql, _subject):
        return self.account_row

    async def fetch(self, sql, _account_id):
        if "account_affiliation" in sql:
            return [{"corporate_entity_id": "entity-1"}]
        return [{"permission_code": "post_read"}]


@pytest.mark.asyncio
async def test_resolve_current_account_success_and_failures() -> None:
    with pytest.raises(HTTPException, match="no subject"):
        await auth.resolve_current_account(FakePool(AccountConnection(None)), "")
    with pytest.raises(HTTPException, match="no user_account"):
        await auth.resolve_current_account(FakePool(AccountConnection(None)), "missing")
    result = await auth.resolve_current_account(
        FakePool(AccountConnection({"user_account_id": "account-1", "display_name": "Analyst"})),
        "subject-1",
    )
    assert result.external_subject_id == "subject-1"
    assert result.corporate_entity_ids == frozenset({"entity-1"})
    assert result.has_permission("post_read")
    assert not result.has_permission("post_write")


@pytest.mark.asyncio
async def test_get_current_account_validates_subject_and_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = settings()
    monkeypatch.setattr(auth, "load_settings", lambda: cfg)
    monkeypatch.setattr(auth, "_decode_access_token", lambda *_args, **_kwargs: {})
    credentials = SimpleNamespace(credentials="token")
    with pytest.raises(HTTPException, match="no subject"):
        await auth.get_current_account(credentials, object())

    expected = auth.CurrentAccount("a", "s", "n", frozenset(), frozenset())
    monkeypatch.setattr(auth, "_decode_access_token", lambda *_args, **_kwargs: {"sub": "s"})

    async def resolve(pool, subject):
        assert subject == "s"
        return expected

    monkeypatch.setattr(auth, "resolve_current_account", resolve)
    assert await auth.get_current_account(credentials, object()) is expected


def test_scope_normalization_supports_string_list_and_rejects_other_types() -> None:
    assert mcp_auth._scopes_from_claim("a  b") == ["a", "b"]
    assert mcp_auth._scopes_from_claim(["a", "", 1, "b"]) == ["a", "b"]
    assert mcp_auth._scopes_from_claim(None) == []


@pytest.mark.asyncio
async def test_mcp_verifier_returns_subject_client_scope_and_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = settings()
    token, jwks = signed_token(audience=cfg.mcp_audience)
    monkeypatch.setattr(auth, "_jwks", lambda _: jwks)
    verified = await mcp_auth.KeycloakMcpTokenVerifier(cfg).verify_token(token)
    assert verified is not None
    assert verified.subject == "subject-1"
    assert verified.client_id == "codex-client"
    assert verified.scopes == ["openid", "lineageweave:ask"]
    assert verified.resource == cfg.mcp_audience


@pytest.mark.asyncio
async def test_mcp_verifier_returns_none_for_wrong_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = settings()
    token, jwks = signed_token(audience="https://other.example/mcp")
    monkeypatch.setattr(auth, "_jwks", lambda _: jwks)
    assert await mcp_auth.KeycloakMcpTokenVerifier(cfg).verify_token(token) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims",
    [
        {"sub": "", "azp": "client"},
        {"sub": "subject", "azp": ""},
        {"sub": "subject"},
    ],
)
async def test_verifier_rejects_missing_principal_components(
    monkeypatch: pytest.MonkeyPatch, claims
) -> None:
    monkeypatch.setattr(mcp_auth, "decode_access_token", lambda *_args, **_kwargs: claims)
    assert await mcp_auth.KeycloakMcpTokenVerifier(settings()).verify_token("token") is None


@pytest.mark.asyncio
async def test_verifier_accepts_client_id_array_scope_and_missing_exp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        mcp_auth,
        "decode_access_token",
        lambda *_args, **_kwargs: {
            "sub": "subject",
            "client_id": "client",
            "scope": ["a", "b"],
            "iss": "issuer",
            "aud": ["resource"],
            "exp": "not-a-number",
        },
    )
    token = await mcp_auth.KeycloakMcpTokenVerifier(settings()).verify_token("token")
    assert token is not None
    assert token.expires_at is None
    assert token.client_id == "client"


@pytest.mark.asyncio
async def test_verifier_converts_decode_http_error_to_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args, **_kwargs):
        raise HTTPException(401, "invalid")

    monkeypatch.setattr(mcp_auth, "decode_access_token", fail)
    assert await mcp_auth.KeycloakMcpTokenVerifier(settings()).verify_token("token") is None
