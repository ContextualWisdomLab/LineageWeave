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
