"""Seed Demo Corp write clocks stay distinct from the January cutoff."""

from pathlib import Path

_SEED = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo_data.py"


def test_seed_demo_public_post_is_rewritten_after_the_january_cutoff() -> None:
    """After make seed, only Demo public post is the edited counter-example."""
    source = _SEED.read_text(encoding="utf-8")
    assert "updated_at = '2026-01-13T09:00:00Z'" in source
    assert "where post_title = 'Demo public post'" in source
    assert "updated_at = '2026-01-10T12:00:00Z'" in source
    assert "where post_title = 'Demo private post'" in source
