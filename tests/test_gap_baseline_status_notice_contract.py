"""Contracts that keep the current ADR 0134 gap classification code-current."""

from pathlib import Path


_BASELINE = Path(__file__).parents[1] / "docs" / "product-technical-gap-baseline.md"


def test_adr_0134_gap_row_acknowledges_shared_status_notice_delivery() -> None:
    """Do not report the protected shared StatusNotice as still absent."""

    rows = [
        line
        for line in _BASELINE.read_text(encoding="utf-8").splitlines()
        if line.startswith("| ADR 0134 token-backed exception messages |")
    ]

    assert len(rows) == 1
    row = rows[0]
    assert "StatusNotice" in row
    assert "no shared token-backed exception component" not in row
