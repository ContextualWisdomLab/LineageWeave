"""Seed Demo Corp write clocks stay distinct from the January cutoff."""

from pathlib import Path

_SEED = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo_data.py"


def test_seed_demo_public_post_is_rewritten_after_the_january_cutoff() -> None:
    """After make seed, only Demo public post is the edited counter-example."""
    source = _SEED.read_text(encoding="utf-8")
    assert "0022_source_post_write_clock.sql" in source
    assert "updated_at = '2026-01-13T09:00:00Z'" in source
    assert "where post_title = 'Demo public post'" in source
    assert "updated_at = '2026-01-10T12:00:00Z'" in source
    assert "where post_title = 'Demo private post'" in source
    assert "updated_at = created_at" in source


def test_write_clock_trigger_honors_an_explicit_updated_at() -> None:
    """A body rewrite stamps now() unless the statement sets updated_at."""
    root = Path(__file__).resolve().parents[1]
    trigger = (root / "migrations" / "0022_source_post_write_clock.sql").read_text(
        encoding="utf-8"
    )
    assert "source_post_set_updated_at" in trigger
    assert "new.post_title is not distinct from old.post_title" in trigger
    assert "new.post_body is not distinct from old.post_body" in trigger
    assert "new.updated_at is not distinct from old.updated_at" in trigger
    assert "new.updated_at = now()" in trigger
