"""A single asyncpg connection pool -- direct PostgreSQL access, no ORM, no
file-backed database. Every query in this backend goes through this pool."""

from __future__ import annotations

import asyncpg
from fastapi import Request


async def create_pool(database_url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(database_url, min_size=1, max_size=10)


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool
