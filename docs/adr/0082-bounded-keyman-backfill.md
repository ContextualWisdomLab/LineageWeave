# ADR 0082: Bounded Keyman backfill through the contextual-orchestrator boundary

- Status: Accepted
- Date: 2026-08-20

## Context

The buyer Customer Master can use source-author/account information as a hint,
but a source-author code is not a person identity. Actual Keyman evidence must
come from the existing Keyman extraction and persistence projection. Imported
real data has many posts without a `post_person_mention` row, so relying only
on the per-post operator button leaves the author-group view mostly empty.

## Decision

Provide `scripts/backfill_post_keymen.py` as an operator-only, bounded runner.
It will:

- select eligible, non-deleted, non-draft posts that have no existing
  `post_person_mention`, or one explicit `--post-id`;
- normalize HTML, OOXML-derived text, embedded images, and image regions with
  the existing VISION normalization path before extraction;
- pass source author, account, PU, sales-pool, customer, company, and project
  context through the existing semantic-hints loader as priors, never facts;
- call `ContextualOrchestratorKeymanExtractionClient` and the existing
  `ingest_post_keymen` write path, including catalog identity and graph
  reconciliation;
- carry `build_post_llm_metadata` and `use_llm_metadata` across all LLM/VISION
  calls for one post, yielding the same deterministic post session id;
- default to one post and require explicit `--all --limit N` for a batch;
- admit a batch limit only as an exact integer in the inclusive `1..100`
  range, applying the same check to direct programmatic runner calls before
  gateway or database work. The upper bound keeps one invocation genuinely
  bounded even when a caller bypasses the CLI; larger work is split into
  repeated observable invocations instead of turning one process into an
  effectively unbounded serial crawl;
- require the programmatic batch-mode selector to be an exact boolean before
  using its truth value, so strings or integer-like transport values cannot
  silently switch a direct call into or out of batch mode;
- enforce one admitted per-post timeout across the operator and its Keyman
  contextual-orchestrator transport. The transport must not impose an
  unrelated shorter fixed timeout that can terminate a valid long-running
  model workflow before the operator's explicit administrative budget;
- return a typed timeout failure count instead of allowing a provider workflow
  to hold an operator process indefinitely.

Gateway credentials are read from runtime-injected environment variables. The
script never reads or copies `~/.env`, and it is not exposed as a buyer HTTP
route. No analysis-run registry tables are modified.

## Consequences

- Keyman coverage can be increased incrementally with a bounded cost and
  auditable operator output. One invocation processes at most 100 posts; larger
  backfills require repeated invocations whose result summaries remain
  independently attributable.
- Empty extraction remains a real empty result; the script does not create a
  placeholder person or retry indefinitely through an implicit attempt table.
- Re-running a selected post is idempotent through `ingest_post_keymen`'s
  replacement semantics, while the default selector may revisit an empty
  extraction because no evidence row exists.
- A provider workflow that exceeds the operator-selected timeout is recorded as
  unavailable for that attempt; it is not converted into an empty Keyman
  result, and an unrelated client-local fixed timeout does not pre-empt that
  budget.
