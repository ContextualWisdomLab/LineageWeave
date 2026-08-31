"""Focused checks for the Post body streaming authorization boundary."""

import asyncio

import pytest

from backend.app.auth import CurrentAccount
from backend.app.main import stream_post_body


class _Acquire:
    def __init__(self, connection: "_Connection") -> None:
        self.connection = connection

    async def __aenter__(self) -> "_Connection":
        return self.connection

    async def __aexit__(self, *args: object) -> None:
        return None


class _Connection:
    def __init__(self) -> None:
        self.chunk_queries: list[str] = []
        self.chunk_reads = 0

    async def fetchrow(self, query: str, *_args: object) -> dict[str, object] | None:
        if "as body_chunk" in query:
            self.chunk_queries.append(query)
            self.chunk_reads += 1
            if self.chunk_reads == 1:
                return {"body_chunk": "a" * 262_144}
            return None
        return {
            "post_id": "00000000-0000-0000-0000-000000000001",
            "visibility_code": "private",
            "corporate_entity_id": "00000000-0000-0000-0000-000000000002",
            "process_unit_id": None,
            "body_version": "7",
            "post_body_character_count": 524_288,
            "post_body_byte_count": 524_288,
        }

    async def fetchval(self, query: str, *_args: object) -> object:
        if "select exists" in query:
            return False
        raise AssertionError(f"unexpected fetchval: {query}")


class _Pool:
    def __init__(self) -> None:
        self.connection = _Connection()

    def acquire(self) -> _Acquire:
        return _Acquire(self.connection)


def test_body_stream_stops_when_version_or_authorization_changes() -> None:
    """Every chunk rechecks the captured row version and current ABAC scope."""
    pool = _Pool()
    account = CurrentAccount(
        user_account_id="account",
        external_subject_id="subject",
        display_name="Synthetic analyst",
        preferred_locale=None,
        corporate_entity_ids=frozenset({"00000000-0000-0000-0000-000000000002"}),
        process_unit_ids=frozenset(),
        permission_codes=frozenset({"post_read"}),
    )

    async def exercise() -> None:
        response = await stream_post_body(
            "00000000-0000-0000-0000-000000000001", None, account, pool
        )
        iterator = response.body_iterator.__aiter__()
        assert await iterator.__anext__() == b"a" * 262_144
        with pytest.raises(RuntimeError, match="changed while it was being transferred"):
            await iterator.__anext__()

    asyncio.run(exercise())
    assert pool.connection.chunk_reads == 2
    query = pool.connection.chunk_queries[0]
    assert "revision.xmin::text = $2" in query
    assert "post.corporate_entity_id = any($5::uuid[])" in query
    assert "source_draft_code" in query
