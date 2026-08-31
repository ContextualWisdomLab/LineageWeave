"""Persist receipt-bearing derived Voice assertions and their history."""

from __future__ import annotations

from typing import Any, Protocol

from lineageweave.voice_classification import VoiceClassificationResult


class _Transaction(Protocol):
    async def __aenter__(self) -> Any:
        """Enter a database transaction."""
        raise NotImplementedError

    async def __aexit__(self, *args: object) -> bool:
        """Leave a database transaction."""
        raise NotImplementedError


class _Connection(Protocol):
    def transaction(self) -> _Transaction:
        """Create a database transaction context."""
        raise NotImplementedError

    async def fetchval(self, query: str, *args: object) -> Any:
        """Fetch one scalar value."""
        raise NotImplementedError

    async def fetch(self, query: str, *args: object) -> list[Any]:
        """Fetch current derived assertion rows."""
        raise NotImplementedError

    async def execute(self, query: str, *args: object) -> str:
        """Execute one persistence statement."""
        raise NotImplementedError


async def persist_derived_voice_classification(
    conn: _Connection,
    post_id: str,
    result: VoiceClassificationResult,
) -> None:
    """Replace only current derived assertions after locking the exact source revision."""
    async with conn.transaction():
        current_digest = await conn.fetchval(
            "select encode(sha256(convert_to(coalesce(post_body, ''), 'UTF8')), 'hex') "
            "from source_post where post_id = $1::uuid for update",
            post_id,
        )
        if current_digest != result.source_revision_digest:
            raise ValueError(
                "derived Voice result no longer matches the source revision"
            )
        prior_rows = await conn.fetch(
            "select classification_assertion_id, voice_concept_code "
            "from post_voice_classification_assertion where post_id = $1::uuid "
            "and assertion_status_code = 'derived' and valid_to is null for update",
            post_id,
        )
        prior_by_code = {
            str(row["voice_concept_code"]): row["classification_assertion_id"]
            for row in prior_rows
        }
        await conn.execute(
            "update post_voice_classification_assertion set valid_to = clock_timestamp() "
            "where post_id = $1::uuid and assertion_status_code = 'derived' and valid_to is null",
            post_id,
        )
        for assertion in result.assertions:
            await conn.execute(
                "insert into post_voice_classification_assertion "
                "(post_id, voice_concept_code, assertion_status_code, evidence_span_start, "
                "evidence_span_end, evidence_sha256, source_revision_digest, "
                "orchestrator_model_receipt, supersedes_assertion_id) "
                "values ($1::uuid, $2, 'derived', $3, $4, $5, $6, $7, $8)",
                post_id,
                assertion.voice_concept_code,
                assertion.evidence_span_start,
                assertion.evidence_span_end,
                assertion.evidence_sha256,
                result.source_revision_digest,
                result.orchestrator_model_receipt,
                prior_by_code.get(assertion.voice_concept_code),
            )
        await conn.execute(
            "insert into post_voice_classification_analysis "
            "(post_id, source_body_sha256, orchestrator_model_receipt, assertion_count) "
            "values ($1::uuid, $2, $3, $4) on conflict (post_id) do update set "
            "source_body_sha256 = excluded.source_body_sha256, "
            "orchestrator_model_receipt = excluded.orchestrator_model_receipt, "
            "assertion_count = excluded.assertion_count, analyzed_at = clock_timestamp()",
            post_id,
            result.source_revision_digest,
            result.orchestrator_model_receipt,
            len(result.assertions),
        )
