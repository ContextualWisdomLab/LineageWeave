"""Hosted contract for rollback serialization of the UI translation ledger."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLLBACK = ROOT / "migrations" / "rollback" / "0246_ui_translation_ledger.sql"


def test_translation_ledger_rollback_locks_resource_before_empty_guard() -> None:
    """Hosted runners must preserve the lock that closes the empty-check/write race."""
    sql = ROLLBACK.read_text(encoding="utf-8").lower()
    lock = "lock table ui_translation_resource in access exclusive mode"
    guard = "if exists (\n        select 1\n          from ui_translation_resource"

    assert lock in sql
    assert guard in sql
    assert sql.index(lock) < sql.index(guard)
