# ADR 0089: Private real-data runtime boundary

- Status: Accepted
- Date: 2026-08-20
- Related: [0001](0001-demo-identity-and-data-boundary.md), [0068](0068-row-level-synthetic-seed-cleanup.md), [0075](0075-read-time-synthetic-seed-exclusion.md)

## Context

LineageWeave is no longer only a synthetic demonstration. Its private runtime
must read authorized real PostgreSQL source records so the buyer Board,
Customer Master, Calendar, Ask Agent, ontology, and lineage evidence describe
the user's corpus. The public repository must nevertheless remain free of real
records and identifying examples.

## Decision

- Repository fixtures, tests, screenshots, examples, logs, benchmark artifacts,
  and committed documents remain synthetic or aggregate-only.
- A private runtime may import and serve real source records through the
  configured PostgreSQL/data boundary. The source record and its provenance
  remain authoritative; synthetic seed rows are not substituted into real
  views.
- Real-data validation brought back to git is limited to aggregate,
  non-identifying evidence. Raw titles, names, customer codes, post IDs, image
  bytes, and model responses must not be committed or printed.
- Row-level synthetic cleanup uses source-context NULL evidence and never
  deletes or rewrites analysis-run registry rows. Posts referenced by analysis
  snapshots or lineage edges remain a manual operator procedure.
- Tests for new behavior continue to use synthetic fixtures. Private live
  checks must be separately labeled as runtime evidence and must not be used as
  repository test fixtures.

## Consequences

- The application can be a real-data product without turning the public repo
  into a data publication.
- Public CI proves behavior against synthetic data; private runtime reports
  prove coverage against the authorized corpus.
- Demo data and real data require explicit provenance and read-time separation;
  a shared corporate entity code is not sufficient evidence for deletion.
