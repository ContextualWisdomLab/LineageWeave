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


def _post_content_requeue_parser() -> argparse.ArgumentParser:
    """Build the operator-only command-line parser."""
    command_parser = argparse.ArgumentParser(
        description="Explicitly requeue one failed post-content ingestion job."
    )
    command_parser.add_argument("--post-id", required=True)
    command_parser.add_argument("--target-dsn")
    command_parser.add_argument("--valkey-url")
    return command_parser


async def requeue_post_content(
    post_id: str,
    *,
    target_dsn: str,
    valkey_url: str,
) -> None:
    """Reset one failed job, append its audit event, and publish its wake-up."""
    database_connection = await asyncpg.connect(target_dsn)
    valkey_client = redis.from_url(valkey_url, decode_responses=True)
    try:
        source_post_body_row = await database_connection.fetchrow(
            "select post_body from source_post where post_id = $1::uuid",
            post_id,
        )
        if source_post_body_row is None:
            raise ValueError(f"source post does not exist: {post_id}")
        async with database_connection.transaction():
            post_content_job_request = await requeue_failed_post_content_job(
                database_connection,
                post_id,
                str(source_post_body_row["post_body"] or ""),
            )
        valkey_stream_entry_id = await publish_post_content_event(
            valkey_client,
            post_id=post_content_job_request.post_id,
            source_body_digest=post_content_job_request.source_body_sha256,
        )
        if valkey_stream_entry_id is None:
            raise RuntimeError("Valkey did not publish the explicit retry wake-up")
        print(
            {
                "post_id": post_id,
                "status": post_content_job_request.status_code,
                "published": True,
            }
        )
    finally:
        await database_connection.close()
        await valkey_client.aclose()


def main() -> None:
    """Parse the target and run one explicit terminal-job recovery."""
    command_arguments = _post_content_requeue_parser().parse_args()
    runtime_settings = load_settings()
    asyncio.run(
        requeue_post_content(
            command_arguments.post_id,
            target_dsn=command_arguments.target_dsn or runtime_settings.database_url,
            valkey_url=command_arguments.valkey_url or runtime_settings.valkey_url,
        )
    )


if __name__ == "__main__":
    main()
