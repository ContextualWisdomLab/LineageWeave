# ADR 0075: Exclude pure synthetic seed rows at the read boundary

- Status: Accepted
- Date: 2026-08-19

## Context

The real import can share a historical `DEMO-*` corporate entity with seed
rows. Analysis-run snapshot and lineage tables are immutable and must not be
deleted or rewritten automatically. Leaving pure seed posts in ordinary buyer
reads makes fabricated records appear beside real evidence.

## Decision

The shared `SOURCE_POST_ELIGIBILITY_SQL` boundary excludes a `source_post` row
when every `source_*` context field is blank and at least one source post with
real context exists. The rule is applied to buyer reads that already use the
shared eligibility clause, including board, lineage, and evidence retrieval.

The rule does not mutate `analysis_run`, snapshot, or lineage registry tables.
Synthetic-only installations remain readable because the exclusion activates
only after real source context exists. Import-time cleanup remains the explicit
row-level deletion path for unreferenced synthetic rows; referenced rows stay
blocked for operator review.
