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
4. A monotonic authorization version advances on the normalized affiliation,
   role-permission, process-unit, and source-Post authorities that can change a
   visible candidate set. For each declared scope and exact projection version,
   the worker builds one immutable canonical length-prefixed packed identity
   buffer and binds its scope and byte digests. It executes RankWeave's exact
   owner preflight plus PostgreSQL result reauthorization for that real scope.
   Readiness opens only after every declared scope's warm owner-plus-postauth
   path completes within ADR 0272's 20-millisecond maximum. The preflight
   result is discarded; it is not answer or authorization caching.
5. Every query re-reads projection and authorization versions, supplies the
   matching immutable packed scope to RankWeave, and reauthorizes the exact
   returned identities in PostgreSQL before constructing a source. An unknown,
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
