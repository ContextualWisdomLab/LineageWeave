"""Regression contract for durable frontend delivery-performance evidence."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPOSITORY_ROOT / "docs" / "evidence" / "frontend-delivery-performance-20260910.md"


def _evidence_text() -> str:
    """Read the dated evidence only after proving the review artifact exists."""
    assert EVIDENCE_PATH.exists(), (
        "#994 requires durable buyer-path evidence; local results.tsv experiments "
        "are not release evidence"
    )
    return EVIDENCE_PATH.read_text(encoding="utf-8").lower()


def test_frontend_delivery_performance_evidence_is_committed() -> None:
    """Keep #994 buyer-path measurements reviewable instead of local-only."""
    assert EVIDENCE_PATH.exists(), (
        "#994 requires durable buyer-path evidence; local results.tsv experiments "
        "are not release evidence"
    )


def test_frontend_delivery_performance_evidence_covers_required_buyer_paths() -> None:
    """Require the committed record to retain method, paths, and runtime observations."""
    evidence = _evidence_text()
    required_terms = (
        "measured revision",
        "environment and method",
        "cold cache",
        "board",
        "dashboard",
        "customer master",
        "cited evidence",
        "javascript transfer",
        "dom",
        "p95",
        "limitations",
    )
    missing = [term for term in required_terms if term not in evidence]
    assert not missing, f"frontend delivery evidence is missing required terms: {missing}"

    assert "lineage" in evidence or "ontology" in evidence, (
        "frontend delivery evidence must cover the Lineage/ontology buyer path"
    )
    assert any(term in evidence for term in ("parse/compile", "parse and compile", "parse + compile")), (
        "frontend delivery evidence must retain parse/compile observations"
    )
    assert "main thread" in evidence or "main-thread" in evidence, (
        "frontend delivery evidence must retain main-thread observations"
    )
