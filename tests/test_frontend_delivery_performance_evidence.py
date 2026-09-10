"""Regression contract for durable frontend delivery-performance evidence."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPOSITORY_ROOT / "docs" / "evidence" / "frontend-delivery-performance-20260910.md"


def test_frontend_delivery_performance_evidence_is_committed() -> None:
    """Keep #994 buyer-path measurements reviewable instead of local-only."""
    assert EVIDENCE_PATH.exists(), (
        "#994 requires durable buyer-path evidence; local results.tsv experiments "
        "are not release evidence"
    )


def test_frontend_delivery_performance_evidence_covers_required_buyer_paths() -> None:
    """Require the committed record to retain method, paths, and runtime observations."""
    evidence = EVIDENCE_PATH.read_text(encoding="utf-8").lower()
    required_terms = (
        "measured revision",
        "environment and method",
        "cold cache",
        "board",
        "dashboard",
        "customer master",
        "lineage",
        "ontology",
        "cited evidence",
        "javascript transfer",
        "parse/compile",
        "main thread",
        "dom",
        "p95",
        "limitations",
    )
    missing = [term for term in required_terms if term not in evidence]
    assert not missing, f"frontend delivery evidence is missing required terms: {missing}"
