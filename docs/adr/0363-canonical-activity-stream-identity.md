# ADR 0363: Canonical activity-stream identity

- Status: Proposed
- Date: 2026-09-04

## Context

`source_post.post_id` is a PostgreSQL `uuid`, while historical HTTP requests
could spell the same UUID with upper-case digits, braces, omitted hyphens, or
other PostgreSQL-accepted hyphen placement. Earlier activity writes embedded
the request spelling in a Valkey stream key. Canonicalizing only new writes can
therefore strand authorized history, and enumerating selected spellings cannot
cover PostgreSQL's input grammar.

The activity feed is a retained operational projection. It is not a source of
record truth, and its compatibility work must not broaden a request into a
keyspace scan.

## Decision

New activity writes use PostgreSQL's canonical lower-case, hyphenated UUID
form. Before the application begins serving reads, startup scans the existing
activity-key namespace once and records every actually present, UUID-equivalent
legacy key in a durable canonical-post alias set. A request reads the canonical
stream and only the aliases in that set. Non-UUID synthetic and legacy keys
retain exact spelling.

Cross-stream ordering uses the persisted millisecond component and declared
canonical-first precedence for equal milliseconds. Stream-local sequence
numbers never become a global chronology. Alias event identifiers remain
namespaced so two streams cannot emit the same public identity.

WATCH retries, retained-window read limits, and alias-index startup are fixed
product contracts. Failure to build the alias index makes the application
unready; the product does not silently hide historical activity.

The supported deployment is the repository's single `lineageweave` Compose
backend service. Deployment stops the preceding backend before starting the
replacement, so no pre-canonical writer may overlap the alias scan. A rolling
multi-version replica deployment is unavailable until it has a separate
writer-fencing contract.

Reads enumerate at most the retained-window number of streams. For a UUID read,
the common path queues the first bounded alias-index `SSCAN` page and canonical
`XREVRANGE count=N` in one non-transactional redis-py pipeline. When that scan
returns cursor zero with no aliases, the paired canonical page is the complete
result, so alias admission and data retrieval consume one network exchange rather
than two sequential waits. A nonzero cursor or any retained alias falls back to
the compatibility reader; it never treats an incomplete alias scan as evidence
that the canonical stream is the only history.

When aliases exist, the compatibility path performs a newest-first incremental
merge, fetching one entry per stream initially and at most one further entry per
returned event. More retained aliases fail closed instead of creating unbounded
fan-out or silently sampling history. This keeps the common path latency bounded
without pretending legacy stream-local sequence numbers form one global order.

## Consequences

- Canonical reads retain every historical UUID spelling that actually exists.
- The alias-free UUID buyer path admits compatibility metadata and fetches the
  bounded canonical window in one redis-py pipeline network exchange.
- Compatibility merging may pay an additional bounded probe before its existing
  incremental reads; legacy-history preservation takes precedence over the
  alias-free fast path once an alias or unfinished scan is observed.
- Request-time records and calls remain bounded by the retained stream and output
  limits; excessive alias cardinality is explicitly unavailable.
- Startup performs a cursor scan and must finish before readiness.
- The alias index is additional derived Valkey state and can be rebuilt from
  retained activity keys.

## Alternatives considered

- Enumerate common UUID spellings: rejected because PostgreSQL accepts more
  forms than a finite hand-picked list would honestly cover.
- Perform an alias-index lookup and only afterward issue the canonical
  `XREVRANGE`: rejected because the normal UUID path then has at least two
  sequential Valkey network waits even when the alias set is empty.
- Always use one-entry incremental reads, including the canonical-only path:
  rejected because it turns the normal activity panel into one sequential Valkey
  round trip per returned event without adding compatibility information.
- Scan the activity keyspace on each request: rejected because latency and work
  would scale with unrelated posts.
- Drop legacy aliases: rejected because canonicalization would hide retained
  authorized history.

## Implementation evidence

- Review `5121693984` identified that the earlier read-budget test counted only
  `XREVRANGE` and omitted the preceding alias-index `SSCAN` network wait.
- RED `7dcc5c16bc61393fc6a533e216baee8c43363894` counts both direct Valkey waits
  and therefore rejects the earlier two-exchange canonical UUID path.
- Production repair `02417fcf92969ffe7924f2722b192f40ff953e0d`
  pipelines bounded alias admission with the canonical page while preserving the
  existing compatibility fallback.
- Test convergence `2b594942c12c37fe68459c02fbf47a2d11a727e4` models the pipeline as one
  network exchange and retains the exact canonical stream/count assertion.
- redis-py asyncio pipeline documentation specifies that pipeline commands are
  buffered and executed together when awaited through `execute()`; transactions
  remain optional and are not required for these independent read commands.
