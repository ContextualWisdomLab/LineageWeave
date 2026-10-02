"""Govern the synchronous PostgreSQL TLS ADR identity and proposal status."""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXPECTED_ADR = _REPO_ROOT / "docs" / "adr" / "0366-synchronous-postgresql-default-tls.md"
_COLLIDING_ADR = _REPO_ROOT / "docs" / "adr" / "0363-synchronous-postgresql-default-tls.md"


def test_postgres_sync_tls_adr_uses_unclaimed_number_and_stays_proposed() -> None:
    """The TLS decision must not collide with ADR 0363 or pre-accept itself."""
    assert _EXPECTED_ADR.exists()
    assert not _COLLIDING_ADR.exists()

    text = _EXPECTED_ADR.read_text(encoding="utf-8")
    assert text.startswith("# ADR 0366 — Verify synchronous PostgreSQL server identity by default\n")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
