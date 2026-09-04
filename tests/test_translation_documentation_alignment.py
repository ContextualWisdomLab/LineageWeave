"""Code-current documentation contracts for the versioned translation slice."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_REAL_WIRE_TEST = ROOT / "tests" / "test_translation_cache_recursion_real_payload.py"


def _between(text: str, start: str, end: str) -> str:
    """Return one named current-evidence section without accepting historical decoys."""
    _, separator, remainder = text.partition(start)
    if not separator:
        raise AssertionError(f"missing section start: {start}")
    section, separator, _ = remainder.partition(end)
    if not separator:
        raise AssertionError(f"missing section end: {end}")
    return section


def _real_wire_test_has_structural_recursion_proof(source: str) -> bool:
    """Return whether raw JSON decoding is inside pytest.raises(RecursionError)."""
    module = ast.parse(source)
    for node in ast.walk(module):
        if not isinstance(node, ast.With):
            continue
        raises_recursion = False
        for item in node.items:
            context = item.context_expr
            if not isinstance(context, ast.Call):
                continue
            function = context.func
            if not (
                isinstance(function, ast.Attribute)
                and isinstance(function.value, ast.Name)
                and function.value.id == "pytest"
                and function.attr == "raises"
                and context.args
                and isinstance(context.args[0], ast.Name)
                and context.args[0].id == "RecursionError"
            ):
                continue
            raises_recursion = True
            break
        if not raises_recursion:
            continue
        for statement in node.body:
            for nested in ast.walk(statement):
                if not isinstance(nested, ast.Call):
                    continue
                function = nested.func
                if not (
                    isinstance(function, ast.Attribute)
                    and isinstance(function.value, ast.Name)
                    and function.value.id == "json"
                    and function.attr == "loads"
                    and len(nested.args) == 1
                    and isinstance(nested.args[0], ast.Name)
                    and nested.args[0].id == "raw_payload"
                ):
                    continue
                return True
    return False


def test_translation_gap_baseline_tracks_authenticated_api_slice() -> None:
    """The buyer-gap baseline must not describe an already implemented API as absent."""
    api_source = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    baseline = (ROOT / "docs" / "product-technical-gap-baseline.md").read_text(
        encoding="utf-8"
    )

    assert '@app.get("/api/translations/{screen_key}")' in api_source
    assert "does not yet provide the authenticated PostgreSQL API" not in baseline
    assert "`GET /api/translations/{screen_key}`" in baseline


def test_translation_gap_baseline_scopes_current_929_review_boundary() -> None:
    """The current #929 snapshot itself must carry review and GREEN limitations."""
    baseline = (ROOT / "docs" / "product-technical-gap-baseline.md").read_text(
        encoding="utf-8"
    )
    current_snapshot = _between(
        baseline,
        "# Product & Technical Gap Baseline\n\n",
        "> Two adjacent candidates remain outside protected `main`:",
    )
    normalized = " ".join(current_snapshot.split())

    assert "PR #929" in normalized
    assert "open / Ready with normal squash auto-merge armed" in normalized
    assert "terminal GREEN" in normalized
    assert "qualifying independent review" in normalized
    assert "not protected-main, deployed, or release evidence" in normalized


def test_translation_gap_baseline_tracks_live_adjacent_postgres_candidate() -> None:
    """The current adjacent-candidate block must not pin #911 to a predecessor head."""
    baseline = (ROOT / "docs" / "product-technical-gap-baseline.md").read_text(
        encoding="utf-8"
    )
    adjacent = _between(
        baseline,
        "> Two adjacent candidates remain outside protected `main`:",
        "> Historical baseline overlays through the preceding snapshot are preserved as",
    )

    assert "`5d40eed35a0b6e0d182397f8d02b29c38e9bdd17`" in adjacent
    assert "`034dfc42f78c89f315bf06836c71c838de9dfd72`" not in adjacent


def test_translation_real_wire_evidence_is_structurally_bound_to_decoder_failure() -> None:
    """The actual raw payload decode must execute inside the recursion assertion."""
    source = _REAL_WIRE_TEST.read_text(encoding="utf-8")

    assert _real_wire_test_has_structural_recursion_proof(source)


def test_translation_history_has_no_blank_lines_inside_blockquotes() -> None:
    """Historical Markdown must satisfy the repository blockquote lint gate."""
    history = (
        ROOT / "docs" / "product-technical-gap-baseline-history-2026-09-04.md"
    ).read_text(encoding="utf-8")

    assert ">\n\n>" not in history


def test_translation_history_raw_archive_preserves_original_git_blob() -> None:
    """Lint repair must retain the former historical baseline byte-for-byte."""
    raw_history = (
        ROOT / "docs" / "product-technical-gap-baseline-history-2026-09-04.raw.txt"
    ).read_bytes()
    git_object = f"blob {len(raw_history)}\0".encode() + raw_history

    assert hashlib.sha1(git_object, usedforsecurity=False).hexdigest() == (
        "ee48bf0fcd01d9a0c511c6f70970994878965cf8"
    )
