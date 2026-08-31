# ADR 0272: Twenty-millisecond read SLO

- Status: Accepted
- Date: 2026-08-31
- Supersedes: the no-read-threshold statements in ADR 0206

## Context

Authenticated Dashboard reads against 43,189 source records exposed a planner
cardinality error: PostgreSQL estimated one eligible row, repeatedly probed an
index, and left the browser in a loading state. A timeout would only hide that
cost. The product owner has now set an explicit requirement that every lookup
complete within 20 milliseconds.

ISO/IEC 25010:2023 makes performance efficiency part of the product quality
model, while ISO/IEC 25023:2016 defines quantitative product-quality
measurement. The threshold itself is the product-owner requirement; it is not
derived from either standard or from a rule of thumb.

## Decision

1. Every authenticated REST `GET` and MCP read tool has a maximum 20 ms
   service-processing budget. Measurement starts at application request entry
   and ends when the complete response bytes are ready. It includes identity
   and authorization checks, database work, projection, and serialization.
2. Provider and measurement computations are asynchronous commands, not
   lookups. Their enqueue, status, result, and citation reads remain subject to
   20 ms; the external computation duration is reported separately.
3. Acceptance measures cold and warm reads. A cache-hit run alone is not
   evidence. The declared deployment, dataset cardinality, response-byte
   count, concurrency, hardware, and raw maximum distribution stay with the
   runtime evidence. Every observed request must meet 20 ms; an average or
   percentile cannot conceal a slower request.
4. Setting a 20 ms timeout, returning an incomplete response, dropping
   authorized evidence, or moving an ordinary read behind a job does not meet
   the SLO. A failed request is a failed functional and performance check.
5. Read paths use bounded projections and continuation where the complete
   detail set cannot meet the budget. Summary counts remain exact over the
   authorized population; continuation changes transport size, not evidence
   membership, ranking, or measurement.
   The Dashboard therefore returns at most 20 evidence-rich cases by default
   (caller-bounded to 50), ordered by event instant, Post id, and case kind,
   plus `next_case_cursor`. Its all-post, per-kind Event/Post, and lifecycle
   counts are computed over the complete authorized period, never the page.
6. PostgreSQL plans must use narrow, maintained access paths instead of
   rescanning wide source bodies. Eligibility predicates remain logically
   identical, ABAC executes before aggregation, and source/provenance tables
   remain authoritative and normalized. Dashboard authorization, period,
   active-source, source-context, case-analysis, and ingestion-failure fields
   are maintained one row per Post in `dashboard_post_read_projection` by the
   same transaction that changes their authoritative source rows. Migration
   replay rebuilds the complete projection with set-based `EXISTS` checks;
   it never derives a second business fact or admits eventual counts.
   Exact case Event/Post and lifecycle totals use the companion
   `dashboard_case_rollup_read_projection`. It records every contributing
   evidence Post id, so the read rejects a rollup when any source falls outside
   the caller's current scope instead of leaking a pre-aggregated count.
   Exact Post totals use `dashboard_post_daily_summary`, keyed by natural
   event day and the complete visibility/entity/PU/context scope. The source
   projection trigger applies old/new row deltas in the same transaction;
   migration replay rebuilds the summary set-wise before deltas resume.
   Dashboard metrics, complete case rollups, bounded case/detail rows, and
   persisted topic readiness/detail are returned by one JSON statement.
7. k6 and database-plan checks enforce the same 20 ms maximum. The gate records
   cold and warm observations separately and fails on any HTTP, authorization,
   schema, citation, or latency failure.
8. Backend PostgreSQL sessions disable JIT. Runtime plans showed compilation
   startup dominating the bounded interactive aggregates without changing the
   result; analytical workers may opt in only with their own measured plan.
9. Voice taxonomy reads use trigger-maintained per-post truth projections and
   natural day/month rollups. Writes apply atomic old/new deltas; they never
   recount a shared group. Stored assertion validity instants wake the durable
   worker through PostgreSQL notification, so a time transition is reconciled
   at its recorded instant without an invented polling interval. Pool startup
   prepares the three bounded query shapes before accepting HTTP traffic.
