"""Authenticated Streamable HTTP MCP adapter for durable Global Ask."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context
from mcp.server.transport_security import (
    TransportSecurityMiddleware,
    TransportSecuritySettings,
)
from mcp.shared.exceptions import MCPError
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.activity_stream import create_valkey_client
from backend.app.auth import CurrentAccount, resolve_current_account
from backend.app.config import Settings, load_settings
from backend.app.db import create_pool
from backend.app.global_ask_service import (
    read_global_ask_job as read_global_ask_job_service,
)
from backend.app.global_ask_service import (
    submit_global_ask as submit_global_ask_service,
)
from backend.app.mcp_admission import BoundedRequestBodyApp
from backend.app.mcp_auth import KeyverseMcpTokenVerifier
from backend.app.mcp_rate_limit import (
    McpRateLimiterUnavailable,
    McpRateLimitExceeded,
    ValkeyMcpRateLimiter,
)
from lineageweave.post_chat import (
    ContextualOrchestratorPostChatClient,
    NullPostChatClient,
)


@dataclass
class McpAppContext:
    """Long-lived dependencies shared by MCP tool calls."""

    pool: Any
    valkey: Any
    limiter: ValkeyMcpRateLimiter
    service_available: bool
    settings: Settings


class PreAuthTransportSecurityApp:
    """Reject hostile Host and Origin metadata before OAuth processing."""

    def __init__(self, app: ASGIApp, settings: TransportSecuritySettings) -> None:
        """Wrap an ASGI app with the SDK transport validator."""
        self._app = app
        self._security = TransportSecurityMiddleware(settings)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Validate HTTP transport metadata and pass non-HTTP traffic through."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        rejection = await self._security.validate_request(
            request, is_post=request.method == "POST"
        )
        if rejection is not None:
            if request.headers.get("origin") is not None:
                rejection.headers.add_vary_header("Origin")
            await rejection(scope, receive, send)
            return
        await self._app(scope, receive, send)


class McpRetryAfterHeaderApp:
    """Expose a bounded retry delay only for exhausted authenticated quota."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the SDK response serializer."""
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Add Retry-After from the serialized quota error before headers commit."""
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self._app(scope, receive, send)
            return
        response_start: Message | None = None

        async def send_with_retry(message: Message) -> None:
            """Hold response start until the first MCP event reveals its status."""
            nonlocal response_start
            if message.get("type") == "http.response.start":
                response_start = message
                return
            if response_start is not None:
                retry_after = _quota_retry_after(message.get("body", b""))
                if retry_after is not None:
                    headers = [
                        (name, value)
                        for name, value in response_start.get("headers", [])
                        if name.lower() != b"retry-after"
                    ]
                    headers.append(
                        (b"retry-after", str(retry_after).encode("ascii"))
                    )
                    response_start = {**response_start, "headers": headers}
                await send(response_start)
                response_start = None
            await send(message)

        await self._app(scope, receive, send_with_retry)


def _quota_retry_after(body: bytes) -> int | None:
    """Read the bounded retry delay from an exact MCP JSON-RPC error event."""
    for line in body.splitlines():
        if not line.startswith(b"data:"):
            continue
        try:
            payload = json.loads(line.removeprefix(b"data:").strip())
            error = payload["error"]
            retry_after = error["data"]["retry_after_seconds"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        if error.get("code") == -31929 and type(retry_after) is int and retry_after > 0:
            return retry_after
    return None


def _validate_mcp_settings(settings: Settings) -> tuple[int, int]:
    """Require exact origins and measured deployment quota parameters."""
    if not settings.mcp_audience.strip():
        raise ValueError("MCP_AUDIENCE must name the exact MCP resource")
    for origin in settings.mcp_allowed_origins:
        parsed = urlsplit(origin)
        if (
            origin in {"*", "null"}
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "MCP_ALLOWED_ORIGINS entries must be exact HTTP(S) origins"
            )
    if (
        settings.mcp_rate_limit_requests is None
        or settings.mcp_rate_limit_window_seconds is None
    ):
        raise ValueError(
            "MCP_RATE_LIMIT_REQUESTS and MCP_RATE_LIMIT_WINDOW_SECONDS must be set from measured capacity"
        )
    return settings.mcp_rate_limit_requests, settings.mcp_rate_limit_window_seconds


PoolFactory = Callable[[str], Awaitable[Any]]
ValkeyFactory = Callable[[str], Any]
LimiterFactory = Callable[[Any, int, int], ValkeyMcpRateLimiter]
AccountResolver = Callable[[Any, dict, Settings], Awaitable[CurrentAccount]]
AccessTokenProvider = Callable[[], AccessToken | None]


def _build_limiter(client: Any, requests: int, window: int) -> ValkeyMcpRateLimiter:
    """Build the production shared limiter from validated inputs."""
    return ValkeyMcpRateLimiter(client, request_limit=requests, window_seconds=window)


async def _account(
    ctx: Context[McpAppContext, Any],
    *,
    access_token_provider: AccessTokenProvider,
    account_resolver: AccountResolver,
) -> CurrentAccount:
    """Resolve the authenticated token to one provisioned database account."""
    token = access_token_provider()
    if token is None or not token.subject or not isinstance(token.claims, dict):
        raise PermissionError("authenticated MCP principal is unavailable")
    dependencies = ctx.request_context.lifespan_context
    account = await account_resolver(
        dependencies.pool, token.claims, dependencies.settings
    )
    if not account.has_permission("post_read"):
        raise PermissionError("post_read permission required")
    try:
        await dependencies.limiter.consume(account.user_account_id)
    except McpRateLimitExceeded as exc:
        raise MCPError(
            -31929,
            "mcp_rate_limit_exceeded",
            {"retry_after_seconds": exc.retry_after_seconds},
        ) from exc
    except McpRateLimiterUnavailable as exc:
        raise MCPError(-31930, "mcp_rate_limiter_unavailable") from exc
    return account


def build_mcp_server(
    settings: Settings | None = None,
    *,
    pool_factory: PoolFactory = create_pool,
    valkey_factory: ValkeyFactory = create_valkey_client,
    limiter_factory: LimiterFactory = _build_limiter,
    token_verifier: TokenVerifier | None = None,
    account_resolver: AccountResolver = resolve_current_account,
    access_token_provider: AccessTokenProvider = get_access_token,
) -> MCPServer[McpAppContext]:
    """Build the authenticated MCP server over the current durable Ask contract."""
    resolved = settings or load_settings()
    request_limit, window_seconds = _validate_mcp_settings(resolved)

    @asynccontextmanager
    async def lifespan(_: MCPServer) -> AsyncIterator[McpAppContext]:
        """Open and close process-wide database and quota clients."""
        pool = await pool_factory(resolved.database_url)
        valkey = valkey_factory(resolved.valkey_url)
        limiter = limiter_factory(valkey, request_limit, window_seconds)
        chat_client = (
            ContextualOrchestratorPostChatClient(
                base_url=resolved.orchestrator_base_url,
                api_key=resolved.orchestrator_api_key,
            )
            if resolved.orchestrator_base_url and resolved.orchestrator_api_key
            else NullPostChatClient()
        )
        try:
            yield McpAppContext(pool, valkey, limiter, chat_client.available, resolved)
        finally:
            try:
                await limiter.close()
            finally:
                await pool.close()

    server = MCPServer(
        "lineageweave",
        title="LineageWeave",
        description="Authenticated provenance-bearing lineage intelligence.",
        version="2.19.0",
        lifespan=lifespan,
        token_verifier=token_verifier or KeyverseMcpTokenVerifier(resolved),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(resolved.oidc_issuer),
            resource_server_url=AnyHttpUrl(resolved.mcp_resource_url),
            required_scopes=resolved.mcp_required_scopes,
        ),
    )

    @server.tool(
        title="Submit Global Ask",
        description="Queue a question against the caller's authorized LineageWeave evidence.",
        annotations=ToolAnnotations(
            read_only_hint=False, idempotent_hint=False, open_world_hint=True
        ),
    )
    async def submit_global_ask(
        question: str,
        ctx: Context[McpAppContext, Any],
        verify_external: bool = False,
        knowledge_cutoff: str | None = None,
    ) -> dict[str, Any]:
        """Queue one current-contract Global Ask job without blocking transport."""
        dependencies = ctx.request_context.lifespan_context
        account = await _account(
            ctx,
            access_token_provider=access_token_provider,
            account_resolver=account_resolver,
        )
        return await submit_global_ask_service(
            pool=dependencies.pool,
            valkey=dependencies.valkey,
            account=account,
            question=question,
            verify_external=verify_external,
            knowledge_cutoff=knowledge_cutoff,
            service_available=dependencies.service_available,
        )

    @server.tool(
        title="Read Global Ask Job",
        description="Read a queued Global Ask job owned by the authenticated caller.",
        annotations=ToolAnnotations(
            read_only_hint=True, idempotent_hint=True, open_world_hint=False
        ),
    )
    async def read_global_ask_job(
        ask_job_id: str, ctx: Context[McpAppContext, Any]
    ) -> dict[str, Any]:
        """Read one current-contract Global Ask job and its persisted answer."""
        account = await _account(
            ctx,
            access_token_provider=access_token_provider,
            account_resolver=account_resolver,
        )
        try:
            parsed_job_id = UUID(ask_job_id)
        except ValueError as exc:
            raise ValueError("ask_job_id must be a UUID") from exc
        return await read_global_ask_job_service(
            pool=ctx.request_context.lifespan_context.pool,
            account=account,
            ask_job_id=parsed_job_id,
        )

    return server


def build_mcp_http_app(server: MCPServer[McpAppContext], settings: Settings) -> ASGIApp:
    """Build exact-origin, byte-bounded Streamable HTTP outside OAuth."""
    _validate_mcp_settings(settings)
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.mcp_allowed_hosts,
        allowed_origins=settings.mcp_allowed_origins,
    )
    sdk_app = server.streamable_http_app(transport_security=security)
    cors_app = CORSMiddleware(
        McpRetryAfterHeaderApp(sdk_app),
        allow_origins=settings.mcp_allowed_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "Last-Event-ID",
            "MCP-Protocol-Version",
            "Mcp-Session-Id",
        ],
        expose_headers=["MCP-Protocol-Version", "Mcp-Session-Id", "WWW-Authenticate"],
        allow_credentials=False,
    )
    return PreAuthTransportSecurityApp(
        BoundedRequestBodyApp(cors_app, maximum_bytes=settings.mcp_max_request_bytes),
        security,
    )


_settings = load_settings()
mcp = build_mcp_server(_settings)
app = build_mcp_http_app(mcp, _settings)
