"""Synchronize the fixed official O*NET construct catalog into PostgreSQL."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.config import load_settings
from lineageweave.http_client import get_json
from lineageweave.occupational_construct_catalog import (
    ONET_CONTENT_MODEL_URL,
    sync_onet_construct_catalog,
)


def _parser() -> argparse.ArgumentParser:
    """Build the operator-only catalog synchronization parser."""
    parser = argparse.ArgumentParser(
        description="Synchronize the governed O*NET occupational construct catalog."
    )
    parser.add_argument("--target-dsn")
    return parser


async def synchronize_catalog(target_dsn: str) -> int:
    """Download the fixed release and persist it without exposing credentials."""
    payload = await asyncio.to_thread(
        get_json,
        ONET_CONTENT_MODEL_URL,
        timeout=30.0,
        service_peer_name="onet-resource-center",
        maximum_response_bytes=8 * 1024 * 1024,
        expected_response_media_type="application/json",
    )
    conn = await asyncpg.connect(target_dsn)
    try:
        return await sync_onet_construct_catalog(conn, payload)
    finally:
        await conn.close()


def main() -> None:
    """Parse configuration, synchronize the catalog, and print only its count."""
    args = _parser().parse_args()
    settings = load_settings()
    count = asyncio.run(synchronize_catalog(args.target_dsn or settings.database_url))
    print({"release": "31.0", "construct_count": count})


if __name__ == "__main__":
    main()
