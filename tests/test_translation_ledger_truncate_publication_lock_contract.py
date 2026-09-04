"""Hosted lock-order contract for translation TRUNCATE versus publication."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = ROOT / "migrations" / "0247_ui_translation_truncate_guard.sql"


def test_truncate_guard_locks_resource_before_published_state_snapshot() -> None:
    """Serialize resource UPDATE before the READ COMMITTED publication-state check."""
    sql = _MIGRATION.read_text(encoding="utf-8").lower()
    lock = "lock table ui_translation_resource in share mode;"
    published_check = "if exists ("

    assert lock in sql
    assert published_check in sql
    assert sql.index(lock) < sql.index(published_check)
