# ADR 0035 — Project period reports

## Status

Accepted

## Context

`thread_group_key` is the coarse lineage grouping key. Source ingestion also
persists `secondary_grouping_key`, the fine-grained project key used by the
reconstruction channels. Reports need to compare those dimensions without
silently treating them as the same grouping.

## Decision

Expose `project` reports from `secondary_grouping_key`. The existing weekly
and monthly period parser, shared item bank, FIPC linking, CAT information
ranking, ABAC member filtering, and report persistence are reused. Empty
project keys do not create a report group.

## Consequences

- Project reports preserve the source project's exact persisted key.
- Thread and project reports can both contain the same post, intentionally.
- No project name is inferred from post text or from the process unit.
