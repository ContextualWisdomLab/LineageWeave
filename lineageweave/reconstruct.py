"""The core pipeline: cluster records, score candidate parents on
independent channels, fuse the channels with RankWeave, and assemble the
winning edges into a tree per group with ThreadWeave.

Validated against a real 43,814-row dataset during development (see
docs/lineage-bi-research-notes.md for the methodology writeup): naive
grouping-plus-recency linking agreed with an independent secondary-key
signal only 2.6% of the time, which is why this module fuses several weak
channels instead of trusting any single one.
"""

from __future__ import annotations

from collections import defaultdict

import rankweave as rw
import threadweave as tw

from .adjudication_client import AdjudicationClient, NullAdjudicationClient
from .channels import secondary_key_match_score, temporal_score, text_similarity_score
from .embedding_client import EmbeddingClient, NullEmbeddingClient, cosine_similarity
from .models import Edge, Record, Tree

# Channel weights when every channel is available. llm gets the most weight
# because it is the only channel that actually reasons about the content
# instead of approximating it; the rest renormalize when llm is unavailable
# (see active_weights()).
DEFAULT_CHANNEL_WEIGHTS = {"temporal": 0.15, "secondary_key": 0.15, "text": 0.30, "llm": 0.40}

# ponytail: only the most recent WINDOW prior records in a group are
# considered as candidate parents, bounding per-group cost to O(n*window)
# instead of O(n^2). True parents are almost always temporally close in
# practice (validated on the reference dataset); raise this if a future
# recall check finds real parents falling outside the window.
DEFAULT_CANDIDATE_WINDOW = 50

# Below this fused score, a record becomes its own root instead of being
# force-attached to the best of a set of genuinely weak candidates -- every
# channel score is in [0, 1] and weights sum to 1, so the fused score is
# already on a comparable [0, 1] scale. Without this floor every record
# after the first in a group gets *some* parent even when none of the
# candidates are plausible, which is wrong more often than it is right.
DEFAULT_MIN_FUSED_SCORE = 0.3

# ponytail: same batch-size philosophy as post_content_persistence's LLM
# batching -- a corpus-wide rebuild is tens of thousands of records, and
# provider embedding endpoints cap request size/latency per call.
_EMBEDDING_BATCH_MAX_RECORDS = 64
_EMBEDDING_BATCH_MAX_CHARS = 24_000


def active_weights(
    llm: AdjudicationClient, weights: dict[str, float] = DEFAULT_CHANNEL_WEIGHTS
) -> dict[str, float]:
    """Drop and renormalize the llm channel's weight when no client is configured."""
    active = dict(weights)
    if not getattr(llm, "available", False):
        active.pop("llm", None)
    total = sum(active.values())
    return {channel: weight / total for channel, weight in active.items()}


def _group_by(records: list[Record]) -> dict[str, list[Record]]:
    """Implement the _group_by operation for this channel."""
    groups: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        groups[record.group_key].append(record)
    return groups


def _best_parent(
    record: Record,
    candidates: list[Record],
    llm: AdjudicationClient,
    weights: dict[str, float],
    min_score: float,
    vectors: dict[str, list[float]],
) -> tuple[Record, float, dict[str, float]] | None:
    """Implement the _best_parent operation for this channel."""
    if not candidates:
        return None
    channel_results: dict[str, list[tuple[str, float]]] = {"temporal": [], "secondary_key": [], "text": []}
    if "llm" in weights:
        channel_results["llm"] = []
    per_candidate_scores: dict[str, dict[str, float]] = defaultdict(dict)

    record_vector = vectors.get(record.record_id)
    for candidate in candidates:
        candidate_vector = vectors.get(candidate.record_id)
        # A real embedding pair always wins over the difflib stand-in
        # (channels.py's own docstring names this the intended swap); a
        # candidate missing a vector (failed embedding batch) still gets a
        # signal instead of silently losing the whole text channel.
        text_score = (
            cosine_similarity(candidate_vector, record_vector)
            if candidate_vector is not None and record_vector is not None
            else text_similarity_score(candidate, record)
        )
        scores = {
            "temporal": temporal_score(candidate, record),
            "secondary_key": secondary_key_match_score(candidate, record),
            "text": text_score,
        }
        if "llm" in weights:
            scores["llm"] = llm.judge(candidate.label, record.label)
        for channel, score in scores.items():
            channel_results[channel].append((candidate.record_id, score))
            per_candidate_scores[candidate.record_id][channel] = score

    fused = rw.weighted_convex_fuse(channel_results, weights, limit=1)
    if not fused or fused[0].score < min_score:
        return None
    winner_id = fused[0].item_id
    winner = next(c for c in candidates if c.record_id == winner_id)
    return winner, fused[0].score, per_candidate_scores[winner_id]


