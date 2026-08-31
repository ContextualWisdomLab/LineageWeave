# ADR 0279: Global Ask exact semantic index projection

- Status: Proposed
- Date: 2026-08-31
- Depends on: RankWeave ADR 0008 accepted on protected main and an immutable
  LineageWeave dependency pin containing that contract

## Context

The current Global Ask cosine statement joins 6,578 embedding headers to
20,223,744 scalar coordinate rows for the active 3,072-dimensional model. On
the declared four-CPU Compose runtime, one authenticated Ask held PostgreSQL
for about three seconds and concurrent ordinary reads exceeded ADR 0272's
20-millisecond maximum. Packing the same 161,660,928 vector bytes for every
request reduces Python expansion but does not remove transfer or repeated
scoring.

ADR 0208 assigns retrieval vector and linear-algebra ownership to RankWeave.
ADR 0237 requires deterministic multithreaded CPU before an accelerator can be
considered. LineageWeave must retain model identity, persistence, ABAC, and
post-authorization without approximating or dropping evidence.

## Decision

1. PostgreSQL maintains `post_content_embedding_exact_projection`, one row per
   complete embedding. `vector_bytes` is the ordered concatenation of
   PostgreSQL `float8send` values: canonical big-endian IEEE 754 binary64. The
   row records the exact model, dimension, Post/unit identities, and SHA-256 of
   those bytes. Incomplete coordinate sets have no projection row.
2. The same transaction that persists or backfills embedding coordinates calls
   the set-based refresh function. Delete and rebuild are transactionally
   invisible to readers. A statement trigger advances one monotonic global
   projection version after projection inserts, updates, deletes, and cascades.
   Migration replay bootstraps all existing embeddings only while the
   projection is empty; an already-maintained projection is not repacked or
   version-advanced merely because the idempotent migration runs at startup.
3. A cold worker or changed projection loads the ordered rows once, verifies
   every persisted row digest, concatenates the packed bytes, and asks
   RankWeave to build a complete immutable snapshot. It accepts the snapshot
   only when version, dimension, and candidate count match. Restart recovery
   repeats the same validation; no query-result cache exists. The durable
   worker does not advance its readiness heartbeat or consume Ask work until
   this preparation completes. A request path never builds or replaces a
   snapshot: a missing or newly stale snapshot is unavailable until the
   background preparation barrier installs the complete replacement. Before
   readiness opens, the worker also prepares every distinct authorization
   scope held by a currently configured `post_read` account: the local
   all-affiliation scope and each Keyverse-compatible atomic affiliation.
   An authoritative projection with no rows is a complete empty snapshot, not
   an owner failure: there is no vector dimension or candidate to score. The
   worker may open readiness for that version after preparing the configured
   scopes, but every request rechecks the current projection and authorization
   versions before returning the exact empty result. The first projected
   embedding advances the projection version, closes readiness, and requires
   normal dimension discovery and owner snapshot preparation before service
   resumes.
4. A monotonic authorization version advances on the normalized affiliation,
   role-permission, process-unit, and source-Post authorities that can change a
   visible candidate set. For each declared scope and exact projection version,
   the worker builds one immutable canonical length-prefixed packed identity
   buffer and binds its scope and byte digests. It executes RankWeave's exact
   complete-ranking and interval-screened top-k preflights plus PostgreSQL
   result reauthorization for that real scope. Readiness opens only after
   every declared scope's warm owner-plus-postauth path completes within ADR
   0272's 20-millisecond maximum. The preflight results are discarded; they
   are not answer or authorization caching. A scope whose canonical packed
   count is zero is nevertheless prepared as an exact empty authorization
   scope. It has no candidate on which to run an owner preflight or final row
   reauthorization. Before readiness, the worker warms and measures the same
   projection-and-authorization version check twice against the unchanged
   20-millisecond maximum. Each request repeats that check and returns no
   candidates only while both versions still match. This lets unrelated
   non-empty scopes proceed without admitting a stale or unauthorized item.
   Preparation also includes the current-grant intersection of every queued or
   running job's enqueue-time entity and process-unit scope. Job scope-table
   mutations advance the authorization version, so a newly queued historical
   scope closes readiness and is prepared before dispatch. Later grants can
   never widen that captured scope, while revocations still narrow it.
5. Every query supplies the
   matching immutable packed scope to RankWeave, and reauthorizes the exact
   returned identities in PostgreSQL before constructing a source. The final
   repeatable-read query returns current projection and authorization versions
   beside the rows and fails closed unless both equal the prepared snapshot.
   Because every `source_post` mutation advances the authorization version,
   equality proves the eligibility predicate used to build the packed scope is
   unchanged; final ABAC and native UUID identity joins do not repeat its
   corpus-wide fallback probe. An unknown,
   changed, or unprepared scope fails closed while the background worker
   prepares it. Event-time filtering is applied during final PostgreSQL
   reauthorization over the owner's complete exact item ranking, so a cached
   base scope cannot admit or truncate a date-ineligible result. Request-scoped
   reauthorization is never reused.
6. Snapshot load, authorization selection, owner invocation, and result
   verification use one repeatable-read database snapshot. A process lock
   serializes replacement only; warm callers retain one immutable owner
   snapshot and score concurrently. RankWeave's immutable handle provides
   atomic replacement, so an in-flight owner query observes one complete old or
   new snapshot.
7. The indexed path activates only when the immutable pinned RankWeave revision
   exports its accepted `SemanticUnitExactIndex` contract. The current pin does
   not, so this branch keeps the new path inactive. Missing or malformed owner
   evidence fails the indexed path closed; LineageWeave never substitutes local
   cosine, approximate pgvector, or a partial candidate set.
