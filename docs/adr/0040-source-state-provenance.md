# ADR 0040: Preserve raw source post state separately

- Status: Accepted
- Date: 2026-08-18

## Context

The source export contains separate raw fields for stage, detail state, draft
or property markers, and deletion markers. The target `source_post` schema had
discarded them, so the Board could neither show the source state nor establish
whether a record was a temporary save. The available source evidence contains
codes but no authoritative code-to-label table for these fields.

## Decision

- Preserve each caller-mapped raw field in its own nullable `source_post`
  column: `source_stage_code`, `source_detail_state_code`,
  `source_draft_code`, and `source_deleted_flag`.
- Expose these fields in the authorized post list and detail payloads, and show
  them in the Board/detail view as raw source codes.
- Do not infer `published`, `draft`, or `temporary save` from an unverified
  code, and do not filter a record out based on that inference.
- Add a source-specific label mapping or exclusion rule only when the source
  system supplies an authoritative lookup or an explicit caller mapping. The
  PostgreSQL importer accepts repeated `--exclude-draft-value` and
  `--exclude-deleted-value` arguments for this purpose, compares them only to
  the caller-mapped raw fields, and reports skipped rows in its aggregate
  output. It never deletes a previously imported target row as a side effect.

## Consequences

The product can inspect original state evidence without losing distinctions
between lifecycle dimensions. Until a source codebook is provided, users see
codes rather than invented labels and the Board remains complete rather than
silently excluding records.

## Product display mapping

For the current Board workflow, the product owner supplied a display
interpretation for the observed detail-state codes:

- `W` — Writing in progress (`작성 중`)
- `D` — Pending approval (`결재 중`)
- `A` — Approved (`결재 완료`)

This is a reader-facing explanation, not a rewrite of the raw source field or
an assertion that the source system's full codebook has been verified. The API
continues to return the raw code, unknown codes remain visible as unmapped, and
`source_draft_code` remains a separate signal. The Board may filter by the raw
detail-state code while showing this mapping beside it.

## Writing-state access and derivation boundary

W is an original-source record that is still being written. It is not a
service target. The author account and post_admin may open the raw source
record so the author can continue reviewing their own work, but W is excluded
from all derived reads and writes: summaries, 5W1H, ontology/Keyman and
relationship extraction, knowledge-graph projections, lineage, rankings,
reports, calendar commitments, chat/Ask sources, and content-analysis
projections. A persisted summary does not make W eligible; the API refuses
analysis requests and the summary backfill query excludes W. D and A remain
the service summary targets.
