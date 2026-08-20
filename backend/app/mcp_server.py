"""Authenticated Streamable HTTP MCP server exposing read-only Global Ask."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import Annotated, Any, Literal

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
from mcp.types import CallToolResult, ErrorData, ImageContent, TextContent, ToolAnnotations
from pydantic import AnyHttpUrl, BaseModel, Field
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.app.activity_stream import create_valkey_client
from backend.app.auth import CurrentAccount, resolve_current_account
from backend.app.config import Settings, load_settings
from backend.app.db import create_pool
from backend.app.global_ask import (
    GlobalAskAnswer,
    GlobalAskForbiddenError,
    answer_global_question,
)
from backend.app.global_ask_verification import (
    STATUS_NOT_REQUESTED,
    ExternalVerificationResult,
    GlobalAskExternalVerifier,
    NullGlobalAskExternalVerifier,
    SearxngOrchestratorGlobalAskVerifier,
)
from backend.app.mcp_auth import KeycloakMcpTokenVerifier
from backend.app.mcp_rate_limit import (
    GLOBAL_ASK_RATE_LIMIT_ERROR_CODE,
    GLOBAL_ASK_RATE_LIMIT_UNAVAILABLE_ERROR_CODE,
    GlobalAskRateLimiter,
    GlobalAskRateLimitUnavailable,
    ValkeyGlobalAskRateLimiter,
)
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.post_chat import ContextualOrchestratorPostChatClient, NullPostChatClient, PostChatClient


class GlobalAskContentBlockModel(BaseModel):
    """Structured metadata for one prose or source-image response block."""

    type: Literal["text", "image"]
    text: str | None = None
    post_id: str | None = None
    unit_index: int | None = None
    mime_type: str | None = None
    data_base64: str | None = None
    alt_text: str | None = None
    caption: str | None = None


class GlobalAskResult(BaseModel):
    """Structured MCP response separating internal citations from web verification."""

    answer_text: str
    anchor_post_id: str
    cited_post_ids: list[str] = Field(default_factory=list)
    cited_posts: list[dict[str, str]] = Field(default_factory=list)
    source_post_ids: list[str] = Field(default_factory=list)
    timeline: list[dict[str, str]] = Field(default_factory=list)
    content_blocks: list[GlobalAskContentBlockModel] = Field(default_factory=list)
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
    rate_limiter: GlobalAskRateLimiter


class PreAuthTransportSecurityApp:
    """Apply MCP Host, Origin, and POST content-type checks before OAuth.

    MCP SDK 2.0 assembles its OAuth resource-server middleware outside the
    Streamable HTTP transport. Calling ``streamable_http_app`` directly can
    therefore challenge an unauthenticated hostile Host before the transport's
    DNS-rebinding validator runs. This outer ASGI boundary reuses the SDK's own
    validator and rejects invalid transport metadata before any token verifier,
    database resolver, quota decision, or Global Ask dependency is invoked.
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
            await rejection(scope, receive, send)
            return
        await self._app(scope, receive, send)


PoolFactory = Callable[[str], Awaitable[Any]]
AccountResolver = Callable[[Any, str], Awaitable[CurrentAccount]]
Answerer = Callable[..., Awaitable[GlobalAskAnswer]]
AccessTokenProvider = Callable[[], AccessToken | None]
ValkeyFactory = Callable[[str], Any]


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


def _rate_limit_error_data(error_code: str, retry_after_seconds: int) -> dict[str, object]:
    """Return client-actionable retry data without counters or raw principal ids."""
    return {
        "error_code": error_code,
        "retry_after_seconds": retry_after_seconds,
        "retryable": True,
        "scope": "authenticated_principal",
    }


