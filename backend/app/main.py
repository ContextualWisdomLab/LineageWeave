"""FastAPI app: direct-PostgreSQL source_post list/detail endpoints, gated
by OIDC login (backend.app.auth) and RBAC + ABAC (this module).

RBAC gate: the account's roles (account_role_assignment -> role_permission)
must include the 'post_read' permission at all -- a coarse yes/no on the
resource type.

ABAC gate, evaluated per row on top of the RBAC gate: a source_post is
visible if it is public, or if it is private and the requesting account is
affiliated with the post's owning corporate_entity_id. abac_policy's
condition_expression column is reserved for a future, richer per-policy
DSL (documented in migrations/0001_initial_schema.sql); Phase 1 implements
exactly this one fixed rule directly, since it is the only rule the
product currently needs.

The HTTP paths stay ``/api/posts`` (the product noun). The table they
read is ``source_post`` -- two-or-more-word table names, per AGENTS.md.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lineageweave.commitment_extraction import (
    ContextualOrchestratorCommitmentExtractionClient,
    NullCommitmentExtractionClient,
)
from lineageweave.entity_relationship_classification import (
    ContextualOrchestratorEntityRelationshipClient,
    NullEntityRelationshipClient,
)
from lineageweave.keyman_extraction import (
    ContextualOrchestratorKeymanExtractionClient,
    NullKeymanExtractionClient,
)
from lineageweave.post_chat import ContextualOrchestratorPostChatClient, NullPostChatClient
from lineageweave.post_summary import ContextualOrchestratorPostSummaryClient, NullPostSummaryClient

from backend.app.activity_stream import (
    create_valkey_client,
    get_valkey,
    publish_activity_event,
    read_activity_events,
)
from backend.app.affiliate_tree_ingestion import fetch_affiliate_forest, fetch_voc_evidence
from backend.app.auth import CurrentAccount, get_current_account
from backend.app.config import load_settings
from backend.app.db import create_pool, get_pool
from backend.app.entity_relationship_ingestion import ingest_post_entity_relationships
from backend.app.issue_ticket_ingestion import (
    create_ticket,
    fetch_ticket_post_id,
    fetch_upcoming_commitments,
    list_tickets_for_post,
    update_ticket,
    upsert_commitment_ticket,
)
from backend.app.keyman_ingestion import ingest_post_keymen
from backend.app.knowledge_graph import (
    fetch_post_keymen,
    person_exists,
    related_for_person,
    visible_mention_post_ids,
)
from backend.app.lineage_ingestion import rebuild_lineage, visible_lineage_graph
from backend.app.post_chat_ingestion import find_linked_post_ids, gather_chat_sources

_POST_READ = "post_read"
_POST_ADMIN = "post_admin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open one asyncpg pool and one Valkey client for the process, and
    close both on shutdown."""
    settings = load_settings()
    app.state.pool = await create_pool(settings.database_url)
    app.state.valkey = create_valkey_client(settings.valkey_url)
    try:
        yield
    finally:
        await app.state.pool.close()
        await app.state.valkey.aclose()


app = FastAPI(title="LineageWeave API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=load_settings().frontend_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization"],
)


