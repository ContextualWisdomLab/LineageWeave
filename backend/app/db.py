"""A single asyncpg connection pool -- direct PostgreSQL access, no ORM, no
file-backed database. Every query in this backend goes through this pool."""

from __future__ import annotations

import asyncpg
from fastapi import Request


async def create_pool(database_url: str) -> asyncpg.Pool:
    """Open the process-wide asyncpg pool against ``database_url``."""
    return await asyncpg.create_pool(
        database_url,
        min_size=1,
        max_size=10,
        server_settings={"jit": "off"},
    )


def get_pool(request: Request) -> asyncpg.Pool:
    """FastAPI dependency: the pool stored on ``app.state`` at startup."""
    return request.app.state.pool
