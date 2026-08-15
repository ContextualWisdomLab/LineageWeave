"""Bind the accepted product contract to concrete Figma pages and claims."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = (
    _ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-08-14-db-grounded-product-ux-design.md"
)


def test_figma_page_nodes_are_part_of_the_accepted_contract() -> None:
    """The canonical and archived pages must be unambiguous in automation."""
    content = _SPEC.read_text(encoding="utf-8")
    assert "**Canonical Figma page node:** `9:2`" in content
    assert "**Archive Figma page node:** `0:1`" in content
    assert "**Last contract synchronization:** `2026-08-15`" in content


def test_figma_contract_archives_unsupported_product_claims() -> None:
    """Attractive unmodeled screens stay archived rather than becoming claims."""
    content = _SPEC.read_text(encoding="utf-8")
    for statement in (
        "Graph change history, the PROV-O product explorer, and access audit remain archived",
        "The canonical role vocabulary is `viewer` and `admin`; Figma does not fabricate an `Analyst` role.",
        "Direct lineage remains a plausible parent-child reconstruction, never a causal claim.",
    ):
        assert statement in content
