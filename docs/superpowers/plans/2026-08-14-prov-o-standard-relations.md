# PROV-O standard relations implementation plan

## Completed TDD sequence

1. Write failing tests for exact class/property inventories, datatype-property set, qualification tables, inverse-name table, graph validation, inference, RDF serialization, SQL seed coverage, naming rules, and support-profile mappings.
2. Confirm test collection fails before `lineageweave.prov_o` exists.
3. Implement the complete immutable registry and validated graph API.
4. Implement deterministic fixed-point materialization.
5. Generate the normalized PostgreSQL migration from the same registry and verify every IRI/code is present.
6. Add the ontology support profile and product-class mappings.
7. Add ADR, implementation architecture, complete matrix, and APA 7th doctoring references.
8. Run focused tests, branch coverage, compile checks, exact-head CI/security review, then return the PR to Ready.

## Merge gates

- 30/30 classes and 50/50 properties present.
- 14/14 qualification implications pass.
- 44/44 object-property inverse names present.
- Focused production statement and branch coverage 100%.
- Public callable docstrings 100%.
- Migration executes on PostgreSQL 16 in CI and rejects wrong object kinds/domains/ranges.
- Exact-head Tests, Security Scan, and SAST succeed.
- No valid unresolved review thread.
