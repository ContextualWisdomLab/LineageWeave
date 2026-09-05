"""Retained UUID-alias reads stay bounded at the Valkey wire."""

from __future__ import annotations

import asyncio

from backend.app.activity_stream import read_activity_events


class _CompatibilityPipeline:
    """Model queued SSCAN/XREVRANGE commands as one network exchange."""

    def __init__(self, client: _CompatibilityReadClient) -> None:
        self.client = client
        self.commands: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> bool:
        del exc_type, exc, traceback
        return False

    def sscan(self, key: str, *, cursor: int, count: int):
        self.commands.append(("sscan", (key,), {"cursor": cursor, "count": count}))
        return self

    def xrevrange(self, key: str, *, count: int, max: str = "+"):
        self.commands.append(("xrevrange", (key,), {"count": count, "max": max}))
        return self

    async def execute(self):
        self.client.round_trips += 1
        self.client.pipeline_batch_sizes.append(len(self.commands))
        results: list[object] = []
        for command, args, kwargs in self.commands:
            key = str(args[0])
            if command == "sscan":
                results.append((0, [self.client.legacy_key]))
                continue
            entries = self.client.entries_by_key[key]
            max_value = str(kwargs["max"])
            if max_value.startswith("("):
                boundary = max_value[1:]
                entries = [entry for entry in entries if entry[0] != boundary]
            results.append(entries[: int(kwargs["count"])])
        return results


class _CompatibilityReadClient:
    """Expose one canonical stream and one retained UUID-equivalent alias."""

    def __init__(self) -> None:
        canonical_post_id = "550e8400-e29b-41d4-a716-446655440000"
        self.canonical_key = f"activity:{canonical_post_id}"
        self.legacy_key = "activity:{550E8400-E29B-41D4-A716-446655440000}"
        self.round_trips = 0
        self.pipeline_batch_sizes: list[int] = []
        self.entries_by_key = {
            self.canonical_key: [
                ("400-0", {"event_type": "status", "actor_account_id": "acct", "summary": "canonical 400"}),
                ("200-0", {"event_type": "status", "actor_account_id": "acct", "summary": "canonical 200"}),
            ],
            self.legacy_key: [
                ("300-0", {"event_type": "created", "actor_account_id": "acct", "summary": "legacy 300"}),
                ("100-0", {"event_type": "created", "actor_account_id": "acct", "summary": "legacy 100"}),
            ],
        }

    def pipeline(self, *, transaction: bool):
        assert transaction is False
        return _CompatibilityPipeline(self)

    async def sscan_iter(self, key: str):
        assert key == "activity-aliases:550e8400-e29b-41d4-a716-446655440000"
        self.round_trips += 1
        yield self.legacy_key

    async def xrevrange(self, key: str, *, count: int, max: str = "+"):
        self.round_trips += 1
        entries = self.entries_by_key[key]
        if max.startswith("("):
            boundary = max[1:]
            entries = [entry for entry in entries if entry[0] != boundary]
        return entries[:count]


def test_retained_alias_read_reuses_complete_admission_page_before_local_merge() -> None:
    """A complete alias admission page must not be discarded and scanned again."""
    client = _CompatibilityReadClient()

    events = asyncio.run(
        read_activity_events(
            client,  # type: ignore[arg-type]
            "550E8400-E29B-41D4-A716-446655440000",
            event_count=4,
        )
    )

    assert [event["summary"] for event in events] == [
        "canonical 400",
        "legacy 300",
        "canonical 200",
        "legacy 100",
    ]
    assert client.round_trips == 2
    assert client.pipeline_batch_sizes == [2, 1]