def _reconstruct_group(
    records: list[Record],
    llm: AdjudicationClient,
    weights: dict[str, float],
    window: int,
    min_score: float,
    vectors: dict[str, list[float]],
) -> tuple[list[tw.Container], list[Edge]]:
    """Implement the _reconstruct_group operation for this channel."""
    ordered = sorted(records, key=lambda r: r.occurred_at)
    messages: list[tw.Message] = []
    edges: list[Edge] = []
    for index, record in enumerate(ordered):
        candidates = ordered[max(0, index - window) : index]
        parent_choice = _best_parent(record, candidates, llm, weights, min_score, vectors)
        references: list[str] = []
        if parent_choice is not None:
            parent, score, channel_scores = parent_choice
            references = [parent.record_id]
            edges.append(
                Edge(
                    parent_id=parent.record_id,
                    child_id=record.record_id,
                    fused_score=score,
                    channel_scores=channel_scores,
                )
            )
        messages.append(tw.Message(message_id=record.record_id, references=references, payload=record))
    return tw.thread_messages(messages), edges


def _embed_labels(records: list[Record], embedding_client: EmbeddingClient) -> dict[str, list[float]]:
    """Batch-embed every record's label once, up front.

    A failed batch yields no vectors for its records rather than raising --
    ``_best_parent`` falls back to ``text_similarity_score`` for any record
    without a vector, so a provider hiccup degrades the text channel back to
    its difflib stand-in instead of failing the whole reconstruction.
    """
    vectors: dict[str, list[float]] = {}
    embed_many = getattr(embedding_client, "embed_many", None)
    batches: list[list[Record]] = []
    batch: list[Record] = []
    batch_chars = 0
    for record in records:
        label_chars = len(record.label)
        if batch and (
            len(batch) >= _EMBEDDING_BATCH_MAX_RECORDS
            or batch_chars + label_chars > _EMBEDDING_BATCH_MAX_CHARS
        ):
            batches.append(batch)
            batch = []
            batch_chars = 0
        batch.append(record)
        batch_chars += label_chars
    if batch:
        batches.append(batch)

    for group in batches:
        try:
            embedded = (
                embed_many([record.label for record in group])
                if callable(embed_many)
                else [embedding_client.embed(record.label) for record in group]
            )
        except (OSError, RuntimeError, ValueError):
            continue
        for record, vector in zip(group, embedded, strict=True):
            if isinstance(vector, list) and vector:
                vectors[record.record_id] = vector
    return vectors


def _walk(roots: list[tw.Container]) -> tuple[list[str], dict[str, list[str]]]:
    """``thread_messages`` returns only the root Containers, each nesting its
    descendants under ``.children`` -- walk the whole forest to recover every
    node's id and its direct children, not just the top level.
    """
    root_ids = [container.message.message_id for container in roots]
    children_of: dict[str, list[str]] = defaultdict(list)
    stack = list(roots)
    while stack:
        container = stack.pop()
        parent_id = container.message.message_id
        for child in container.children:
            children_of[parent_id].append(child.message.message_id)
            stack.append(child)
    return root_ids, dict(children_of)


def reconstruct(
    records: list[Record],
    *,
    llm: AdjudicationClient | None = None,
    embedding: EmbeddingClient | None = None,
    weights: dict[str, float] = DEFAULT_CHANNEL_WEIGHTS,
    candidate_window: int = DEFAULT_CANDIDATE_WINDOW,
    min_fused_score: float = DEFAULT_MIN_FUSED_SCORE,
) -> list[Tree]:
    """Reconstruct one lineage :class:`Tree` per distinct ``group_key``.

    Args:
        records: every record across every group; grouping happens here.
        llm: adjudication channel client; defaults to
            :class:`~lineageweave.adjudication_client.NullAdjudicationClient`
            (the llm channel is then dropped, not faked).
        embedding: embedding channel client for the ``text`` channel;
            defaults to :class:`~lineageweave.embedding_client.NullEmbeddingClient`
            (the ``text`` channel then falls back to
            :func:`~lineageweave.channels.text_similarity_score`'s difflib
            stand-in, not a fabricated cosine score). When available, every
            record's label is embedded once up front (batched), not per
            candidate pair -- unlike ``llm``, which is genuinely a per-pair
            judgment.
        weights: per-channel fusion weights before llm-availability
            renormalization; see :data:`DEFAULT_CHANNEL_WEIGHTS`.
        candidate_window: how many recent prior records to consider as
            candidate parents per record; see :data:`DEFAULT_CANDIDATE_WINDOW`.
        min_fused_score: candidates scoring below this become a new root
            instead of a forced weak match; see :data:`DEFAULT_MIN_FUSED_SCORE`.
    """
    llm = llm or NullAdjudicationClient()
    embedding = embedding or NullEmbeddingClient()
    active = active_weights(llm, weights)
    vectors = _embed_labels(records, embedding) if embedding.available else {}
    trees: list[Tree] = []
    for group_key, group_records in _group_by(records).items():
        root_containers, edges = _reconstruct_group(
            group_records, llm, active, candidate_window, min_fused_score, vectors
        )
        record_by_id = {record.record_id: record for record in group_records}
        roots, children_of = _walk(root_containers)
        trees.append(
            Tree(
                group_key=group_key,
                records=record_by_id,
                edges=edges,
                roots=roots,
                children_of=children_of,
            )
        )
    return trees
