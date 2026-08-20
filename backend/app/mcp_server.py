"""Authenticated Streamable HTTP MCP server exposing read-only Global Ask."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import Any

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context
from mcp.server.transport_security import (
    TransportSecurityMiddleware,
    TransportSecuritySettings,
)
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl, BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.app.auth import CurrentAccount, resolve_current_account
from backend.app.config import Settings, load_settings
from backend.app.db import create_pool
from backend.app.global_ask import GlobalAskAnswer, answer_global_question
from backend.app.global_ask_verification import (
    STATUS_NOT_REQUESTED,
    ExternalVerificationResult,
    GlobalAskExternalVerifier,
    NullGlobalAskExternalVerifier,
    SearxngOrchestratorGlobalAskVerifier,
)
from backend.app.mcp_admission import BoundedRequestBodyApp
from backend.app.mcp_auth import KeycloakMcpTokenVerifier
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.post_chat import ContextualOrchestratorPostChatClient, NullPostChatClient, PostChatClient


class GlobalAskResult(BaseModel):
    """Structured MCP response separating internal citations from web verification."""

    answer_text: str
    anchor_post_id: str
    cited_post_ids: list[str] = Field(default_factory=list)
    cited_posts: list[dict[str, str]] = Field(default_factory=list)
    source_post_ids: list[str] = Field(default_factory=list)
    external_verification_status: str
    external_evidence_urls: list[str] = Field(default_factory=list)
    external_verification_rationale: str | None = None


@dataclass
class McpAppContext:
    """Long-lived dependencies shared by every MCP tool call."""

    pool: Any
    chat_client: PostChatClient
    vision_client: Any
    external_verifier: GlobalAskExternalVerifier


class PreAuthTransportSecurityApp:
    """Apply MCP Host, Origin, and POST content-type checks before OAuth.

    MCP SDK 2.0 assembles its OAuth resource-server middleware outside the
    Streamable HTTP transport. Calling ``streamable_http_app`` directly can
    therefore challenge an unauthenticated hostile Host before the transport's
    DNS-rebinding validator runs. This outer ASGI boundary reuses the SDK's own
    validator and rejects invalid transport metadata before any token verifier,
    database resolver, or Global Ask dependency is invoked.
    """

    def __init__(self, app: ASGIApp, settings: TransportSecuritySettings) -> None:
        """Wrap ``app`` with the SDK's transport validator as the outer boundary."""
        self._app = app
        self._transport_security = TransportSecurityMiddleware(settings)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Validate HTTP transport metadata, then delegate non-hostile requests."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        rejection = await self._transport_security.validate_request(
            request,
            is_post=request.method == "POST",
        )
        if rejection is not None:
            if request.headers.get("origin") is not None:
                rejection.headers.add_vary_header("Origin")
            await rejection(scope, receive, send)
            return
        await self._app(scope, receive, send)


PoolFactory = Callable[[str], Awaitable[Any]]
AccountResolver = Callable[[Any, str], Awaitable[CurrentAccount]]
Answerer = Callable[..., Awaitable[GlobalAskAnswer]]
AccessTokenProvider = Callable[[], AccessToken | None]


def _chat_client(settings: Settings) -> PostChatClient:
    """Build the existing contextual-orchestrator chat channel or its null client."""
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostChatClient()
    return ContextualOrchestratorPostChatClient(
        base_url=settings.orchestrator_base_url,
        api_key=settings.orchestrator_api_key,
    )


def _external_verifier(settings: Settings) -> GlobalAskExternalVerifier:
    """Build external corroboration only when both search and judge channels exist."""
    if not (
        settings.searxng_base_url
        and settings.orchestrator_base_url
        and settings.orchestrator_api_key
    ):
        return NullGlobalAskExternalVerifier()
    return SearxngOrchestratorGlobalAskVerifier(
        settings.searxng_base_url,
        settings.orchestrator_base_url,
        settings.orchestrator_api_key,
    )


