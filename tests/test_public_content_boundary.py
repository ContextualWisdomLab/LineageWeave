"""Public-git denylist for the analysis-run registry slice.

The registry may mention synthetic Demo Corp and aggregate ranges. It must
not ship source-export table names, industrial-group or source-org names,
raw row identifiers, image bytes, credentials, or exact private counts.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCAN_ROOTS = (
    _ROOT / "docs",
    _ROOT / "migrations",
    _ROOT / "lineageweave",
    _ROOT / "CHANGELOG.md",
    _ROOT / "CHANGELOG.d",
    _ROOT / "ARCHITECTURE.md",
    _ROOT / "README.md",
)
_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".lock"}
_BASE64_IMAGE = re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/]{80,}")
_CREDENTIAL_DSN = re.compile(r"postgres(?:ql)?://[^/\s:]+:[^@\s/]+@")
_EXACT_PRIVATE_COUNT = re.compile(
    r"\bexactly\s+\d{3,}\s+(?:rows?|documents?|threads?|nodes?|edges?)\b",
    re.IGNORECASE,
)
_RAW_ROW_ID = re.compile(
    r"\b(?:row_id|source_row_id|export_row_id)\s*[:=]\s*['\"]?\d{4,}",
    re.IGNORECASE,
)
_FORBIDDEN_ASSEMBLED = (
    ("source_export", "_"),
    ("src_export", "_"),
    ("industrial", "_group"),
    ("source_org", "_name"),
)


def _iter_public_text_files() -> list[Path]:
    """Return committed-style text files in the public documentation surface."""

    files: list[Path] = []
    for root in _SCAN_ROOTS:
        if root.is_file():
            files.append(root)
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() in _SKIP_SUFFIXES:
                continue
            try:
                path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            files.append(path)
    return files


def test_public_registry_surface_keeps_private_source_material_out() -> None:
    """Docs, migrations, and package text stay inside the synthetic boundary."""

    allowed_demo = "Demo Corp"
    findings: list[str] = []
    for path in _iter_public_text_files():
        text = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(_ROOT))
        if _BASE64_IMAGE.search(text):
            findings.append(f"{relative}: base64 image payload")
        if _CREDENTIAL_DSN.search(text) and "lineageweave_dev_only" not in text:
            findings.append(f"{relative}: credential-shaped DSN")
        if "COPILOT_GITHUB_TOKEN" in text:
            findings.append(f"{relative}: COPILOT_GITHUB_TOKEN")
        if _EXACT_PRIVATE_COUNT.search(text):
            findings.append(f"{relative}: exact private count")
        if _RAW_ROW_ID.search(text):
            findings.append(f"{relative}: raw row identifier")
        for left, right in _FORBIDDEN_ASSEMBLED:
            if f"{left}{right}" in text:
                findings.append(f"{relative}: forbidden {left}{right}")
        if "Corp" in text and allowed_demo not in text and "Test Corp" not in text:
            if re.search(r"\b[A-Z][A-Za-z]+ Corp\b", text):
                # Synthetic Acme appears in the 0001 schema commentary only.
                if "Acme" not in text and relative != "migrations/0001_initial_schema.sql":
                    findings.append(f"{relative}: non-demo corporate name")
    assert findings == []


def test_registry_docs_allow_only_aggregate_ranges() -> None:
    """Buyer-facing registry docs speak in ranges, not private cardinalities."""

    registry_docs = [
        _ROOT / "docs" / "analysis-run-registry.md",
        _ROOT / "docs" / "adr" / "0014-normalized-analysis-run-registry.md",
        _ROOT / "docs" / "doctoring" / "ANALYSIS_RUN_REGISTRY_REFERENCES.md",
    ]
    for path in registry_docs:
        text = path.read_text(encoding="utf-8")
        assert path.is_file()
        assert "aggregate" in text.casefold()
        assert not _EXACT_PRIVATE_COUNT.search(text)
