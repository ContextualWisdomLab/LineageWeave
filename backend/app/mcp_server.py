"""Authenticated Model Context Protocol endpoint for LineageWeave Global Ask.

The server implements the stateless MCP protocol revision 2026-07-28 over
Streamable HTTP. It exposes one read-only ``global_ask`` tool and reuses
LineageWeave's persisted authorization and evidence contracts instead of
forwarding the caller's bearer token to another service.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import asyncpg
import jwt
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from jwt.algorithms import RSAAlgorithm

from backend.app.activity_stream import create_valkey_client
from backend.app.auth import CurrentAccount
from backend.app.config import Settings, load_settings
from backend.app.db import create_pool
from backend.app.post_chat_ingestion import gather_global_chat_sources
from lineageweave.http_client import HttpClientError, get_json
from lineageweave.post_chat import (
    ContextualOrchestratorPostChatClient,
    cited_post_evidence,
    cited_post_summaries,
)

_PROTOCOL_VERSION = "2026-07-28"
_SERVER_NAME = "lineageweave"
_SERVER_VERSION = "2.18.0"
_TOOL_NAME = "global_ask"
_LOG = logging.getLogger("lineageweave.mcp")
_JWKS_CACHE: dict[str, dict[str, Any]] = {}

_META_PROTOCOL_VERSION = "io.modelcontextprotocol/protocolVersion"
_META_CLIENT_INFO = "io.modelcontextprotocol/clientInfo"
_META_CLIENT_CAPABILITIES = "io.modelcontextprotocol/clientCapabilities"
_META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"

_HEADER_MISMATCH = -32020
_UNSUPPORTED_PROTOCOL_VERSION = -32022
_SERVER_INFO = {"name": _SERVER_NAME, "version": _SERVER_VERSION}

_GLOBAL_ASK_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer_text": {"type": "string"},
        "cited_post_ids": {"type": "array", "items": {"type": "string"}},
        "cited_posts": {"type": "array", "items": {"type": "object"}},
        "cited_post_evidence": {"type": "array", "items": {"type": "object"}},
        "source_post_ids": {"type": "array", "items": {"type": "string"}},
        "next_action": {"type": ["string", "null"]},
    },
    "required": [
        "answer_text",
        "cited_post_ids",
        "cited_posts",
        "cited_post_evidence",
        "source_post_ids",
        "next_action",
    ],
    "additionalProperties": False,
}

_GLOBAL_ASK_TOOL: dict[str, Any] = {
    "name": _TOOL_NAME,
    "title": "LineageWeave Global Ask",
    "description": (
        "Ask a question over only the LineageWeave source posts and persisted "
        "business evidence the authenticated account is authorized to read. "
        "Returns source-grounded citations and never fabricates unavailable evidence."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "minLength": 1,
                "maxLength": 4000,
                "description": "Question to answer from authorized LineageWeave evidence.",
            }
        },
        "required": ["question"],
        "additionalProperties": False,
    },
    "outputSchema": _GLOBAL_ASK_OUTPUT_SCHEMA,
    "annotations": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


@dataclass(frozen=True)
class McpRuntimeSettings:
    """MCP-specific settings layered on shared LineageWeave settings."""

    resource_uri: str
    allowed_origins: frozenset[str]
    requests_per_minute: int


def load_mcp_settings() -> McpRuntimeSettings:
    """Load the canonical MCP resource and bounded transport policy."""
    resource_uri = os.environ.get(
        "LINEAGEWEAVE_MCP_RESOURCE_URI", "http://localhost:18421/mcp"
    ).strip()
    parsed = urlsplit(resource_uri)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.fragment or parsed.query:
        raise ValueError(
            "LINEAGEWEAVE_MCP_RESOURCE_URI must be an absolute http(s) URI without query or fragment"
        )
    loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not loopback:
        raise ValueError("LINEAGEWEAVE_MCP_RESOURCE_URI must use HTTPS outside loopback development")
    allowed_origins = frozenset(
        origin.strip()
        for origin in os.environ.get("LINEAGEWEAVE_MCP_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    )
    try:
        requests_per_minute = int(os.environ.get("LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE", "30"))
    except ValueError as exc:
        raise ValueError("LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE must be an integer") from exc
    if not 1 <= requests_per_minute <= 600:
        raise ValueError("LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE must be between 1 and 600")
    return McpRuntimeSettings(
        resource_uri=resource_uri,
        allowed_origins=allowed_origins,
        requests_per_minute=requests_per_minute,
    )


def _resource_metadata_url(mcp_settings: McpRuntimeSettings) -> str:
    """Return the canonical RFC 9728 metadata URL for the configured resource."""
    parsed = urlsplit(mcp_settings.resource_uri)
    path = parsed.path if parsed.path.startswith("/") else f"/{parsed.path}"
    return f"{parsed.scheme}://{parsed.netloc}/.well-known/oauth-protected-resource{path}"


def _validate_transport_target(request: Request, mcp_settings: McpRuntimeSettings) -> None:
    """Validate browser Origin and canonical Host to bound DNS-rebinding surface."""
    origin = request.headers.get("origin")
    if origin is not None and origin not in mcp_settings.allowed_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "MCP Origin is not allowed")
    canonical_host = urlsplit(mcp_settings.resource_uri).netloc.lower()
    request_host = request.headers.get("host", "").lower()
    if request_host and request_host != canonical_host:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "MCP Host does not match the configured resource")


def _mcp_jwks(settings: Settings) -> dict[str, Any]:
    """Fetch and cache the configured OIDC provider's JWKS."""
    cache_key = settings.oidc_issuer
    cached = _JWKS_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        if settings.oidc_jwks_uri_override:
            jwks_uri = settings.oidc_jwks_uri_override
        else:
            metadata = get_json(settings.oidc_discovery_uri, timeout=10)
            jwks_uri = metadata.get("jwks_uri")
            if not isinstance(jwks_uri, str) or not jwks_uri.strip():
                raise ValueError("OIDC discovery document has no jwks_uri")
        cached = get_json(jwks_uri, timeout=10)
    except (HttpClientError, OSError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "could not fetch the configured OIDC signing keys",
        ) from exc
    if not isinstance(cached, dict) or not isinstance(cached.get("keys"), list):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "OIDC JWKS has no key set")
    _JWKS_CACHE[cache_key] = cached
    return cached


