"""Authenticated Model Context Protocol endpoint for LineageWeave Global Ask.

This module is deliberately separate from the browser-facing FastAPI app.
It exposes one read-only MCP tool, ``global_ask``, over Streamable HTTP and
reuses LineageWeave's persisted authorization and evidence contracts instead
of forwarding the caller's bearer token to another service.

The HTTP authorization boundary follows MCP protocol revision 2025-06-18:
resource metadata advertises the authorization server, access tokens must be
bound to this MCP resource, and browser ``Origin`` values are allow-listed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import asyncpg
import jwt
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from jwt.algorithms import RSAAlgorithm

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

_PROTOCOL_VERSION = "2025-06-18"
_SERVER_NAME = "lineageweave"
_SERVER_VERSION = "2.18.0"
_TOOL_NAME = "global_ask"
_LOG = logging.getLogger("lineageweave.mcp")
_JWKS_CACHE: dict[str, dict[str, Any]] = {}
_RATE_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LOCK = asyncio.Lock()

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
    """MCP-specific settings layered on the shared LineageWeave settings."""

    resource_uri: str
    allowed_origins: frozenset[str]
    requests_per_minute: int


def load_mcp_settings() -> McpRuntimeSettings:
    """Load the canonical MCP resource and bounded transport policy."""
    resource_uri = os.environ.get(
        "LINEAGEWEAVE_MCP_RESOURCE_URI", "http://localhost:18421/mcp"
    ).strip()
    if not resource_uri.startswith(("http://", "https://")) or "#" in resource_uri:
        raise ValueError("LINEAGEWEAVE_MCP_RESOURCE_URI must be an absolute http(s) URI without a fragment")
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


def _resource_metadata_url(request: Request) -> str:
    """Return the RFC 9728 metadata URL advertised in 401 challenges."""
    return str(request.base_url).rstrip("/") + "/.well-known/oauth-protected-resource/mcp"


def _validate_origin(request: Request, mcp_settings: McpRuntimeSettings) -> None:
    """Reject browser origins not explicitly authorized for this MCP server."""
    origin = request.headers.get("origin")
    if origin is None:
        return
    if origin not in mcp_settings.allowed_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "MCP Origin is not allowed")


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


async def _check_rate_limit(account_id: str, limit: int) -> None:
    """Bound MCP tool execution per process without storing question text."""
    now = time.monotonic()
    cutoff = now - 60.0
    async with _RATE_LOCK:
        window = _RATE_WINDOWS[account_id]
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "MCP tool rate limit exceeded")
        window.append(now)


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


def _jsonrpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


async def _dispatch_message(
    message: Any,
    pool: asyncpg.Pool,
    account: CurrentAccount,
    mcp_settings: McpRuntimeSettings,
) -> dict[str, Any] | None:
    """Dispatch one non-batched JSON-RPC 2.0 MCP message."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _jsonrpc_error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid Request")
    if isinstance(message, list):
        return _jsonrpc_error(None, -32600, "JSON-RPC batching is not supported")
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        if method == "notifications/initialized":
            return None
        return None
    if method == "initialize":
        params = message.get("params") or {}
        requested_version = params.get("protocolVersion") if isinstance(params, dict) else None
        if requested_version != _PROTOCOL_VERSION:
            return _jsonrpc_error(request_id, -32602, f"Unsupported protocolVersion: {requested_version!r}")
        return _jsonrpc_result(
            request_id,
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": _SERVER_NAME, "version": _SERVER_VERSION},
                "instructions": "Use global_ask only for source-grounded LineageWeave questions.",
            },
        )
    if method == "ping":
        return _jsonrpc_result(request_id, {})
    if method == "tools/list":
        return _jsonrpc_result(request_id, {"tools": [_GLOBAL_ASK_TOOL]})
    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, dict) or params.get("name") != _TOOL_NAME:
            return _jsonrpc_error(request_id, -32602, "Unknown tool")
        arguments = params.get("arguments")
        if not isinstance(arguments, dict) or set(arguments) != {"question"}:
            return _jsonrpc_error(request_id, -32602, "global_ask requires only the question argument")
        question = arguments.get("question")
        if not isinstance(question, str) or not question.strip() or len(question.strip()) > 4000:
            return _jsonrpc_error(request_id, -32602, "question must contain between 1 and 4000 characters")
        await _check_rate_limit(account.user_account_id, mcp_settings.requests_per_minute)
        try:
            structured = await _global_ask(pool, account, question)
        except RuntimeError as exc:
            return _jsonrpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
        text = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
        return _jsonrpc_result(
            request_id,
            {
                "content": [{"type": "text", "text": text}],
                "structuredContent": structured,
                "isError": False,
            },
        )
    return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create only the database pool needed by the MCP resource server."""
    app.state.pool = await create_pool(load_settings().database_url)
    try:
        yield
    finally:
        await app.state.pool.close()


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
    """This first slice is non-streaming; GET explicitly declines SSE."""
    return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, headers={"Allow": "POST"})


@mcp_app.post("/mcp")
async def mcp_post(request: Request) -> Response:
    """Handle one authenticated Streamable-HTTP MCP JSON-RPC message."""
    mcp_settings = load_mcp_settings()
    _validate_origin(request, mcp_settings)
    try:
        account = await _authenticate(request, request.app.state.pool)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return JSONResponse(
                {"detail": exc.detail},
                status_code=exc.status_code,
                headers={
                    "WWW-Authenticate": (
                        'Bearer resource_metadata="' + _resource_metadata_url(request) + '"'
                    )
                },
            )
        raise
    protocol_header = request.headers.get("mcp-protocol-version")
    if protocol_header is not None and protocol_header != _PROTOCOL_VERSION:
        return JSONResponse(
            {"detail": "Unsupported MCP-Protocol-Version"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        message = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return JSONResponse(_jsonrpc_error(None, -32700, "Parse error"), status_code=200)
    if isinstance(message, list):
        return JSONResponse(_jsonrpc_error(None, -32600, "JSON-RPC batching is not supported"), status_code=200)
    response_message = await _dispatch_message(
        message,
        request.app.state.pool,
        account,
        mcp_settings,
    )
    if response_message is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return JSONResponse(response_message)


app = mcp_app
