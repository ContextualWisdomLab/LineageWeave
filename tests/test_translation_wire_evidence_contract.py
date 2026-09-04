"""Contracts for executable translation-cache wire evidence and baseline claims."""

from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_REAL_WIRE_TEST = _ROOT / "tests" / "test_translation_cache_recursion_real_payload.py"
_GAP_BASELINE = _ROOT / "docs" / "product-technical-gap-baseline.md"


def test_real_wire_recursion_evidence_is_runtime_portable() -> None:
    """The real-wire regression must accept either supported decoder outcome."""
    source = _REAL_WIRE_TEST.read_text(encoding="utf-8")

    assert "except RecursionError:" in source
    assert "assert isinstance(decoded, list)" in source
    assert "json.loads(raw_payload)" in source


def test_gap_baseline_does_not_transfer_unhosted_focused_pass_counts() -> None:
    """Non-terminal exact heads must not inherit local or predecessor pass totals."""
    baseline = _GAP_BASELINE.read_text(encoding="utf-8")

    assert "Focused verification is 122 passing" not in baseline
    assert "accepts either decoder outcome" in baseline