def _mcp_signing_key(jwks: dict[str, Any], token: str):
    """Require a non-empty JWT ``kid`` and an exact RSA signing-key match."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid access-token header") from exc
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "access token must include a non-empty kid")
    for key in jwks.get("keys", []):
        if not isinstance(key, dict) or key.get("kid") != kid:
            continue
        if key.get("kty") not in (None, "RSA") or key.get("alg") not in (None, "RS256"):
            continue
        try:
            return RSAAlgorithm.from_jwk(json.dumps(key))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "matching JWKS key is invalid") from exc
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no JWKS key matched the access-token kid")


def _decode_mcp_access_token(
    token: str,
    settings: Settings,
    mcp_settings: McpRuntimeSettings,
) -> dict[str, Any]:
    """Validate signature, issuer, expiry and this MCP resource audience."""
    try:
        signing_key = _mcp_signing_key(_mcp_jwks(settings), token)
        claims = jwt.decode(
            token,
            key=signing_key,
            algorithms=["RS256"],
            issuer=settings.oidc_issuer,
            audience=mcp_settings.resource_uri,
            leeway=settings.oidc_clock_skew_seconds,
        )
    except HTTPException:
        raise
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid MCP access token") from exc
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MCP access token has no subject")
    return claims


async def _resolve_account(pool: asyncpg.Pool, subject: str) -> CurrentAccount:
    """Resolve authorization from LineageWeave DB state, never token attributes."""
    async with pool.acquire() as conn:
        account_row = await conn.fetchrow(
            "select user_account_id, display_name, preferred_locale "
            "from user_account where external_subject_id = $1",
            subject,
        )
        if account_row is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "token is valid but no LineageWeave account is provisioned for this subject",
            )
        entity_rows = await conn.fetch(
            "select corporate_entity_id from account_affiliation where user_account_id = $1",
            account_row["user_account_id"],
        )
        permission_rows = await conn.fetch(
            """
            select distinct rp.permission_code
              from account_role_assignment ara
              join role_permission rp on rp.access_role_id = ara.access_role_id
             where ara.user_account_id = $1
            """,
            account_row["user_account_id"],
        )
    account = CurrentAccount(
        user_account_id=str(account_row["user_account_id"]),
        external_subject_id=subject,
        display_name=account_row["display_name"],
        preferred_locale=account_row["preferred_locale"],
        corporate_entity_ids=frozenset(str(row["corporate_entity_id"]) for row in entity_rows),
        permission_codes=frozenset(str(row["permission_code"]) for row in permission_rows),
    )
    if not account.has_permission("post_read"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account lacks the post_read permission")
    return account


async def _authenticate(request: Request, pool: asyncpg.Pool) -> CurrentAccount:
    """Authenticate one MCP HTTP request and resolve its persisted account policy."""
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer access token required")
    claims = _decode_mcp_access_token(token.strip(), load_settings(), load_mcp_settings())
    return await _resolve_account(pool, str(claims["sub"]))


async def _check_rate_limit(client: redis.Redis, account_id: str, limit: int) -> None:
    """Apply a distributed fixed-window MCP rate limit using existing Valkey."""
    bucket = int(time.time() // 60)
    key = f"mcp:rate:{account_id}:{bucket}"
    script = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then redis.call('EXPIRE', KEYS[1], 120) end
    return count
    """
    count = int(await client.eval(script, 1, key))
    if count > limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "MCP tool rate limit exceeded")


