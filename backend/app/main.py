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

from backend.app.auth import CurrentAccount, get_current_account
from backend.app.config import load_settings
from backend.app.db import create_pool, get_pool

_POST_READ = "post_read"


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
    allow_methods=["GET"],
    allow_headers=["Authorization"],
)


def _require_post_read(account: CurrentAccount) -> None:
    """Raise 403 when the account has no ``post_read`` permission at all."""
    if not account.has_permission(_POST_READ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account lacks the post_read permission")


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