10. The existing ten-connection application pool is established eagerly, and
   every connection loads the UUID-array and text-array codecs during
   initialization. Account scope and permissions use those types on every
   authenticated read; connection creation and codec discovery are startup
   work and may not consume the lookup budget.
    The Dashboard statement exceeds asyncpg's default cacheable-query byte
    ceiling, so every connection admits it to the existing statement cache,
    uses a generic PostgreSQL plan, and executes each query shape once during
    pool initialization. Pool reset restores that measured plan policy.
11. A Post detail lookup returns the complete metadata and evidence envelope
    without materializing `source_post.post_body`. The separately authorized
    `/api/posts/{post_id}/body` response streams the unchanged source text;
    its time to first byte remains within 20 ms, while complete transfer time
    and bytes per second are recorded as payload-throughput evidence. This is
    the sole exception to the complete-response boundary in item 1: a measured
    1,898,576-byte source body required more than 20 ms merely to leave the
    process, so pretending that full delivery met the lookup budget would make
    the SLO physically false. The UI renders the metadata immediately, aborts
    an obsolete body stream when navigation changes, and offers an explicit
    retry after a transfer failure. It never truncates or substitutes the
    source text.
12. The body stream reads bounded PostgreSQL TOAST slices rather than first
    materializing the whole value. Runtime comparison on the same exact body
    selected 262,144-character slices: 65,536-character slices delivered a
    6.2--17.8 ms TTFB but required 321--396 ms total; 262,144-character slices
    retained a 16.0--19.0 ms TTFB and reduced total transfer to 143--167 ms.
    The slice size is therefore a recorded measured selection, not an
    untested rule of thumb. Any later change must repeat the same byte-exact
    comparison and preserve the 20 ms maximum TTFB.
13. The unfiltered Post page uses a transaction-local custom PostgreSQL plan.
    The shared generic plan could not prune its nullable search and filter
    branches and measured 42--64 ms for the database fetch. `EXPLAIN
    (ANALYZE, BUFFERS)` on the identical bound statement measured 2.207 ms
    planning and 4.363 ms execution with a custom plan; the complete direct
    route measured 7.423 ms on its first observation and 2.736--3.094 ms after
    it. `SET LOCAL` confines this exception to the default-page transaction,
    and the pool remains `force_generic_plan` afterward. Search and filtered
    reads retain the shared generic-plan policy until separately measured
    evidence supports a different exact query shape.
14. Visibility and a single selected Voice obtain their exact authorized total
    from the transaction-maintained Voice rollup rather than `count(*) over()`
    on all eligible Posts. Before that change, both generic and custom plans
    measured 45--51 ms; focused direct observations afterward measured
    2.87--3.66 ms for visibility and 6.91--16.28 ms for one Voice. Multiple
    Voice selections may overlap, so they retain an exact distinct count until
    a maintained intersection projection exists; summing category counts would
    double-count multi-membership Posts.
15. Historical revision bodies do not add generated stored length columns to
    `source_post_revision`. A diagnostic attempt caused a multi-gigabyte table
    rewrite and lock, so it was cancelled without treating the rewrite as a
    read optimization. Historical bodies instead stream exact xmin-stable
    chunks to EOF without a fabricated Content-Length. Current bodies use the
    separately maintained Post-list projection populated on source writes.

## Consequences

The existing Dashboard observation that defined no latency threshold is no
longer sufficient. Each read surface needs exact-head runtime evidence before
release. Slow endpoints stay an explicit product gap until both cold and warm
checks meet the budget; documentation or a green unit suite cannot close it.

## References

International Organization for Standardization. (2016). *Systems and software
engineering—Systems and software Quality Requirements and Evaluation
(SQuaRE)—Measurement of system and software product quality* (ISO/IEC Standard
No. 25023:2016). https://www.iso.org/standard/35747.html

International Organization for Standardization. (2023). *Systems and software
engineering—Systems and software Quality Requirements and Evaluation
(SQuaRE)—Product quality model* (ISO/IEC Standard No. 25010:2023).
https://www.iso.org/standard/78176.html