def _can_see_post(account: CurrentAccount, post: Any) -> bool:
    """Match the product ABAC rule used by the browser Global Ask flow."""
    if post["visibility_code"] == "public":
        return True
    return str(post["corporate_entity_id"]) in account.corporate_entity_ids


def _post_chat_client(settings: Settings):
    """Build the same contextual-orchestrator-only chat channel as the product."""
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return None
    return ContextualOrchestratorPostChatClient(
        base_url=settings.orchestrator_base_url,
        api_key=settings.orchestrator_api_key,
    )


async def _global_ask(
    pool: asyncpg.Pool,
    account: CurrentAccount,
    question: str,
) -> dict[str, Any]:
    """Run Global Ask against only evidence visible to ``account``."""
    normalized_question = question.strip()
    if not normalized_question or len(normalized_question) > 4000:
        raise ValueError("question must contain between 1 and 4000 characters")
    client = _post_chat_client(load_settings())
    if client is None:
        raise RuntimeError("Global Ask is unavailable because contextual-orchestrator is not configured")
    async with pool.acquire() as conn:
        sources = await gather_global_chat_sources(
            conn,
            lambda row: _can_see_post(account, row),
            account.corporate_entity_ids,
            question=normalized_question,
        )
    if not sources:
        return {
            "answer_text": "",
            "cited_post_ids": [],
            "cited_posts": [],
            "cited_post_evidence": [],
            "source_post_ids": [],
            "next_action": "No authorized source posts are available for this question.",
        }
    try:
        answer = await asyncio.to_thread(client.answer, normalized_question, sources)
    except (HttpClientError, KeyError, OSError, ValueError) as exc:
        raise RuntimeError("contextual-orchestrator returned no complete evidence object") from exc
    cited_ids = list(answer.cited_post_ids)
    result = {
        "answer_text": answer.answer_text,
        "cited_post_ids": cited_ids,
        "cited_posts": cited_post_summaries(sources, cited_ids),
        "cited_post_evidence": cited_post_evidence(sources, cited_ids),
        "source_post_ids": [source.post_id for source in sources],
        "next_action": None,
    }
    _LOG.info(
        "mcp_global_ask account=%s sources=%d citations=%d question_chars=%d",
        account.user_account_id,
        len(result["source_post_ids"]),
        len(cited_ids),
        len(normalized_question),
    )
    return result


def _jsonrpc_result(request_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Build a complete 2026-era result with server identity metadata."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            **payload,
            "resultType": "complete",
            "_meta": {_META_SERVER_INFO: _SERVER_INFO},
        },
    }


