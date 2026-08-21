"""Contracts for persisted post-Ask knowledge cutoffs."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from backend.app.post_chat_ingestion import persist_post_chat


ROOT = Path(__file__).resolve().parents[1]
CUTOFF = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


class _Connection:
    """Minimal chat-persistence double that records SQL parameters."""

    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *args: object) -> None:
        self.executions.append((query, args))

    async def fetchrow(self, query: str, *args: object):
        del args
        if "from post_chat_result" not in query:
            return None
        return {
            "question_text": "What happened?",
            "answer_text": "Synthetic answer",
            "knowledge_cutoff": CUTOFF,
        }

    async def fetch(self, query: str, *args: object):
        del query, args
        return []


def test_persist_post_chat_writes_the_retrieval_cutoff_not_a_later_read_clock() -> None:
    conn = _Connection()

    result = asyncio.run(
        persist_post_chat(
            conn,
            "00000000-0000-4000-8000-000000000001",
            "What happened?",
            "Synthetic answer",
            [],
            knowledge_cutoff=CUTOFF,
        )
    )

    insert = next(
        (query, args)
        for query, args in conn.executions
        if "insert into post_chat_result" in query
    )
    assert "computed_at" in insert[0]
    assert "knowledge_cutoff" in insert[0]
    assert insert[1][-2] >= CUTOFF
    assert insert[1][-1] == CUTOFF
    assert result["_knowledge_cutoff"] == CUTOFF


def test_cutoff_migration_is_applied_and_fails_closed_on_inverted_clocks() -> None:
    migration = ROOT / "migrations/0053_post_chat_knowledge_cutoff.sql"
    rollback = ROOT / "migrations/rollback/0053_post_chat_knowledge_cutoff.sql"
    migrate_script = (ROOT / "docker/postgres-init/migrate.sh").read_text(encoding="utf-8")

    assert migration.is_file()
    text = migration.read_text(encoding="utf-8")
    assert "knowledge_cutoff timestamptz" in text
    assert "knowledge_cutoff = computed_at" in text
    assert "knowledge_cutoff <= computed_at" in text
    assert rollback.is_file()
    assert "0053_*" in migrate_script
