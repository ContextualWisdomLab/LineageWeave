"""Migration identity and replay-window contracts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_forward_migration_numeric_prefixes_are_unique() -> None:
    """Every forward migration has one unambiguous numeric identity."""

    migrations = sorted((ROOT / "migrations").glob("[0-9][0-9][0-9][0-9]_*.sql"))
    counts = Counter(path.name.split("_", 1)[0] for path in migrations)
    duplicates = sorted(prefix for prefix, count in counts.items() if count > 1)
    assert duplicates == []


def test_post_chat_cutoff_uses_the_next_unique_replayable_migration() -> None:
    """The Ask cutoff migration remains independently addressable and replayed."""

    forward = ROOT / "migrations/0054_post_chat_knowledge_cutoff.sql"
    rollback = ROOT / "migrations/rollback/0054_post_chat_knowledge_cutoff.sql"
    script = (ROOT / "docker/postgres-init/migrate.sh").read_text(encoding="utf-8")
    assert forward.is_file()
    assert rollback.is_file()
    assert not (ROOT / "migrations/0053_post_chat_knowledge_cutoff.sql").exists()
    assert "0054_*" in script
