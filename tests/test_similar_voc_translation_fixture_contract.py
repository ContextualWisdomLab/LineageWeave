"""Structural contract keeping Similar VOC PostgreSQL evidence on the parent migration path."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = ROOT / "tests" / "test_similar_voc_translation_seed.py"


def test_similar_voc_fixture_includes_current_parent_guard_chain() -> None:
    """The seed scenarios must include every parent guard added before migration 0249."""
    source = _FIXTURE.read_text(encoding="utf-8")
    start = source.index("async def _apply_base")
    end = source.index("async def _run_in_database", start)
    apply_base = source[start:end]

    assert "_OWNERSHIP_TRUNCATE_GUARD_MIGRATION" in apply_base
    assert "_CUSTOMER_MASTER_REPLAY_GUARD_MIGRATION" in apply_base
