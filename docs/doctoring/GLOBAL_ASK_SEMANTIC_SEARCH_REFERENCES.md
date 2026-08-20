# Global Ask semantic-search references

## Decision traceability

Global Ask performs bounded multilingual substring lookup over persisted project,
role, affiliation, person, organization, and team evidence. Each searched text
column has its own `pg_trgm` GIN index, and the retrieval SQL keeps one direct
`ILIKE` predicate per column. It deliberately does not wrap those fields in
`concat_ws(...)` or another expression, because such a query would not match the
column indexes declared by migration 0054.

Organization names cross abbreviation and language boundaries only through
corroborated `organization_name_resolution` rows. The source-observed raw name
acts as a SKOS-style alternative label for the canonical corporate-entity name;
pending or uncorroborated mappings never nominate a post. This reuses the
existing contextual-orchestrator plus SearXNG evidence path and document context
rather than generating speculative translations at query time. Multilingual
entity-linking evidence supports using document context to connect surface forms
across languages (De Cao et al., 2022).

PostgreSQL documents that the `pg_trgm` GiST and GIN operator classes support
indexed `LIKE` and `ILIKE` searches even when a pattern is not left-anchored.
It also notes that patterns with no extractable trigrams can degenerate to a
full-index scan. LineageWeave therefore treats the indexes as an acceleration
mechanism, not a latency guarantee: query terms and returned candidates remain
bounded independently of the planner.

Evidence in this repository:

- `backend/app/global_ask_retrieval.py`
- `migrations/0054_global_ask_semantic_search.sql`
- `migrations/0055_verified_organization_label_search.sql`
- `migrations/rollback/0054_global_ask_semantic_search.sql`
- `tests/test_global_ask_retrieval.py`
- `tests/test_global_ask_semantic_indexes.py`

## APA 7th references

De Cao, N., Wu, L., Popat, K., Artetxe, M., Goyal, N., Plekhanov, M.,
Zettlemoyer, L., & Riedel, S. (2022). Multilingual autoregressive entity
linking. *Transactions of the Association for Computational Linguistics, 10*,
274–290. https://doi.org/10.1162/tacl_a_00460

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization
system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

PostgreSQL Global Development Group. (2026). *pg_trgm—Support for similarity of
text using trigram matching* (PostgreSQL 17 documentation, Section F.33).
https://www.postgresql.org/docs/17/pgtrgm.html
