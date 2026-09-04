"""Code-current documentation contracts for the versioned translation slice."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_translation_gap_baseline_tracks_authenticated_api_slice() -> None:
    """The buyer-gap baseline must not describe an already implemented API as absent."""
    api_source = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    baseline = (ROOT / "docs" / "product-technical-gap-baseline.md").read_text(
        encoding="utf-8"
    )

    assert '@app.get("/api/translations/{screen_key}")' in api_source
    assert "does not yet provide the authenticated PostgreSQL API" not in baseline
    assert "`GET /api/translations/{screen_key}`" in baseline


def test_translation_gap_baseline_keeps_unreviewed_candidate_draft() -> None:
    """Non-terminal evidence must never be documented as merge-ready."""
    baseline = (ROOT / "docs" / "product-technical-gap-baseline.md").read_text(
        encoding="utf-8"
    )

    assert "open / ready" not in baseline
    assert "open / Draft" in baseline


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
