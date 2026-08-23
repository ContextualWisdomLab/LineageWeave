"""Explicitly retry one terminal post-content ingestion job."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg
import redis.asyncio as redis

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.config import load_settings
from backend.app.post_content_queue import (
    publish_post_content_event,
    requeue_failed_post_content_job,
)


def _parser() -> argparse.ArgumentParser:
    """Build the operator-only command-line parser."""
    parser = argparse.ArgumentParser(
        description="Explicitly requeue one failed post-content ingestion job."
    )
    parser.add_argument("--post-id", required=True)
    parser.add_argument("--target-dsn")
    parser.add_argument("--valkey-url")
    return parser


async def requeue_post_content(
    post_id: str,
    *,
    target_dsn: str,
    valkey_url: str,
) -> None:
    """Reset one failed job, append its audit event, and publish its wake-up."""
    connection = await asyncpg.connect(target_dsn)
    client = redis.from_url(valkey_url, decode_responses=True)
    try:
        body_row = await connection.fetchrow(
            """
            select post.post_body
              from source_post post
             where post.post_id = $1::uuid
               and coalesce(upper(btrim(post.source_detail_state_code)), '') <> 'W'
            """,
            post_id,
        )
        if body_row is None:
            raise ValueError(f"source post does not exist: {post_id}")
        async with connection.transaction():
            request = await requeue_failed_post_content_job(
                connection,
                post_id,
                str(body_row["post_body"] or ""),
            )
        entry_id = await publish_post_content_event(
            client,
            post_id=request.post_id,
            source_body_digest=request.source_body_sha256,
        )
        if entry_id is None:
            raise RuntimeError("Valkey did not publish the explicit retry wake-up")
        print({"post_id": post_id, "status": request.status_code, "published": True})
    finally:
        await connection.close()
        await client.aclose()


def main() -> None:
    """Parse the target and run one explicit terminal-job recovery."""
    args = _parser().parse_args()
    settings = load_settings()
    asyncio.run(
        requeue_post_content(
            args.post_id,
            target_dsn=args.target_dsn or settings.database_url,
            valkey_url=args.valkey_url or settings.valkey_url,
        )
    )


if __name__ == "__main__":
    main()