def _jsonrpc_error(
    request_id: Any,
    code: int,
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-RPC error response."""
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _unsupported_version_error(request_id: Any, requested: Any) -> dict[str, Any]:
    """Build the final 2026 UnsupportedProtocolVersion wire shape."""
    return _jsonrpc_error(
        request_id,
        _UNSUPPORTED_PROTOCOL_VERSION,
        "Unsupported protocol version",
        data={"supported": [_PROTOCOL_VERSION], "requested": str(requested or "")},
    )


def _request_envelope(message: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate the stateless per-request MCP metadata envelope."""
    params = message.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    meta = params.get("_meta")
    if not isinstance(meta, dict):
        raise ValueError("params._meta is required")
    protocol_version = meta.get(_META_PROTOCOL_VERSION)
    if protocol_version != _PROTOCOL_VERSION:
        raise RuntimeError(str(protocol_version or ""))
    client_capabilities = meta.get(_META_CLIENT_CAPABILITIES)
    if not isinstance(client_capabilities, dict):
        raise ValueError("clientCapabilities must be an object")
    client_info = meta.get(_META_CLIENT_INFO)
    if client_info is not None:
        if not isinstance(client_info, dict):
            raise ValueError("clientInfo must be an object when present")
        if not isinstance(client_info.get("name"), str) or not isinstance(client_info.get("version"), str):
            raise ValueError("clientInfo name and version must be strings")
    return params, meta


def _expected_mcp_name(method: Any, params: dict[str, Any]) -> str | None:
    """Return the standardized Mcp-Name source for name-bearing methods."""
    if method == "tools/call":
        name = params.get("name")
        return name if isinstance(name, str) else None
    if method in {"resources/read", "prompts/get"}:
        source = params.get("uri") if method == "resources/read" else params.get("name")
        return source if isinstance(source, str) else None
    return None


def _validate_transport_headers(request: Request, message: dict[str, Any]) -> JSONResponse | None:
    """Validate 2026 protocol/version/method/name headers against the body."""
    request_id = message.get("id")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}
    meta = params.get("_meta") if isinstance(params, dict) else None
    body_version = meta.get(_META_PROTOCOL_VERSION) if isinstance(meta, dict) else None
    header_version = request.headers.get("mcp-protocol-version")

    if header_version != body_version:
        return JSONResponse(
            _jsonrpc_error(request_id, _HEADER_MISMATCH, "MCP-Protocol-Version header mismatch"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if header_version != _PROTOCOL_VERSION:
        return JSONResponse(
            _unsupported_version_error(request_id, header_version),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    method = message.get("method")
    method_header = request.headers.get("mcp-method")
    if not isinstance(method, str) or method_header != method:
        return JSONResponse(
            _jsonrpc_error(request_id, _HEADER_MISMATCH, "Mcp-Method header mismatch"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    expected_name = _expected_mcp_name(method, params)
    name_header = request.headers.get("mcp-name")
    if expected_name is None:
        if name_header is not None:
            return JSONResponse(
                _jsonrpc_error(request_id, _HEADER_MISMATCH, "unexpected Mcp-Name header"),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    elif name_header != expected_name:
        return JSONResponse(
            _jsonrpc_error(request_id, _HEADER_MISMATCH, "Mcp-Name header mismatch"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return None


async def _dispatch_message(
    message: Any,
    pool: asyncpg.Pool,
    valkey: redis.Redis,
    account: CurrentAccount,
    mcp_settings: McpRuntimeSettings,
) -> tuple[dict[str, Any] | None, int]:
    """Dispatch one stateless, non-batched JSON-RPC 2.0 MCP message."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        request_id = message.get("id") if isinstance(message, dict) else None
        return _jsonrpc_error(request_id, -32600, "Invalid Request"), status.HTTP_200_OK
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None, status.HTTP_202_ACCEPTED
    try:
        params, _meta = _request_envelope(message)
    except RuntimeError as exc:
        return _unsupported_version_error(request_id, str(exc)), status.HTTP_400_BAD_REQUEST
    except ValueError as exc:
        return _jsonrpc_error(request_id, -32602, str(exc)), status.HTTP_200_OK

    if method == "server/discover":
        return (
            _jsonrpc_result(
                request_id,
                {
                    "supportedVersions": [_PROTOCOL_VERSION],
                    "capabilities": {"tools": {"listChanged": False}},
                    "instructions": "Use global_ask only for source-grounded LineageWeave questions.",
                    "ttlMs": 0,
                    "cacheScope": "private",
                },
            ),
            status.HTTP_200_OK,
        )
    if method == "ping":
        return _jsonrpc_result(request_id, {}), status.HTTP_200_OK
    if method == "tools/list":
        return (
            _jsonrpc_result(
                request_id,
                {"tools": [_GLOBAL_ASK_TOOL], "ttlMs": 0, "cacheScope": "private"},
            ),
            status.HTTP_200_OK,
        )
    if method == "tools/call":
        if params.get("name") != _TOOL_NAME:
            return _jsonrpc_error(request_id, -32602, "Unknown tool"), status.HTTP_200_OK
        arguments = params.get("arguments")
        if not isinstance(arguments, dict) or set(arguments) != {"question"}:
            return (
                _jsonrpc_error(request_id, -32602, "global_ask requires only the question argument"),
                status.HTTP_200_OK,
            )
        question = arguments.get("question")
        if not isinstance(question, str) or not question.strip() or len(question.strip()) > 4000:
            return (
                _jsonrpc_error(
                    request_id,
                    -32602,
                    "question must contain between 1 and 4000 characters",
                ),
                status.HTTP_200_OK,
            )
        await _check_rate_limit(valkey, account.user_account_id, mcp_settings.requests_per_minute)
        try:
            structured = await _global_ask(pool, account, question)
        except RuntimeError as exc:
            return (
                _jsonrpc_result(
                    request_id,
                    {"content": [{"type": "text", "text": str(exc)}], "isError": True},
                ),
                status.HTTP_200_OK,
            )
        text = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
        return (
            _jsonrpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": text}],
                    "structuredContent": structured,
                    "isError": False,
                },
            ),
            status.HTTP_200_OK,
        )
    return _jsonrpc_error(request_id, -32601, f"Method not found: {method}"), status.HTTP_404_NOT_FOUND


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create shared DB and Valkey clients; MCP protocol state stays per request."""
    shared = load_settings()
    app.state.pool = await create_pool(shared.database_url)
    app.state.valkey = create_valkey_client(shared.valkey_url)
    try:
        yield
    finally:
        await app.state.pool.close()
        await app.state.valkey.aclose()


mcp_app = FastAPI(title="LineageWeave MCP", lifespan=lifespan)


@mcp_app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Process liveness without leaking authentication or evidence state."""
    return {"status": "ok"}


@mcp_app.get("/.well-known/oauth-protected-resource")
@mcp_app.get("/.well-known/oauth-protected-resource/mcp")
async def protected_resource_metadata() -> dict[str, Any]:
    """Publish RFC 9728 resource metadata for MCP client discovery."""
    settings = load_settings()
    mcp_settings = load_mcp_settings()
    return {
        "resource": mcp_settings.resource_uri,
        "authorization_servers": [settings.oidc_issuer],
        "bearer_methods_supported": ["header"],
    }


@mcp_app.get("/mcp")
async def mcp_get() -> Response:
    """No subscription stream is exposed in this read-only first slice."""
    return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, headers={"Allow": "POST"})


@mcp_app.post("/mcp")
async def mcp_post(request: Request) -> Response:
    """Handle one authenticated MCP 2026-07-28 Streamable HTTP request."""
    mcp_settings = load_mcp_settings()
    _validate_transport_target(request, mcp_settings)
    try:
        message = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return JSONResponse(_jsonrpc_error(None, -32700, "Parse error"), status_code=200)
    if isinstance(message, list):
        return JSONResponse(
            _jsonrpc_error(None, -32600, "JSON-RPC batching is not supported"),
            status_code=200,
        )
    if not isinstance(message, dict):
        return JSONResponse(_jsonrpc_error(None, -32600, "Invalid Request"), status_code=200)
    header_error = _validate_transport_headers(request, message)
    if header_error is not None:
        return header_error
    try:
        account = await _authenticate(request, request.app.state.pool)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return JSONResponse(
                {"detail": exc.detail},
                status_code=exc.status_code,
                headers={
                    "WWW-Authenticate": (
                        'Bearer resource_metadata="' + _resource_metadata_url(mcp_settings) + '"'
                    )
                },
            )
        raise
    response_message, http_status = await _dispatch_message(
        message,
        request.app.state.pool,
        request.app.state.valkey,
        account,
        mcp_settings,
    )
    if response_message is None:
        return Response(status_code=http_status)
    return JSONResponse(response_message, status_code=http_status)


app = mcp_app