8. This decision does not claim ADR 0272 acceptance. Activation requires cold
   and restart recovery, projection maintenance, asyncpg transfer/packing,
   exact owner results, ABAC non-leakage, and the authenticated concurrent k6
   maximum to be measured on the declared Compose runtime.

Requests arriving in the same scheduler turn may share one owner traversal
only when snapshot, projection version, authorization version, model,
dimension, exact scope digest, and packed-authorization digest all match.
No-date requests use RankWeave's exact top-k contract; date-filtered requests
retain the complete ranking so PostgreSQL filtering cannot hide a later
eligible result. One fixed-shape `UNNEST` query reauthorizes all reports and
returns rows partitioned by request. Every request retains its own date
predicate, result limit, ordered-row validation, and final version check.
Different scope digests never share owner or database work.

The 2026-08-31 aggregate, non-identifying full-path measurement used the
declared four-worker CPU profile, 6,578 complete 3,072-dimensional embeddings,
161,660,928 persisted vector bytes, and a 577,992-byte exact public
authorization buffer. One projection refresh took 28.923 ms. After removing
packed-ID allocations in RankWeave, cold restart recovery took 1,035.223 ms;
30 warm full queries measured 15.637-20.703 ms (18.340 ms mean). Ten batches of
four concurrent queries measured 32.130-44.010 ms per request (39.807 ms mean)
and therefore did not satisfy ADR 0272. Isolated warm phases measured 5.819-
8.941 ms for PostgreSQL authorization packing, 4.964-6.896 ms for exact owner
ranking, and 1.308-3.614 ms for PostgreSQL result reauthorization. Authenticated
k6 remains an activation gate after the accepted owner revision is pinned into
the Compose image; these component measurements are not a k6 substitute.

The interval-safe owner plus fixed-shape batch reauthorization later measured
100 batches of four distinct queries at 15.286 ms minimum, 15.890 ms mean,
17.232 ms nearest-rank p95, and 22.587 ms maximum on the exact application
pool; one ten-batch series therefore still failed the maximum. A 500-iteration
phase trace observed four failures, including a 68.421 ms batch whose owner
call alone took 61.509 ms while PostgreSQL took 1.231 ms. First accepted
requests for five prepared scopes measured 8.067-9.625 ms. The optimization is
exact and materially faster, but deterministic 20 ms acceptance remains
unproven on this host, so activation and authenticated k6 claims stay closed.

Removing Python and the application event loop did not close that proof gap.
A host-native Rust process used a warmed immutable 6,578-by-3,072 synthetic
snapshot, four distinct mixed-sign queries, macOS user-initiated QoS, and a
dedicated Rayon pool. An initial 100-call sweep for every outer worker count
from one through ten stayed below 20 ms, but ten fresh one-worker processes
later produced 52.948 ms and 81.775 ms calls. The declared four-vCPU Colima
Linux scalar profile also failed for every worker count: one through four
workers had maxima of 82.359, 56.221, 52.808, and 80.210 ms. Startup
calibration cannot turn a finite passing sample into the required maximum, and
the owner has no proven service profile for LineageWeave to consume. This ADR
therefore adds no endpoint setting or native service activation.

An isolated Colima profile then held the cloned PostgreSQL and Valkey state,
8 GiB memory, and all product services constant while varying virtual CPUs from
four through the host's ten physical cores. VM-internal authenticated five-way
k6 removed the macOS port-forward and host k6 process from the measured path.
Every profile still failed the deterministic maximum: at four CPUs the two
series reached 30.700/29.700/28.420/28.170/27.390 ms and
31.020/27.260/26.180/25.680/22.810 ms for search/posts/lineage/dashboard/Ask
poll; five through ten CPUs reached respective overall maxima of 79.040,
85.920, 48.280, 127.320, 98.140, and 116.490 ms. Increasing CPU allocation is
therefore not a measured capacity precondition, and the indexed path remains
inactive.

ADR 0224's readiness-epoch corrections prevent false health after a reboot or
transient validation failure. They do not change the request path or any
latency result above, and therefore cannot satisfy ADR 0272's activation gate.

## Consequences

Warm Ask transfers only the query vector and authorized opaque identities to
the owner. PostgreSQL no longer performs the 20,223,744-row active cosine scan.
Projection writes pay an exact set-based pack and digest cost in their existing
transaction; full snapshot transfer and build remain cold/replacement work.

The projection duplicates representation, not business meaning. Normalized
source tables remain authoritative. A projection or owner digest mismatch
makes the indexed channel unavailable and cannot be repaired heuristically.

## Rejected alternatives

- HNSW, IVFFlat, or approximate pgvector: changes recall and can discard
  authorized evidence before ABAC.
- Per-request packed full snapshot: still transfers 161,660,928 bytes and
  rebuilds validation/norm metadata for every Ask.
- Fixed worker counts or a local process pool: deployment guesses are not an
  owner execution contract.
- LineageWeave cosine or norm arithmetic: conflicts with ADR 0208.
- Query-result caching: cannot replace exact authorization at request time.
- Preflighting a fabricated public or synthetic scope: does not establish the
  statement, page, owner, and postauthorization path for a configured caller.

## References

IEEE Computer Society. (2019). *IEEE standard for floating-point arithmetic*
(IEEE Std 754-2019). https://doi.org/10.1109/IEEESTD.2019.8766229

National Institute of Standards and Technology. (2015). *Secure Hash Standard
(SHS)* (FIPS PUB 180-4). https://doi.org/10.6028/NIST.FIPS.180-4
