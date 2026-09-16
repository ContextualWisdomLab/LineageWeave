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


def _catalog_sync_parser() -> argparse.ArgumentParser:
    """Build the operator-only catalog synchronization parser."""
    catalog_sync_parser = argparse.ArgumentParser(
        description="Synchronize the governed O*NET occupational construct catalog."
    )
    catalog_sync_parser.add_argument("--target-dsn")
    return catalog_sync_parser


async def synchronize_occupational_construct_catalog(target_dsn: str) -> int:
    """Download the fixed release and persist it without exposing credentials."""
    catalog_payload = await asyncio.to_thread(
        get_json,
        ONET_CONTENT_MODEL_URL,
        timeout=30.0,
        service_peer_name="onet-resource-center",
        maximum_response_bytes=8 * 1024 * 1024,
        expected_response_media_type="application/json",
    )
    database_connection = await asyncpg.connect(target_dsn)
    try:
        return await sync_onet_construct_catalog(database_connection, catalog_payload)
    finally:
        await database_connection.close()


def main() -> None:
    """Parse configuration, synchronize the catalog, and print only its count."""
    command_arguments = _catalog_sync_parser().parse_args()
    runtime_settings = load_settings()
    synchronized_construct_count = asyncio.run(
        synchronize_occupational_construct_catalog(
            command_arguments.target_dsn or runtime_settings.database_url
        )
    )
    print({"release": "31.0", "construct_count": synchronized_construct_count})


if __name__ == "__main__":
    main()
