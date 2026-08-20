# Global Ask semantic-search references

## Decision traceability

Global Ask performs bounded multilingual substring lookup over persisted project,
role, affiliation, person, organization, and team evidence. Each searched text
column has its own `pg_trgm` GIN index, and the retrieval SQL keeps one direct
`ILIKE` predicate per column. It deliberately does not wrap those fields in
`concat_ws(...)` or another expression, because such a query would not match the
column indexes declared by migration 0054.

PostgreSQL documents that the `pg_trgm` GiST and GIN operator classes support
indexed `LIKE` and `ILIKE` searches even when a pattern is not left-anchored.
It also notes that patterns with no extractable trigrams can degenerate to a
full-index scan. LineageWeave therefore treats the indexes as an acceleration
mechanism, not a latency guarantee: query terms and returned candidates remain
bounded independently of the planner.

Evidence in this repository:

- `backend/app/global_ask_retrieval.py`
- `migrations/0054_global_ask_semantic_search.sql`
- `migrations/rollback/0054_global_ask_semantic_search.sql`
- `tests/test_global_ask_retrieval.py`
- `tests/test_global_ask_semantic_indexes.py`

## APA 7th reference

PostgreSQL Global Development Group. (2026). *pg_trgm—Support for similarity of
text using trigram matching* (PostgreSQL 17 documentation, Section F.33).
https://www.postgresql.org/docs/17/pgtrgm.html
