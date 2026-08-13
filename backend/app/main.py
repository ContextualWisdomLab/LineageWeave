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
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from lineageweave.keyman_extraction import (
    ContextualOrchestratorKeymanExtractionClient,
    NullKeymanExtractionClient,
)

from backend.app.auth import CurrentAccount, get_current_account
from backend.app.config import load_settings
from backend.app.db import create_pool, get_pool
from backend.app.keyman_ingestion import ingest_post_keymen
from backend.app.knowledge_graph import (
    fetch_post_keymen,
    person_exists,
    related_for_person,
    visible_mention_post_ids,
)

_POST_READ = "post_read"
_POST_ADMIN = "post_admin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open one asyncpg pool for the process and close it on shutdown."""
    settings = load_settings()
    app.state.pool = await create_pool(settings.database_url)
    try:
        yield
    finally:
        await app.state.pool.close()


app = FastAPI(title="LineageWeave API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=load_settings().frontend_origins,
    allow_methods=["GET", "POST"],
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


@app.post("/api/posts/{post_id}/extract-keymen")
async def extract_post_keymen(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Runs Keyman extraction over a post's own title+body and persists the
    result (cataloged_person / person_affiliation / post_person_mention /
    knowledge_graph_edge). Gated by post_admin, not post_read: this is a
    write action with a real LLM-call cost, not a read.
    """
    _require_post_admin(account)
    post = await _load_visible_post(post_id, account, pool)
    client = _keyman_extraction_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Keyman extraction is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    async with pool.acquire() as conn:
        body_row = await conn.fetchrow("select post_body from source_post where post_id = $1", post_id)
        async with conn.transaction():
            mentions = await ingest_post_keymen(conn, client, post_id, post["post_title"], body_row["post_body"])
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
    }
