# ADR 0233: Global Ask nominates persisted semantic candidates

- Status: Accepted
- Date: 2026-08-26
- Related: PRD-FR-4, ADR 0062, ADR 0202, issue #272

## Context

Global Ask ranked persisted semantic-unit embeddings, then loaded project,
role, person, organization, team, and Knowledge Graph evidence only for the
selected posts. A term present only in that persisted evidence could therefore
miss its source. Local token lists, hand-picked term weights, or provider
fallbacks would create an unaudited second semantic policy.

## Decision

Before embedding retrieval, PostgreSQL nominates a bounded set of post IDs by
applying `websearch_to_tsquery('simple', question)` to persisted project,
responsibility, affiliation, person, organization, team, and Knowledge Graph
type evidence. Matching expression GIN indexes make this a database-native
search boundary. No local stopword list, score, threshold, or channel weight is
introduced.

Nomination returns IDs only and grants no access. The existing final source
query repeats corporate-entity/process-unit scope, publication eligibility,
event-time bounds, and caller authorization before reading any body or semantic
fact. Exact persisted-evidence candidates precede embedding candidates; both
use the caller's existing result limit, preserve deterministic ordering, and
deduplicate by post ID. An unavailable embedding channel drops only that
channel. No candidate from either channel is evidence until final authorization
succeeds.

This decision implements only issue #272's internal semantic nomination slice.
External public verification, three-way truth status, and SearXNG citations
remain separate work because they cross a different trust boundary.

## Consequences

- A semantic-only persisted term can nominate its authorized source without a
  raw-LLM call or an invented weight.
- Private candidate IDs may be examined inside PostgreSQL, but no private text
  leaves the final authorization boundary.
- PostgreSQL full-text query semantics, rather than application token
  heuristics, define exact nomination behavior.

## References

PostgreSQL Global Development Group. (2026). *Controlling text search*.
PostgreSQL 18 documentation.
https://www.postgresql.org/docs/current/textsearch-controls.html

PostgreSQL Global Development Group. (2026). *GIN indexes*.
PostgreSQL 18 documentation. https://www.postgresql.org/docs/current/gin.html

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology* (W3C
Recommendation). https://www.w3.org/TR/prov-o/
