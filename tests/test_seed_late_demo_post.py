"""#110 cutoff counter-example stays in the Demo Corp seed."""

from pathlib import Path

_SEED_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo_data.py"


def test_seed_includes_late_demo_public_post_after_cutoff() -> None:
    """Late Demo public post is dated after the January 12 knowledge cutoff."""
    seed = _SEED_SCRIPT.read_text(encoding="utf-8")
    assert "Late Demo public post" in seed
    assert 'late_demo_post_created_at = "2026-01-13T09:00:00Z"' in seed
    assert "2026-01-12T12:00:00Z" in seed
