# ADR 0372: Canonical migration identity after a shipped ordinal collision

- Status: Proposed
- Date: 2026-09-12
- Decision owners: LineageWeave database/operability boundary
- Related: #1048, PR #1049, ADR 0166

## Context

Protected `main@83eba56149eb802cd63642c507c324c9976ec78e` contains two executable root migrations whose filenames both begin with ordinal `0233`:

- `0233_report_leftover_map_unexplained_share.sql`;
- `0233_source_conversation_turn_evidence.sql`.

The replay service does not currently collapse these files: `migrate.sh` iterates every qualifying `NNNN_*.sql` filename. The defect is migration identity rather than an observed missing schema delta. The filenames are also referenced by tests, rollback files, seed tooling, PR/ADR history, and buyer/audit evidence, so deleting or silently renaming an already-shipped path would create a different compatibility problem.

At this decision point, active translation-ledger work reserves migrations 0246–0247. A live repository/PR inventory found no current `0248_*` migration authority, so this repair uses 0248 for the later source-conversation delta. This reservation must be rechecked before promotion if concurrent work moves.

## Constraints

- Existing databases that already executed the historical source-conversation `0233` must upgrade without a divergent second schema effect.
- Fresh databases and existing-volume replay must converge to the same effective schema.
- Historical file references should remain resolvable in the current tree.
- Canonical forward migrations need a unique ordinal namespace so tooling and release evidence can identify one migration unambiguously.
- Rollback discoverability must remain deterministic.
- The replay gate remains POSIX `/bin/sh`; no database migration ledger is introduced by this repair because all affected SQL is already replay-safe and a ledger would be a broader operational migration.
- Production replay keeps `/opt/lineageweave/migrations` as its no-argument authority. A caller may pass one explicit migration-root argument only so recovery rehearsal and repository integration tests can exercise the exact production replay loop against an isolated migration set instead of reimplementing that loop.

## Alternatives considered

### Leave both `0233` files unchanged

Rejected. Both SQL files happen to replay idempotently, but the ordinal no longer identifies one migration. The ambiguity already leaks into documentation, rollback naming, and any tool that reasons by numeric migration identity.

### Delete or directly rename the later `0233` file

Rejected. Git history would preserve the old path, but current-checkout tests, rollback/tooling references, and external audit procedures could still rely on the shipped filename. A destructive rename provides no executable compatibility contract.

### Keep the historical path as an explicit alias and add a unique canonical migration

Chosen. The historical `0233_source_conversation_turn_evidence.sql` remains executable for manual/audit compatibility but declares `0248_source_conversation_turn_evidence.sql` as its canonical replacement. Runtime replay recognizes the declaration and skips the alias, then applies the canonical 0248 migration. The canonical and historical SQL bodies and rollback bodies must remain equivalent under test.

## Decision

1. `0248_source_conversation_turn_evidence.sql` becomes the canonical forward identity for the source-evidence delta.
2. `0233_source_conversation_turn_evidence.sql` remains at its historical path with a first-line `lineageweave-compatibility-alias-of` declaration.
3. `migrate.sh` skips declared compatibility aliases and continues to execute the canonical target through the normal four-digit replay path. With no argument it reads the image-baked `/opt/lineageweave/migrations`; an explicit migration-root argument is reserved for recovery rehearsal and repository integration testing of that same loop.
4. Both the historical and canonical rollback paths remain available; automated contract tests require equivalent rollback effects.
5. CI treats alias-declared files as compatibility paths rather than canonical forward identities, verifies alias targets are real non-alias migrations with different ordinals, and rejects duplicate ordinals among canonical migrations.
6. Alias chains and alias-specific schema divergence are forbidden.

## Consequences and risks

Existing databases may execute the canonical 0248 SQL after having executed the historical 0233 SQL. That is intentional and safe only because this migration uses `ADD COLUMN IF NOT EXISTS` and a guarded constraint creation block. The exact SQL-body equivalence test prevents the retained alias from drifting into a second behavior.

The marker is a repository contract understood by LineageWeave replay tooling, not a generic PostgreSQL feature. Any future deployment path that executes root migration files independently must either honor the marker or use only the canonical migration set. This must be reflected in operability/recovery documentation before the ADR can become Accepted.

The optional migration-root argument does not replace the production image path and is not populated from mutable application configuration. Its purpose is to run the exact production shell control flow against a bounded recovery/test set, including real `pg_isready` and `psql` calls, so alias handling is verified behaviorally rather than inferred from source text.

A database-backed migration ledger remains the preferred successor when a non-idempotent migration family requires stronger once-only execution semantics, consistent with ADR 0166. This ADR does not manufacture such a ledger prematurely.

## Promotion evidence

Before changing this ADR to Accepted, one exact head must prove:

- canonical ordinal uniqueness and alias-contract tests;
- clean PostgreSQL install;
- upgrade/replay from a database predating both historical 0233 deltas;
- two consecutive executions of the exact production `migrate.sh` loop against real PostgreSQL, with `0233_report_leftover_map_unexplained_share.sql` and canonical `0248_source_conversation_turn_evidence.sql` applied, the historical source-evidence alias skipped, and both intended schema effects present exactly once;
- both historical and canonical rollback discoverability;
- full PostgreSQL suite and migration replay suite;
- current migration/operability/recovery documentation and protected-base collision recheck.
