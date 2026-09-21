"""Executable ownership checks for the live product-gap validation overlay."""

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_PRODUCT_GAP_BASELINE = _ROOT / "docs" / "product-technical-gap-baseline.md"
_LATEST_VALIDATION_MARKER = "> Exact-head validation overlay:"


def _latest_validation_overlay() -> str:
    """Return only the newest validation overlay, leaving older snapshots immutable."""
    baseline = _PRODUCT_GAP_BASELINE.read_text(encoding="utf-8")
    _, separator, tail = baseline.partition(_LATEST_VALIDATION_MARKER)
    assert separator, "product-gap baseline must publish a validation overlay"
    return separator + tail.split("\n> Exact-head validation overlay:", 1)[0]


def test_latest_validation_overlay_records_released_orchestrator_consumer_gap() -> None:
    """A local CO wire client cannot be promoted while the owner has no release."""
    overlay = _latest_validation_overlay().replace("\n> ", " ")

    assert "`c943060c7c16f74faf48d1ee40eaa5301c830065`" in overlay
    assert "contextual-orchestrator#1083" in overlay
    assert "Releases API" in overlay and "`[]`" in overlay
    assert "/v1/chat/completions" in overlay
    assert "`180.0s`" in overlay
    assert "released API/client/schema" in overlay
    assert "bind to mutable `main`" in overlay
