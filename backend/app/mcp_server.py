"""Authenticated Streamable HTTP MCP server exposing read-only Global Ask."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import Any

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl, BaseModel, Field

from backend.app.auth import CurrentAccount, resolve_current_account
from backend.app.config import Settings, load_settings
from backend.app.db import create_pool
from backend.app.global_ask import GlobalAskAnswer, answer_global_question
from backend.app.mcp_auth import KeycloakMcpTokenVerifier
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.post_chat import ContextualOrchestratorPostChatClient, NullPostChatClient, PostChatClient


class GlobalAskResult(BaseModel):
    """Structured MCP response with bounded source and citation identifiers."""

    answer_text: str
    anchor_post_id: str
    cited_post_ids: list[str] = Field(default_factory=list)
    cited_posts: list[dict[str, str]] = Field(default_factory=list)
    source_post_ids: list[str] = Field(default_factory=list)


@dataclass
class McpAppContext:
    """Long-lived dependencies shared by every MCP tool call."""

    pool: Any
    chat_client: PostChatClient
    vision_client: Any


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


def build_mcp_server(
    settings: Settings | None = None,
    *,
    pool_factory: PoolFactory = create_pool,
    token_verifier: TokenVerifier | None = None,
    account_resolver: AccountResolver = resolve_current_account,
    answerer: Answerer = answer_global_question,
    access_token_provider: AccessTokenProvider = get_access_token,
) -> MCPServer[McpAppContext]:
    """Build a testable OAuth resource server with one read-only tool."""
    resolved_settings = settings or load_settings()

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
            )
        finally:
            await pool.close()

    mcp = MCPServer(
        "lineageweave",
        title="LineageWeave",
        description="Authenticated evidence-grounded lineage intelligence.",
        instructions=(
            "Use global_ask only to answer from the authenticated caller's authorized "
            "LineageWeave source-post and event-lineage evidence. Treat answers as "
            "evidence-grounded inference, not authoritative fact. Follow cited post IDs. "
            "The tool is read-only and fails closed when evidence or the configured "
            "contextual-orchestrator is unavailable."
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
            "Answer a question using only source posts and event-lineage evidence visible "
            "to the authenticated LineageWeave account; returns source and citation IDs."
        ),
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
    )
    async def global_ask(question: str, ctx: Context[McpAppContext, Any]) -> GlobalAskResult:
        """Run authorization-preserving Global Ask for the current MCP principal."""
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
        return GlobalAskResult(**asdict(result))

    return mcp


_settings = load_settings()
mcp = build_mcp_server(_settings)
app = mcp.streamable_http_app(
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_settings.mcp_allowed_hosts,
        allowed_origins=_settings.mcp_allowed_origins,
    )
)