def build_mcp_server(
    settings: Settings | None = None,
    *,
    pool_factory: PoolFactory = create_pool,
    token_verifier: TokenVerifier | None = None,
    account_resolver: AccountResolver = resolve_current_account,
    answerer: Answerer = answer_global_question,
    access_token_provider: AccessTokenProvider = get_access_token,
    external_verifier: GlobalAskExternalVerifier | None = None,
) -> MCPServer[McpAppContext]:
    """Build a testable OAuth resource server with one read-only Global Ask tool."""
    resolved_settings = settings or load_settings()
    resolved_external_verifier = external_verifier or _external_verifier(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: MCPServer) -> AsyncIterator[McpAppContext]:
        """Open and close the MCP process-wide database and client context."""
        pool = await pool_factory(resolved_settings.database_url)
        try:
            yield McpAppContext(
                pool=pool,
                chat_client=_chat_client(resolved_settings),
                vision_client=orchestrator_vision_client(
                    resolved_settings.orchestrator_base_url,
                    resolved_settings.orchestrator_api_key,
                    resolved_settings.vision_model,
                ),
                external_verifier=resolved_external_verifier,
            )
        finally:
            await pool.close()

    mcp = MCPServer(
        "lineageweave",
        title="LineageWeave",
        description="Authenticated evidence-grounded lineage intelligence.",
        instructions=(
            "Use global_ask to answer from the authenticated caller's authorized "
            "LineageWeave source-post and event-lineage evidence. The answer and its "
            "post citations remain database-authorized internal evidence. Set "
            "verify_external=true only when the caller explicitly permits sending the "
            "question to the configured Searxng open-web search lane. The internal "
            "answer body is never used as a web-search query. External verification is "
            "reported separately and external URLs never become LineageWeave post "
            "authority. Treat insufficient, unavailable, and not_requested as unresolved, "
            "not as support."
        ),
        version="1.0.0",
        lifespan=lifespan,
        token_verifier=token_verifier or KeycloakMcpTokenVerifier(resolved_settings),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(resolved_settings.keycloak_issuer),
            resource_server_url=AnyHttpUrl(resolved_settings.mcp_resource_url),
            required_scopes=resolved_settings.mcp_required_scopes,
        ),
    )

    @mcp.tool(
        title="Global Ask",
        description=(
            "Answer from authorized LineageWeave source posts and Event Lineage. "
            "Optionally, with verify_external=true, send the caller's question to the "
            "configured Searxng open-web lane and separately classify the answer against "
            "bounded retrieved evidence."
        ),
        annotations=ToolAnnotations(
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=True,
        ),
    )
    async def global_ask(
        question: str,
        ctx: Context[McpAppContext, Any],
        verify_external: bool = False,
    ) -> GlobalAskResult:
        """Run source-grounded Global Ask with optional explicit open-web verification."""
        token = access_token_provider()
        if token is None or not token.subject:
            raise PermissionError("authenticated MCP principal is unavailable")
        dependencies = ctx.request_context.lifespan_context
        account = await account_resolver(dependencies.pool, token.subject)
        result = await answerer(
            dependencies.pool,
            account,
            dependencies.chat_client,
            question,
            vision_client=dependencies.vision_client,
        )
        if verify_external:
            verification = await asyncio.to_thread(
                dependencies.external_verifier.verify,
                question,
                result.answer_text,
            )
        else:
            verification = ExternalVerificationResult(status_code=STATUS_NOT_REQUESTED)
        return GlobalAskResult(
            **asdict(result),
            external_verification_status=verification.status_code,
            external_evidence_urls=list(verification.evidence_urls),
            external_verification_rationale=verification.rationale,
        )

    return mcp


def build_mcp_http_app(
    server: MCPServer[McpAppContext],
    settings: Settings,
) -> ASGIApp:
    """Build exact-origin, byte-bounded Streamable HTTP outside OAuth."""
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.mcp_allowed_hosts,
        allowed_origins=settings.mcp_allowed_origins,
    )
    sdk_app = server.streamable_http_app(transport_security=transport_security)
    cors_app = CORSMiddleware(
        sdk_app,
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
        expose_headers=[
            "MCP-Protocol-Version",
            "Mcp-Session-Id",
            "WWW-Authenticate",
        ],
        allow_credentials=False,
        max_age=600,
    )
    bounded_app = BoundedRequestBodyApp(
        cors_app,
        maximum_bytes=settings.mcp_max_request_bytes,
    )
    return PreAuthTransportSecurityApp(bounded_app, transport_security)


_settings = load_settings()
mcp = build_mcp_server(_settings)
app = build_mcp_http_app(mcp, _settings)
