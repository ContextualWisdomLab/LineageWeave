"""Focused contract tests for the single-statement Post detail reader."""

import asyncio
from datetime import datetime, timezone

from backend.app.auth import CurrentAccount
from backend.app.main import _fetch_post_detail_bundle


class _RecordingConnection:
    """Record the one statement without requiring a live database."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args: object) -> None:
        """Capture the detail statement and emulate a missing Post."""
        self.calls.append((query, args))
        return None


def test_post_detail_bundle_is_one_bound_statement_with_all_evidence() -> None:
    """ABAC, cutoff, provenance, and evidence stay inside one round trip."""
    connection = _RecordingConnection()
    account = CurrentAccount(
        user_account_id="synthetic-account",
        external_subject_id="synthetic-subject",
        display_name="Synthetic analyst",
        preferred_locale=None,
        corporate_entity_ids=frozenset({"00000000-0000-0000-0000-000000000001"}),
        process_unit_ids=frozenset({"00000000-0000-0000-0000-000000000002"}),
        permission_codes=frozenset({"post_read"}),
    )
    cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result = asyncio.run(
        _fetch_post_detail_bundle(
            connection,  # type: ignore[arg-type]
            "00000000-0000-0000-0000-000000000003",
            cutoff,
            account,
            evidence_configured=True,
        )
    )

    assert result is None
    assert len(connection.calls) == 1
    query, args = connection.calls[0]
    assert "with corpus_mode as" in query
    assert "post_occupational_construct_assertion.evidence_text" in query
    assert "post_product_mention" in query
    assert "source_post_revision" in query
    assert "evidence_post.corporate_entity_id = any($3::uuid[])" in query
    assert args == (
        "00000000-0000-0000-0000-000000000003",
        cutoff,
        ["00000000-0000-0000-0000-000000000001"],
        ["00000000-0000-0000-0000-000000000002"],
        True,
    )
