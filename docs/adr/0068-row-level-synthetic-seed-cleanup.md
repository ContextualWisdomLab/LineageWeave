# ADR 0068: Separate real import scope from row-level synthetic cleanup

- Status: Accepted
- Date: 2026-08-19
- Depends on: ADR 0020, ADR 0021, ADR 0022, ADR 0042

## Context

The synthetic `make seed` tree and a later PostgreSQL import can accidentally
share a `corporate_entity_id` when an operator uses `DEMO-CORP-01` as the
import scope. Deleting by corporate code would then delete real source posts,
and deleting the analysis registry would destroy immutable run evidence.

## Decision

- A normal PostgreSQL import rejects `DEMO-*` corporate entity codes. A test
  import must opt in explicitly with `--allow-demo-corporate-entity`.
- After a successful import, cleanup considers only posts under a `DEMO-*`
  entity whose source author/company/PU/sales-pool/customer/project context is
  entirely blank, and only when that same entity also contains a post with
  real source context.
- Posts referenced by `analysis_source_snapshot_member` or
  `analysis_run_lineage_edge` are never deleted. They are reported as blocked
  for a manual procedure. No `analysis_run`, snapshot, status, lineage-edge,
  or snapshot-member table is mutated by ingestion cleanup.
- Only unreferenced synthetic rows and their non-analysis derived rows may be
  removed. A shared `DEMO-CORP-*` entity is retained while any real post,
  process unit, affiliation, or child entity still references it.

## Consequences

- Future real imports cannot repeat the shared-scope mistake by default.
- The current polluted scope can be audited by the aggregate cleanup counts;
  immutable run references remain visible and require an explicit operator
  decision.
- Synthetic cleanup is conservative and may leave blocked seed rows behind;
  that is safer than silently rewriting run history.
