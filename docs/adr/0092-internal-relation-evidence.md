# ADR 0031: Preserve authorized internal evidence for relation verification

- Status: Accepted
- Date: 2026-08-18
- Decision owners: LineageWeave maintainers

## Context

LLM classification of a counterparty relation and an external web search are
different signals. A web result can establish that a named organization has a
real-world footprint, but it cannot show what the organization's relationship
was in this product's own corpus. The popup therefore needs an internal source
post without replacing the external verification status.

## Decision

`POST /api/posts/{post_id}/verify-relations` searches normalized source-post
text, including persisted DOM/image descriptions, for the organization name
and relationship label. It considers public posts and private posts in the
requesting account's affiliated corporate entities only. At most one matching
post id is stored in `post_counterparty_entity.verification_evidence_post_id`.

The existing `verification_status_code` and
`verification_evidence_url` remain the external-search result. Internal
evidence is additive metadata, never a fabricated external corroboration and
never a reason to expose an unauthorized post. Reclassification clears the
internal evidence together with the stale external result.

## Consequences

- The counterparty panel can open the internal evidence post directly.
- The database retains provenance for both evidence paths without encoding an
  internal post as a fake URL.
- The current implementation is lexical retrieval over normalized text; a
  future semantic retrieval upgrade must preserve the same authorization and
  separate-signal contract.

## Evidence

- `migrations/0028_internal_relation_evidence.sql`
- `backend/app/relation_verification_ingestion.py`
- `tests/test_relation_verification_internal.py`
