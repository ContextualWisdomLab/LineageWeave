# ADR 0090: Global Ask expands its top match through Event Lineage

- Status: Accepted
- Date: 2026-08-20
- Related: [0047](0047-global-ask-semantic-retrieval.md), [0064](0064-lineage-evidence-and-tree-assembly.md), [0084](0084-lineage-research-grounding.md)

## Context

ADR 0047 gave Global Ask's retrieve step the same source-context search
surface as the board (raw source hints, project mentions, roles, Keyman
mentions, title, body). The current ADR 0047 revision ranks persisted
semantic-unit embeddings against the complete question,
but it never touches `post_lineage_edge` -- the Event-Lineage relation
`lineageweave.reconstruct` already persists, and the same relation the
post-scoped chat flow (`gather_chat_sources`) already expands through for a
single known starting post.

A relevance-correct top match is still one snapshot. A live reproduction
asking about a specific real event got an accurate answer about that one
post and nothing about what led up to it or what happened next. The account asking
almost always wants the event's place in a sequence, not an isolated
record.

## Decision

After `gather_global_chat_sources` ranks candidates by persisted semantic-unit
embedding similarity,
it expands only the single top-ranked match through its direct
`post_lineage_edge` neighbors (parent and child), mirroring the `.direct`
set `find_linked_post_ids` already computes for the post-scoped flow. The
expansion:

- Is bounded to the top match only. Expanding every semantic candidate was
  rejected -- a loosely related term matching a second post would drag an
  unrelated lineage chain into the model's context for no benefit.
- Never bypasses ABAC. Lineage-neighbor ids are merged into the same
  candidate set the existing visibility filter (`can_see_post`) already
  runs over; nothing lineage-adjacent is shown without passing that check.
- Shares the existing bounded source `limit`. The anchor and its direct
  neighbors take the first slots and lower-ranked semantic candidates fill
  any remaining slots; the returned source count never exceeds `limit`.
- Tags each expanded source with an explicit `Event Lineage: reconstructed
  timeline neighbor of post_id=...` evidence fact, and only when the
  anchor post itself is visible -- an expanded neighbor must never cite an
  anchor id the requesting account cannot see.

This is the event-centric temporal retrieval problem DyG-RAG frames
(Sun et al., 2025): a single temporally-anchored record answers "what does
this record say," not "what actually happened," which needs the event
sequence around it.

## Considered alternatives

- Expand every semantically ranked candidate's lineage neighbors, not just the
  top one: rejected for the reason above -- unbounded relevance drift into
  the prompt.
- Increase `limit` and let the ranking naturally surface neighbors: rejected
  -- a genuine lineage predecessor or successor can express a different event
  in the sequence (a
  Kick-off Meeting and its follow-up rarely repeat the same terms), so
  ranking alone cannot be relied on to surface it.

## Consequences

- Global Ask answers can now speak to a connected sequence of records
  around its best match, not only that match's own content.
- `limit` remains the hard upper bound after lineage expansion.
- Global Ask still has no persisted multi-turn conversation state, so
  there is no long-context-compression problem yet. Recursive dialogue
  summarization (Wang et al., 2023) is recorded in
  `docs/lineage-bi-research-notes.md` as the citation a future persisted
  Global Ask conversation thread would build on, not as a claim that
  conversation-level compression exists today.

## Evidence and literature

Full APA 7th-edition entries are maintained in
[`docs/lineage-bi-research-notes.md`](../lineage-bi-research-notes.md)
(Sun et al., 2025; Wang et al., 2023), per the paper register ADR 0084
establishes.
