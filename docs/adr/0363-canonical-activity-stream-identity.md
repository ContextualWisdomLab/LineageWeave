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

Alias discovery may find many independent legacy keys. Startup therefore keeps
at most 128 pending alias-set writes in memory and flushes each bounded group
through a non-transactional redis-py pipeline. `SADD` result integers are summed
exactly, preserving the existing count of newly indexed aliases. Minimal test
adapters without pipeline support retain the sequential compatibility fallback;
the production client created by `create_valkey_client` uses the batched path.
The batching changes transport cost only: discovery, durability, and readiness
semantics remain unchanged.

The supported deployment is the repository's single `lineageweave` Compose
backend service. Deployment stops the preceding backend before starting the
replacement, so no pre-canonical writer may overlap the alias scan. A rolling
multi-version replica deployment is unavailable until it has a separate
writer-fencing contract.

Reads enumerate at most the retained-window number of streams. For a UUID read,
the common path queues the first bounded alias-index `SSCAN` page and canonical
`XREVRANGE count=N` in one non-transactional redis-py pipeline. When that scan
returns cursor zero, its alias members and paired canonical page are both reused
by the same request. An empty member set completes the canonical-only response
in that one exchange. A complete non-empty member set enters compatibility
merge without scanning the alias index again or re-fetching the canonical page;
only retained alias pages are fetched in the next pipeline exchange. Reusing a
complete page does not bypass the existing fan-out ceiling: canonical stream plus
retained aliases may contain at most 1,000 distinct stream keys. A nonzero cursor
falls back to the bounded compatibility iterator and never treats an incomplete
alias scan as complete history.

When aliases exist, production redis-py clients prefetch a bounded slice from
every admitted stream before merging locally. The per-stream page size is
`min(event_count, 1000 // stream_count)`, with a minimum of one. When the first
UUID pipeline already fetched the canonical page, that page is trimmed to this
per-stream budget before retained aliases are fetched, and the alias-only second
pipeline fills the remaining stream pages. Thus resident compatibility pages
still stay within the same 1,000-entry product ceiling. If one stream supplies
more than its prefetched share, only that exhausted stream is refilled with
another bounded page. Minimal adapters without pipeline support retain the older
one-entry incremental merger. Both paths preserve complete retained history,
canonical-first equal-millisecond ordering, and the final 1..1000 buyer-facing
output budget.

## Consequences

- Canonical reads retain every historical UUID spelling that actually exists.
- Startup alias writes use at most 128 pending `(index key, legacy stream key)`
  tuples per production pipeline exchange instead of one awaited network write
  per alias.
- The alias-free UUID buyer path admits compatibility metadata and fetches the
  bounded canonical window in one redis-py pipeline network exchange.
- A complete retained-alias admission page is reused rather than discarded: the
  one-alias compatibility fixture now needs two network exchanges, not three.
- Reused admission pages fail closed above 1,000 distinct canonical-plus-alias
  stream keys before any retained-alias fan-out is issued.
- The retained-alias production path batches bounded history pages instead of
  issuing one network command per stream and one additional command per returned
  event.
- Compatibility prefetch retains at most 1,000 stream entries at a time before
  output construction; skewed history refills only the stream that exhausted
  its bounded page.
- Request-time records and calls remain bounded by the retained stream and output
  limits; excessive alias cardinality is explicitly unavailable.
- Startup performs a cursor scan and must finish before readiness.
- The alias index is additional derived Valkey state and can be rebuilt from
  retained activity keys.

## Alternatives considered

- Enumerate common UUID spellings: rejected because PostgreSQL accepts more
  forms than a finite hand-picked list would honestly cover.
- Await one `SADD` for every discovered alias: rejected because rollout/readiness
  latency then adds one serial Valkey write round trip per historical alias even
  though those writes are independent.
- Buffer every discovered alias and issue one unbounded pipeline at the end:
  rejected because startup memory and command-buffer size would scale with the
  entire retained keyspace rather than a fixed batch.
- Perform an alias-index lookup and only afterward issue the canonical
  `XREVRANGE`: rejected because the normal UUID path then has at least two
  sequential Valkey network waits even when the alias set is empty.
- Discard a complete non-empty first alias page and rescan it before compatibility
  merge: rejected because it adds a deterministic network exchange and repeats
  admission work without improving history correctness.
- Reuse a complete alias page without reapplying the total-stream ceiling:
  rejected because 1,000 aliases plus the canonical stream would silently expand
  request fan-out beyond the bounded contract formerly enforced by the iterator.
- Fetch one compatibility entry per stream and then await one `XREVRANGE` per
  returned event: rejected because an authorized 50-event legacy-history panel
  still pays roughly one sequential Valkey wait per result.
- Fetch `event_count` entries from every compatibility stream in one pipeline:
  rejected because worst-case buffering becomes `event_count * stream_count`,
  up to one million retained records under the existing limits.
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
- Review `5121832019` identified the independent startup N+1 where alias
  discovery awaited one `SADD` network write for every retained legacy key.
- RED `4cfa402acadb43c3f60e4dba7bad8917230b9460` rejects direct per-alias `SADD`
  on a two-alias fixture while preserving exact durable members and added count.
- Production repair `c4a25ce1f03ee225874a56c3f102ffa8b48a0621` introduces a bounded 128-write
  non-transactional pipeline batch with a compatibility fallback for minimal
  adapters that do not expose redis-py pipeline support.
- Review `5121915874` identified the retained-alias buyer-path N+1 left after the
  canonical fast-path repairs: initial probes were concurrent, but each emitted
  event still triggered another awaited `XREVRANGE count=1`.
- RED `7d44315c81bd942db58af75ea9af9e9885c46dc5` requires a four-event,
  two-stream compatibility read to preserve exact merge order without paying one
  network exchange per event.
- Production repair `2ee36cf7844526a5f27803100f2b469e31573a98` batches bounded per-stream
  history pages through one non-transactional pipeline and refills only an
  exhausted stream, with total initial buffering capped at 1,000 entries.
- Review `5122107164` found that the retained-alias path still discarded the
  complete first SSCAN page and canonical XREVRANGE, then repeated alias
  admission and canonical retrieval before merging.
- RED `15746e2be27effca16c71f445f8d77f5d55fe6b8` requires the one-alias fixture
  to preserve exact four-event ordering in exactly two network exchanges, with
  pipeline batches `[2, 1]`.
- Production repair `07fa552f9fecbe1cda79a9fccc7eeacd82c4fba5` carries a complete first
  alias page plus the canonical page into compatibility merge and fetches only
  retained alias pages in the second pipeline exchange.
- Follow-up review `5122123572` found that this reuse path initially skipped the
  iterator's existing total-stream fan-out guard.
- RED `a9c080c1f2fa030bd2b0cec0e2fb6b43e4328bbc` supplies a complete first page
  with 1,000 aliases and requires fail-closed behavior after the first two-command
  exchange, before a retained-alias pipeline is issued.
- Production repair `8ef3a42608739e5a32b5841e4a14494df5326a3f` reapplies the 1,000 distinct
  canonical-plus-alias stream ceiling to reused admission pages.
- redis-py asyncio pipeline documentation specifies that pipeline commands are
  buffered and executed together when awaited through `execute()`; transactions
  remain optional and are not required for these independent read or set-write
  commands.
