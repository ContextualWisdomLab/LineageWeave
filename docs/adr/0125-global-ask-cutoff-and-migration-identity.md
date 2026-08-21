# ADR 0125 — Bind Global Ask cutoffs and keep migration identities unique

**Decision status:** Accepted on the PR #342 repair branch  
**Date:** 2026-08-21  
**Figma File ID:** N/A — this is a backend, migration, and operability decision.

## Context

Global Ask restricts source posts by the requested knowledge cutoff. Its final
PostgreSQL query used the `$4` cutoff placeholder but supplied only three
arguments, so a real PostgreSQL execution could fail before returning any
authorized evidence. The same branch also introduced a second forward
migration with numeric prefix `0053`, colliding with an existing migration.
Temporary self-modifying workflows were compensating for both defects after a
push rather than leaving the branch itself correct.

## Decision

1. Bind the cutoff as the fourth argument of the final Global Ask source query.
2. Assign the cutoff schema change the next unique forward migration identity,
   `0054`, and update rollback, migration dispatch, and contract tests.
3. Keep reproduction and regression checks in committed tests. Do not use a
   workflow that edits, commits, pushes, or deletes product source at runtime.

## Consequences

- Global Ask fails neither at PostgreSQL parameter binding nor by silently
  dropping the requested knowledge cutoff.
- Migration replay and rollback address one numeric identity unambiguously.
- Hosted CI evaluates the exact committed source instead of a workflow-mutated
  branch state.

## Verification

- The synthetic query contract asserts the fourth argument is the requested
  cutoff.
- The PostgreSQL integration contract executes the final query against a real
  local PostgreSQL parser when `LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN` is set.
- Migration identity tests reject duplicate numeric prefixes and require the
  `0054_*` dispatch path.
