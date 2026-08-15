# Analysis-run registry research and standards doctoring

**Capability maturity:** implemented on an active stacked PR; not protected-main
truth until merge.

## Decision traceability

| Source | Product decision |
|---|---|
| PostgreSQL 18 constraints and trigger documentation | Use primary/foreign/unique/check constraints for row-local invariants; use serialized trigger functions for cross-row cutoff, immutability, evidence-freeze, and lifecycle rules rather than unsupported cross-table `CHECK` constraints. |
| ISO 8601-1:2019, confirmed 2024 | Store evidence availability, capture, run cutoff, request, occurrence, and record clocks as timezone-aware PostgreSQL timestamps; do not collapse them into one ambiguous date string. |
| W3C PROV-O | Treat the registry as product execution/provenance metadata that may later bind to the standards-complete provenance layer; do not flatten source entities, activities, agents, or qualified relations into a JSON run payload. |
| Accepted TEPP temporal baseline | Keep reusable source-capture clocks separate from run-specific knowledge cutoff and enforce `maximum_available_time <= knowledge_cutoff` without claiming that this aggregate guard replaces TEPP's full multi-clock model. |

## Current-standard note

ISO 8601-1:2019 remains the published International Standard and was confirmed
in 2024. ISO/CD 8601-1 edition 2 is under development in 2026 and is tracked as
a draft, not used as the binding production standard.

PostgreSQL 18 is the current supported documentation line at the time of this
decision. The shipped container remains PostgreSQL 16, so migration syntax and
runtime behavior are intentionally limited to PostgreSQL 16-compatible
features while design guidance is checked against current documentation.

## Evidence and claim boundary

The migration records only opaque IDs, digests, bounded code values, aggregate
counts, and timestamps. Actual source rows, SQL, DSNs, private identifiers,
model/provider payloads, and acceptance artifacts remain outside public source
control and outside this registry. Real-data acceptance is not established by
schema tests; it requires a later private execution and signed aggregate-only
manifest.

## APA 7th references

International Organization for Standardization. (2019). *ISO 8601-1:2019: Date
and time—Representations for information interchange—Part 1: Basic rules*
(confirmed 2024; Amendment 1:2022).
https://www.iso.org/standard/70907.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 5.5.
Constraints*. https://www.postgresql.org/docs/current/ddl-constraints.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 37.
Triggers*. https://www.postgresql.org/docs/current/triggers.html

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology* (W3C
Recommendation). https://www.w3.org/TR/prov-o/
