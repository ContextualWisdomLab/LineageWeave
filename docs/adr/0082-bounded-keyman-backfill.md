# ADR 0082: Bounded Keyman backfill through the contextual-orchestrator boundary

- Status: Accepted
- Date: 2026-08-20

## Context

The buyer Customer Master can use source-author/account information as a hint,
but a source-author code is not a person identity. Actual Keyman evidence must
come from the existing Keyman extraction and persistence projection. Imported
real data has many posts without a `post_person_mention` row, so relying only
on the per-post operator button leaves the author-group view mostly empty.

ADR 0046 defines `source_post.post_id` as the internal UUID identity and keeps
that UUID distinct from an opaque source-system record key. An operator selector
therefore must not accept arbitrary opaque text or alternate UUID spellings as
though they were the internal post identity.

## Decision

Provide `scripts/backfill_post_keymen.py` as an operator-only, bounded runner.
It will:

- select eligible, non-deleted, non-draft posts that have no existing
  `post_person_mention`, or one explicit `--post-id`;
- admit an explicit `--post-id` only when it is the canonical lowercase,
  hyphenated UUID text for the ADR 0046 internal post identity. Blank, padded,
  malformed, uppercase, braced, and hyphenless aliases fail before gateway or
  database work rather than being normalized into a different textual
  identity;
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
- reject a non-default `--limit` unless batch mode is explicitly selected with
  `--all`. The same cross-field admission applies to direct programmatic calls,
  so a requested limit cannot be silently ignored by falling back to the
  default one-post mode. `--post-id` and `--all` remain mutually exclusive;
- require the programmatic batch-mode selector to be an exact boolean before
  using its truth value, so strings or integer-like transport values cannot
  silently switch a direct call into or out of batch mode;
- admit the per-post administrative timeout only when validation itself is
  total: malformed direct-call values, including an integer too large for the
  runtime finite-number check, fail closed instead of escaping admission with
  an arithmetic exception before the operator can return its normal validation
  error;
- enforce one admitted per-post timeout across the operator and its Keyman and
  Vision contextual-orchestrator transports. Neither synchronous Vision work
  nor Keyman extraction may impose an unrelated shorter fixed timeout that can
  terminate a valid long-running workflow before the operator's explicit
  administrative budget;
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
- An explicit non-default batch size is either honored under `--all` or rejected
  before external work; it is never accepted and then silently collapsed to a
  one-post execution.
- Explicit reruns use one stable textual form for the internal UUID in operator
  logs and LLM metadata; source-system record keys remain separate ADR 0046
  evidence and are never accepted as `--post-id`.
- Empty extraction remains a real empty result; the script does not create a
  placeholder person or retry indefinitely through an implicit attempt table.
- Re-running a selected post is idempotent through `ingest_post_keymen`'s
  replacement semantics, while the default selector may revisit an empty
  extraction because no evidence row exists.
- A provider workflow that exceeds the operator-selected timeout is recorded as
  unavailable for that attempt; it is not converted into an empty Keyman
  result, and unrelated client-local fixed timeouts do not pre-empt that
  budget.
- Programmatic timeout admission remains fail-closed even for numeric values
  whose magnitude cannot be represented by the runtime finite-number helper;
  validation does not leak an `OverflowError` as an alternate control path.