def build_mcp_server(
    settings: Settings | None = None,
    *,
    pool_factory: PoolFactory = create_pool,
    token_verifier: TokenVerifier | None = None,
    account_resolver: AccountResolver = resolve_current_account,
    answerer: Answerer = answer_global_question,
    access_token_provider: AccessTokenProvider = get_access_token,
    external_verifier: GlobalAskExternalVerifier | None = None,
    rate_limiter: GlobalAskRateLimiter | None = None,
    valkey_factory: ValkeyFactory = create_valkey_client,
) -> MCPServer[McpAppContext]:
    """Build a testable OAuth resource server with one read-only Global Ask tool."""
    resolved_settings = settings or load_settings()
    resolved_external_verifier = external_verifier or _external_verifier(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: MCPServer) -> AsyncIterator[McpAppContext]:
        """Open and close process-wide database, Valkey, and client context."""
        pool = await pool_factory(resolved_settings.database_url)
        valkey_client = None
        try:
            resolved_rate_limiter = rate_limiter
            if resolved_rate_limiter is None:
                valkey_client = valkey_factory(resolved_settings.valkey_url)
                resolved_rate_limiter = ValkeyGlobalAskRateLimiter(
                    valkey_client,
                    maximum_requests=resolved_settings.mcp_global_ask_rate_limit,
                    window_seconds=resolved_settings.mcp_global_ask_rate_window_seconds,
                )
            yield McpAppContext(
                pool=pool,
                chat_client=_chat_client(resolved_settings),
                vision_client=orchestrator_vision_client(
                    resolved_settings.orchestrator_base_url,
                    resolved_settings.orchestrator_api_key,
                ),
                external_verifier=resolved_external_verifier,
                rate_limiter=resolved_rate_limiter,
            )
        finally:
            try:
                if valkey_client is not None:
                    await valkey_client.aclose()
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
            "not as support. A structured rate-limit error carries retry_after_seconds; "
            "retry no sooner than that value."
        ),
        version="1.0.2",
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
            "bounded retrieved evidence. Invocations are subject to a shared "
            "authenticated-principal quota."
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
    ) -> Annotated[CallToolResult, GlobalAskResult]:
        """Run source-grounded Global Ask with optional explicit open-web verification."""
        token = access_token_provider()
        if token is None or not token.subject:
            raise PermissionError("authenticated MCP principal is unavailable")
        dependencies = ctx.request_context.lifespan_context
        account = await account_resolver(dependencies.pool, token.subject)
        if not account.has_permission("post_read"):
            raise GlobalAskForbiddenError("account lacks the post_read permission")
        try:
            rate_decision = await dependencies.rate_limiter.acquire(
                account.user_account_id
            )
        except GlobalAskRateLimitUnavailable as exc:
            raise MCPError(
                ErrorData(
                    code=GLOBAL_ASK_RATE_LIMIT_UNAVAILABLE_ERROR_CODE,
                    message="Global Ask distributed rate limit is unavailable",
                    data=_rate_limit_error_data(
                        "global_ask_rate_limit_unavailable",
                        resolved_settings.mcp_rate_limit_unavailable_retry_seconds,
                    ),
                )
            ) from exc
        if not rate_decision.allowed:
            raise MCPError(
                ErrorData(
                    code=GLOBAL_ASK_RATE_LIMIT_ERROR_CODE,
                    message="Global Ask rate limit exceeded",
                    data=_rate_limit_error_data(
                        "global_ask_rate_limited",
                        rate_decision.retry_after_seconds,
                    ),
                )
            )
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
        structured = GlobalAskResult(
            **asdict(result),
            external_verification_status=verification.status_code,
            external_evidence_urls=list(verification.evidence_urls),
            external_verification_rationale=verification.rationale,
        )
        content = [TextContent(type="text", text=result.answer_text)]
        for block in result.content_blocks:
            if block.type == "image" and block.data_base64 and block.mime_type:
                content.append(
                    ImageContent(
                        type="image",
                        data=block.data_base64,
                        mime_type=block.mime_type,
                    )
                )
        return CallToolResult(
            content=content,
            structured_content=structured.model_dump(mode="json"),
        )

    return mcp


def build_mcp_http_app(
    server: MCPServer[McpAppContext],
    settings: Settings,
) -> ASGIApp:
    """Build the Streamable HTTP app with transport checks outside OAuth."""
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.mcp_allowed_hosts,
        allowed_origins=settings.mcp_allowed_origins,
    )
    sdk_app = server.streamable_http_app(transport_security=transport_security)
    return PreAuthTransportSecurityApp(sdk_app, transport_security)


_settings = load_settings()
mcp = build_mcp_server(_settings)
app = build_mcp_http_app(mcp, _settings)
