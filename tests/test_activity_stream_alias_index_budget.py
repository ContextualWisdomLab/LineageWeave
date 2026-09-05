"""Startup legacy-activity alias indexing stays bounded at the Valkey wire."""

from __future__ import annotations

import asyncio
from uuid import UUID

from backend.app.activity_stream import index_legacy_activity_stream_aliases


class _AliasIndexPipeline:
    """Model independent alias-set writes completed by one pipeline exchange."""

    def __init__(self, client: _AliasIndexClient) -> None:
        self.client = client
        self.pending: list[tuple[str, str]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> bool:
        del exc_type, exc, traceback
        return False

    def sadd(self, key: str, member: str):
        self.pending.append((key, member))
        return self

    async def execute(self) -> list[int]:
        self.client.pipeline_round_trips += 1
        self.client.pipeline_batch_sizes.append(len(self.pending))
        added: list[int] = []
        for key, member in self.pending:
            members = self.client.members.setdefault(key, set())
            before = len(members)
            members.add(member)
            added.append(int(len(members) != before))
        return added


class _AliasIndexClient:
    """Expose historical aliases while rejecting per-alias network writes."""

    def __init__(self, keys: tuple[str, ...] | None = None) -> None:
        self.keys = keys or (
            "activity:550e8400-e29b-41d4-a716-446655440000",
            "activity:550e8400e29b41d4a716446655440000",
            "activity:{550E8400-E29B-41D4-A716-446655440000}",
        )
        self.members: dict[str, set[str]] = {}
        self.direct_sadd_calls = 0
        self.pipeline_round_trips = 0
        self.pipeline_batch_sizes: list[int] = []

    async def scan_iter(self, *, match: str):
        assert match == "activity:*"
        for key in self.keys:
            yield key

    async def sadd(self, key: str, member: str) -> int:
        del key, member
        self.direct_sadd_calls += 1
        raise AssertionError("startup alias indexing must not await one SADD per alias")

    def pipeline(self, *, transaction: bool):
        assert transaction is False
        return _AliasIndexPipeline(self)


def test_startup_alias_index_batches_independent_sadd_writes() -> None:
    """Two retained aliases must not add two serial Valkey write round trips."""
    client = _AliasIndexClient()

    indexed = asyncio.run(index_legacy_activity_stream_aliases(client))  # type: ignore[arg-type]

    canonical_post_id = "550e8400-e29b-41d4-a716-446655440000"
    assert indexed == 2
    assert client.direct_sadd_calls == 0
    assert client.pipeline_round_trips == 1
    assert client.pipeline_batch_sizes == [2]
    assert client.members == {
        f"activity-aliases:{canonical_post_id}": {
            "activity:550e8400e29b41d4a716446655440000",
            "activity:{550E8400-E29B-41D4-A716-446655440000}",
        }
    }


def test_startup_alias_index_flushes_before_exceeding_the_batch_ceiling() -> None:
    """The 129th independent alias starts a second bounded pipeline exchange."""
    aliases = tuple(
        f"activity:{{{str(UUID(int=index + 1)).upper()}}}"
        for index in range(129)
    )
    client = _AliasIndexClient(aliases)

    indexed = asyncio.run(index_legacy_activity_stream_aliases(client))  # type: ignore[arg-type]

    assert indexed == 129
    assert client.direct_sadd_calls == 0
    assert client.pipeline_round_trips == 2
    assert client.pipeline_batch_sizes == [128, 1]
    assert sum(len(members) for members in client.members.values()) == 129
