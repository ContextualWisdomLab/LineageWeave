# ADR 0112 — Authoritative project-lifecycle ingestion boundary

- Status: Proposed on Issue #284 and stacked PR #285; not protected-main behavior
- Date: 2026-08-20
- Figma file: `SBpgot7uTvMxEaxUwvoc0S` (reuses the project-history evidence boundary in ADR 0111; no new UI surface)

## Context

Project History needs a source-owned event clock and lifecycle records for
orders, specification changes, delivery, VOC, and rebids. Title/body
classification and an LLM can suggest a candidate, but neither is an
authoritative write source. Re-imports must be safe when a source changes its
record, and withdrawal must remove only the projection owned by that source
record while preserving independent evidence.

## Decision

1. Require an explicit project key/name, source system and source record key,
   versioned source event code, offset-aware start/end, and a source-post
   evidence row before writing.
2. Resolve external event codes through `project_event_mapping`. Unknown or
   inactive codes fail closed; the writer does not inspect titles, bodies, or
   call a model.
3. Store the project identity, source system, mapping, source record, event,
   evidence, actor, relation, responsibility, and audit facts in separate
   third-normal-form tables. A source-system/record advisory transaction lock
   makes concurrent imports converge on one projection.
4. Re-importing the same source identity replaces its event, relations, and
   responsibilities atomically and records before/after digests. Withdrawal
   deletes the owned event projection and marks the source record withdrawn;
   independent source records remain available.
5. Keep the writer behind the dedicated `project_lifecycle_write` permission.
   This PR adds the adapter and migration only; an authenticated application
   route must bind that permission to the existing administrator policy before
   exposing writes to a deployment.

## Consequences

- Buyers can distinguish observed source lifecycle evidence from inferred
  project mentions and follow a deterministic event clock.
- A bad mapping, cross-project relation, mismatched evidence post, or missing
  permission fails without a partial write.
- Audit rows retain aggregate digests and actor keys, not copied source bodies.
- The current read model can adopt these records after this stacked change is
  reviewed and merged through the protected order; this ADR does not claim
  protected-main or production availability.

## Verification

- `tests/test_project_lifecycle_ingestion.py` exercises real PostgreSQL
  mapping, permission, evidence, idempotent replacement, concurrent import,
  cross-project rejection, and withdrawal behavior with synthetic identities.
- `tests/test_migration_replay.py` verifies that Compose replays migration
  0054 on existing volumes.
- `python -m compileall`, `git diff --check`, and the repository's backend and
  frontend gates remain required before the stacked PR can be reviewed.

## References

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2013). *PROV-DM: The PROV data model*.
https://www.w3.org/TR/prov-dm/
