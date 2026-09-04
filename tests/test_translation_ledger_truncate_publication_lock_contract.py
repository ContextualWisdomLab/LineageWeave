"""Hosted lock-order contract for translation TRUNCATE versus publication."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = ROOT / "migrations" / "0247_ui_translation_truncate_guard.sql"


def test_truncate_guard_uses_nonblocking_resource_admission_before_snapshot() -> None:
    """Fail child TRUNCATE closed instead of deadlocking with an active publisher."""
    sql = _MIGRATION.read_text(encoding="utf-8").lower()
    lock = "lock table ui_translation_resource in share mode nowait;"
    contention = "when sqlstate '55p03' then"
    domain_error = "child ui translation relations cannot be truncated"
    published_check = "if exists ("

    assert lock in sql
    assert contention in sql
    assert domain_error in sql
    assert published_check in sql
    assert sql.index(lock) < sql.index(published_check)