def _require_post_read(account: CurrentAccount) -> None:
    """Raise 403 when the account has no ``post_read`` permission at all."""
    if not account.has_permission(_POST_READ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account lacks the post_read permission")


def _require_post_admin(account: CurrentAccount) -> None:
    """Raise 403 when the account has no ``post_admin`` permission at all."""
    if not account.has_permission(_POST_ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account lacks the post_admin permission")


def _keyman_extraction_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullKeymanExtractionClient()
    return ContextualOrchestratorKeymanExtractionClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _entity_relationship_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullEntityRelationshipClient()
    return ContextualOrchestratorEntityRelationshipClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _post_summary_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostSummaryClient()
    return ContextualOrchestratorPostSummaryClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _post_chat_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostChatClient()
    return ContextualOrchestratorPostChatClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _commitment_extraction_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullCommitmentExtractionClient()
    return ContextualOrchestratorCommitmentExtractionClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _can_see_post(account: CurrentAccount, post: asyncpg.Record) -> bool:
    """ABAC: public rows are visible; private rows require same-corp affiliation."""
    if post["visibility_code"] == "public":
        return True
    return str(post["corporate_entity_id"]) in account.corporate_entity_ids


def _serialize_post(post: asyncpg.Record) -> dict[str, Any]:
    """Turn a ``source_post`` row into the public JSON shape."""
    return {
        "post_id": str(post["post_id"]),
        "post_title": post["post_title"],
        "voc_type_code": post["voc_type_code"],
        "visibility_code": post["visibility_code"],
        "created_at": post["created_at"].isoformat(),
    }


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe: the process is up. Does not touch Postgres."""
    return {"status": "ok"}


@app.get("/api/me")
async def read_me(account: CurrentAccount = Depends(get_current_account)) -> dict[str, Any]:
    """Return the provisioned account that the bearer token resolved to."""
    return {
        "user_account_id": account.user_account_id,
        "display_name": account.display_name,
        "permission_codes": sorted(account.permission_codes),
    }


@app.get("/api/lineage")
async def read_lineage_graph(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """ABAC-filtered reconstruct graph for the product UI (same shape as the demo server)."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        return await visible_lineage_graph(conn, lambda row: _can_see_post(account, row))


@app.post("/api/lineage/rebuild")
async def rebuild_lineage_graph(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Run reconstruct over every source_post and persist post_lineage_edge.

    post_admin only: this is a corpus-wide write. Reads stay ABAC-gated.
    """
    _require_post_admin(account)
    async with pool.acquire() as conn:
        async with conn.transaction():
            edges = await rebuild_lineage(conn)
    return {"edge_count": len(edges)}


@app.get("/api/posts")
async def list_posts(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict[str, Any]]:
    """List source_post rows the account is allowed to see (RBAC then ABAC)."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select post_id, post_title, voc_type_code, visibility_code, corporate_entity_id, created_at "
            "from source_post order by created_at desc"
        )
    return [_serialize_post(row) for row in rows if _can_see_post(account, row)]


@app.get("/api/posts/{post_id}")
async def read_post(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Return one source_post, or 404 / 403 if it is missing or out of scope."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select post_id, post_title, post_body, voc_type_code, visibility_code, corporate_entity_id, created_at "
            "from source_post where post_id = $1",
            post_id,
        )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")
    if not _can_see_post(account, row):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this post")
    return {**_serialize_post(row), "post_body": row["post_body"]}


async def _load_visible_post(
    post_id: str,
    account: CurrentAccount,
    pool: asyncpg.Pool,
) -> asyncpg.Record:
    """Load one post the account may see, or raise 404 / 403."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select post_id, post_title, voc_type_code, visibility_code, corporate_entity_id, created_at "
            "from source_post where post_id = $1",
            post_id,
        )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")
    if not _can_see_post(account, row):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this post")
    return row


@app.get("/api/posts/{post_id}/keymen")
async def read_post_keymen(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """People mentioned on one visible post, with their N:N affiliations."""
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        keymen = await fetch_post_keymen(conn, post_id)
    return {"post_id": str(post["post_id"]), "keymen": keymen}


@app.get("/api/keymen/{person_id}/related")
async def read_related_keymen(
    person_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """RWR-ranked related nodes from one person, hiding unseen posts."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        if not await person_exists(conn, person_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "person not found")
        visible_post_ids = await visible_mention_post_ids(conn, person_id, lambda row: _can_see_post(account, row))
        if not visible_post_ids:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this person")
        person = await conn.fetchrow(
            "select person_id, person_name, person_side_code from cataloged_person where person_id = $1",
            person_id,
        )
        related = await related_for_person(conn, person_id, visible_post_ids)
    return {
        "person_id": str(person["person_id"]),
        "person_name": person["person_name"],
        "person_side_code": person["person_side_code"],
        "related": related,
    }


@app.get("/api/posts/{post_id}/counterparties")
async def read_post_counterparties(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Classified counterparty orgs for one visible post."""
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select c.counterparty_entity_name, c.relationship_type_code, v.lookup_label as relationship_label
            from post_counterparty_entity c
            join common_lookup_value v on v.lookup_code = c.relationship_type_code
            where c.post_id = $1
            order by c.counterparty_entity_name
            """,
            post_id,
        )
    return {
        "post_id": str(post["post_id"]),
        "counterparties": [dict(row) for row in rows],
    }


@app.get("/api/posts/{post_id}/affiliate-tree")
async def read_post_affiliate_tree(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Ancestor forest of every organization this post's Keymen touch.

    Resolved affiliations walk ``corporate_entity.parent_entity_id``.
    Unresolved names stay as their own roots -- a missing hierarchy
    match is not a guessed parent.
    """
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        trees = await fetch_affiliate_forest(conn, post_id)
    return {"post_id": str(post["post_id"]), "trees": trees}


@app.get("/api/posts/{post_id}/voc-evidence")
async def read_post_voc_evidence(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """VOC type label plus extractive excerpts that name classified orgs."""
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        return await fetch_voc_evidence(conn, post_id, post["voc_type_code"])


@app.post("/api/posts/{post_id}/extract-keymen")
async def extract_post_keymen(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Runs Keyman extraction over a post's own title+body and persists the
    result (cataloged_person / person_affiliation / post_person_mention /
    knowledge_graph_edge), then classifies each affiliated organization's
    relationship to the post author's org (post_counterparty_entity).
    Gated by post_admin, not post_read: this is a write action with a
    real LLM-call cost, not a read.
    """
    _require_post_admin(account)
    post = await _load_visible_post(post_id, account, pool)
    keyman_client = _keyman_extraction_client()
    if not keyman_client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Keyman extraction is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    relationship_client = _entity_relationship_client()
    async with pool.acquire() as conn:
        body_row = await conn.fetchrow("select post_body from source_post where post_id = $1", post_id)
        post_body = "" if body_row is None else body_row["post_body"]
        async with conn.transaction():
            mentions = await ingest_post_keymen(conn, keyman_client, post_id, post["post_title"], post_body)
            organization_names = sorted(
                {name for mention in mentions for name in mention.affiliated_organization_names}
            )
            # relationship_client is gated by the same settings check as
            # keyman_client above (both read ORCHESTRATOR_BASE_URL/_API_KEY),
            # so reaching here means it is available too.
            relationships = await ingest_post_entity_relationships(
                conn, relationship_client, post_id, post["post_title"], post_body, organization_names
            )
    return {
        "post_id": str(post["post_id"]),
        "extracted_count": len(mentions),
        "mentions": [
            {
                "person_name": mention.person_name,
                "person_side_code": mention.person_side_code,
                "affiliated_organization_names": list(mention.affiliated_organization_names),
            }
            for mention in mentions
        ],
        "counterparties": [
            {
                "organization_name": relationship.organization_name,
                "relationship_type_code": relationship.relationship_type_code,
            }
            for relationship in relationships
        ],
    }


@app.get("/api/posts/{post_id}/lineage")
async def read_post_lineage(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """The Event Lineage panel's data: this post's directly (thread-)linked
    posts and its indirectly (shared-Keyman/organization) linked posts,
    kept as two distinguishable lists -- not merged into one, since they
    are different claims about *why* two posts are related. ABAC-filtered
    per candidate the same way every other endpoint here is.
    """
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        linked = await find_linked_post_ids(conn, post_id)
        candidate_ids = linked.direct | linked.indirect
        rows = {}
        if candidate_ids:
            fetched = await conn.fetch(
                "select post_id, post_title, visibility_code, corporate_entity_id "
                "from source_post where post_id = any($1::uuid[])",
                list(candidate_ids),
            )
            rows = {str(row["post_id"]): row for row in fetched}

    def _visible_summaries(ids: frozenset[str]) -> list[dict[str, Any]]:
        return [
            {"post_id": post_id_, "post_title": rows[post_id_]["post_title"]}
            for post_id_ in ids
            if post_id_ in rows and _can_see_post(account, rows[post_id_])
        ]

    return {
        "post_id": post_id,
        "direct": _visible_summaries(linked.direct),
        "indirect": _visible_summaries(linked.indirect),
    }


@app.get("/api/posts/{post_id}/summary")
async def read_post_summary(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """A Korean summary, key events, and R&R (roles & responsibilities)
    for the popup's summary panel. Computed fresh per request (not
    persisted) -- Phase 4 scope is "return it," not "cache it."
    """
    post = await _load_visible_post(post_id, account, pool)
    client = _post_summary_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Post summary is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    async with pool.acquire() as conn:
        body_row = await conn.fetchrow("select post_body from source_post where post_id = $1", post_id)
    summary = client.summarize(post["post_title"], body_row["post_body"])
    return {
        "post_id": str(post["post_id"]),
        "korean_summary": summary.korean_summary,
        "key_events": list(summary.key_events),
        "roles_and_responsibilities": [
            {"person_name": rr.person_name, "responsibility": rr.responsibility}
            for rr in summary.roles_and_responsibilities
        ],
    }


class ChatRequest(BaseModel):
    """JSON body for ``POST /api/posts/{post_id}/chat``."""

    question: str


@app.post("/api/posts/{post_id}/chat")
async def chat_about_post(
    post_id: str,
    request: ChatRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """In-popup LLM chat: answers `request.question` using this post's own
    content plus its Event-Lineage-linked posts (direct and Knowledge-
    Graph-indirect) as context, and returns which source post(s) the
    answer drew from -- the sliding evidence panel's citation data.
    Two explicit steps (retrieve, then reason-and-cite; see
    `lineageweave.post_chat`'s module docstring) rather than one prompt.
    """
    await _load_visible_post(post_id, account, pool)
    client = _post_chat_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Post chat is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    async with pool.acquire() as conn:
        sources = await gather_chat_sources(conn, post_id, lambda row: _can_see_post(account, row))
    answer = client.answer(request.question, sources)
    return {
        "post_id": post_id,
        "answer_text": answer.answer_text,
        "cited_post_ids": list(answer.cited_post_ids),
        "source_post_ids": [source.post_id for source in sources],
    }


@app.get("/api/posts/{post_id}/tickets")
async def read_post_tickets(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """List issue tickets on one visible post. Read-only, so post_read
    is enough -- same gate as every other post-scoped GET here.
    """
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        tickets = await list_tickets_for_post(conn, post_id)
    return {"post_id": post_id, "tickets": tickets}


class CreateTicketRequest(BaseModel):
    """JSON body for ``POST /api/posts/{post_id}/tickets``."""

    ticket_title: str
    ticket_status_code: str
    assigned_account_id: str | None = None
    # Manual calendar/to-do date, e.g. YYYY-MM-DD. Set automatically instead
    # by POST /api/posts/{post_id}/derive-commitment when the LLM should
    # decide it.
    due_date: str | None = None


@app.post("/api/posts/{post_id}/tickets", status_code=status.HTTP_201_CREATED)
async def create_post_ticket(
    post_id: str,
    request: CreateTicketRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict[str, Any]:
    """Create an issue ticket on a visible post. post_admin-gated: opening
    a ticket is a write action, same discipline as extract-keymen.
    """
    _require_post_admin(account)
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        try:
            ticket = await create_ticket(
                conn,
                post_id,
                request.ticket_title,
                request.ticket_status_code,
                request.assigned_account_id,
                due_date=request.due_date,
            )
        except asyncpg.ForeignKeyViolationError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"ticket_status_code {request.ticket_status_code!r} is not a valid ticket_status lookup code",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"due_date {request.due_date!r} is not a valid YYYY-MM-DD date",
            ) from exc
    await publish_activity_event(
        valkey, post_id, "ticket_created", account.user_account_id, f"Ticket created: {request.ticket_title}"
    )
    return ticket


class UpdateTicketRequest(BaseModel):
    """JSON body for ``PATCH /api/tickets/{issue_ticket_id}``.

    ``assigned_account_id`` left unset means "don't touch it";
    ``clear_assignment=True`` explicitly unassigns. Both are distinct,
    expressible outcomes a partial-update endpoint needs.
    """

    ticket_status_code: str | None = None
    assigned_account_id: str | None = None
    clear_assignment: bool = False


@app.patch("/api/tickets/{issue_ticket_id}")
async def patch_ticket(
    issue_ticket_id: str,
    request: UpdateTicketRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict[str, Any]:
    """Update a ticket's status and/or assignee. post_admin-gated. The
    ABAC check runs against the ticket's OWNING post, resolved first --
    a ticket has no visibility_code of its own, it inherits its post's.
    """
    _require_post_admin(account)
    async with pool.acquire() as conn:
        post_id = await fetch_ticket_post_id(conn, issue_ticket_id)
        if post_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "ticket not found")
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        try:
            ticket = await update_ticket(
                conn,
                issue_ticket_id,
                request.ticket_status_code,
                request.assigned_account_id,
                request.clear_assignment,
            )
        except asyncpg.ForeignKeyViolationError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"ticket_status_code {request.ticket_status_code!r} is not a valid ticket_status lookup code",
            ) from exc
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ticket not found")
    if request.ticket_status_code is not None:
        await publish_activity_event(
            valkey,
            post_id,
            "ticket_status_changed",
            account.user_account_id,
            f"Ticket status changed to {request.ticket_status_code}",
        )
    return ticket


@app.get("/api/posts/{post_id}/activity")
async def read_post_activity(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict[str, Any]:
    """The post's activity feed, read straight off its Valkey stream
    (``XREVRANGE``) -- newest first. Read-only, so post_read is enough.
    """
    await _load_visible_post(post_id, account, pool)
    events = await read_activity_events(valkey, post_id)
    return {"post_id": post_id, "events": events}


@app.post("/api/posts/{post_id}/derive-commitment")
async def derive_post_commitment(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict[str, Any]:
    """LLM-derive a customer commitment (if any) from a post's own text,
    and -- when found -- register it as an issue_ticket with a due_date,
    which is what makes it show up on GET /api/calendar. post_admin-gated:
    a real LLM-call write action, same discipline as extract-keymen.
    `has_commitment: false` is a normal 200 response, not an error --
    most posts genuinely have no commitment in them.
    """
    _require_post_admin(account)
    post = await _load_visible_post(post_id, account, pool)
    client = _commitment_extraction_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Commitment derivation is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    async with pool.acquire() as conn:
        body_row = await conn.fetchrow("select post_body from source_post where post_id = $1", post_id)
    # TimeML/TempEval document creation time, not wall-clock now: "by next
    # Friday" in a January post must resolve to that January, not to the
    # Friday after the operator clicked Derive.
    reference_date = post["created_at"].date().isoformat()
    commitment = client.extract(post["post_title"], body_row["post_body"], reference_date)
    if not commitment.has_commitment:
        return {"post_id": str(post["post_id"]), "has_commitment": False, "ticket": None}
    async with pool.acquire() as conn:
        try:
            ticket = await upsert_commitment_ticket(
                conn,
                post_id,
                commitment.commitment_summary,
                commitment.due_date,
                commitment.commitment_summary,
            )
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"due_date {commitment.due_date!r} is not a valid YYYY-MM-DD date",
            ) from exc
    await publish_activity_event(
        valkey,
        post_id,
        "commitment_derived",
        account.user_account_id,
        f"Commitment derived: {commitment.commitment_summary}",
    )
    return {"post_id": str(post["post_id"]), "has_commitment": True, "ticket": ticket}


@app.get("/api/calendar")
async def read_calendar(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Every dated, not-closed commitment/ticket the account may see,
    soonest first -- the to-do/calendar surface (no Outlook sync yet;
    this is the internal data model that a future Outlook connector
    would read from).
    """
    _require_post_read(account)
    async with pool.acquire() as conn:
        commitments = await fetch_upcoming_commitments(conn)
    visible = [c for c in commitments if _can_see_post(account, c)]
    for c in visible:
        del c["visibility_code"], c["corporate_entity_id"]
    return {"commitments": visible}
