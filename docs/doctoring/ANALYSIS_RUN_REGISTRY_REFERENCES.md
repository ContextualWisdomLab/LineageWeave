# Analysis-run registry research and standards doctoring

**Capability maturity:** implemented on an active stacked PR; not protected-main truth until merge.

## Decision traceability

| Source | Product decision |
|---|---|
| PostgreSQL 18 constraints documentation | Use primary/foreign/unique/check constraints for row-local invariants; do not encode cross-row state as an unsupported cross-table `CHECK`. Add indexes on referencing/query columns deliberately. |
| ISO 8601-1:2019, confirmed 2024 | Store `knowledge_cutoff`, `captured_at`, `requested_at`, and status-event instants as timezone-aware PostgreSQL timestamps; do not collapse the distinct clocks into one ambiguous date string. |
| W3C PROV-O | Treat the run registry as product execution/provenance metadata that may later bind to the standards-complete provenance layer; do not flatten source entities, activities, agents, or qualified relations into a JSON run payload. |

## Current-standard note

ISO 8601-1:2019 remains the published International Standard and was confirmed in 2024. ISO/CD 8601-1 edition 2 is under development in 2026 and is tracked as a draft, not used as the binding production standard.

PostgreSQL 18 is the current supported documentation line at the time of this decision. The shipped container remains PostgreSQL 16, so migration syntax is intentionally limited to behavior available in PostgreSQL 16 while design guidance is checked against current documentation.

## APA 7th references

International Organization for Standardization. (2019). *ISO 8601-1:2019: Date and time—Representations for information interchange—Part 1: Basic rules* (confirmed 2024; Amendment 1:2022). https://www.iso.org/standard/70907.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 5.5. Constraints*. https://www.postgresql.org/docs/current/ddl-constraints.html

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology* (W3C Recommendation). https://www.w3.org/TR/prov-o/
