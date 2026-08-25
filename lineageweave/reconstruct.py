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

import math
from collections import defaultdict

import rankweave as rw
import threadweave as tw

from .adjudication_client import AdjudicationClient, NullAdjudicationClient
from .channels import secondary_key_match_score, temporal_score, text_similarity_score
from .models import Edge, Record, Tree

# No default channel weights exist (ADR 0145, second amendment): fusion
# weights are always estimated by a psychometric model (fast-mlsirm
# today, TEPP when integrated) -- product paths load the persisted
# corpus estimate, and the library demo estimates from its declared
# generative design (channel_weight_estimation.estimate_fixture_channel_weights).
# Every reconstruct() caller passes weights for the exact channel set it can
# execute; a vector estimated for another set is never repaired or renormalized.

_CORE_WEIGHT_CHANNELS = frozenset({"temporal", "secondary_key", "text"})

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


def active_weights(
    llm: AdjudicationClient, weights: dict[str, float]
) -> dict[str, float]:
    """Validate and return the calibrated vector for the exact active channels."""

    expected = set(_CORE_WEIGHT_CHANNELS)
    if getattr(llm, "available", False):
        expected.add("llm")
    if set(weights) != expected:
        raise ValueError("weights must exactly match the active lineage channels")
    values = tuple(weights.values())
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0.0
        for value in values
    ) or not math.isclose(sum(values), 1.0, abs_tol=1e-9):
        raise ValueError("active lineage weights must be finite, positive, and sum to one")
    return dict(weights)


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
) -> tuple[Record, float, dict[str, float]] | None:
    """Implement the _best_parent operation for this channel."""
    if not candidates:
        return None
    channel_results: dict[str, list[tuple[str, float]]] = {"temporal": [], "secondary_key": [], "text": []}
    if "llm" in weights:
        channel_results["llm"] = []
    per_candidate_scores: dict[str, dict[str, float]] = defaultdict(dict)

    for candidate in candidates:
        scores = {
            "temporal": temporal_score(candidate, record),
            "secondary_key": secondary_key_match_score(candidate, record),
            "text": text_similarity_score(candidate, record),
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
) -> tuple[list[tw.Container], list[Edge]]:
    """Implement the _reconstruct_group operation for this channel."""
    ordered = sorted(records, key=lambda r: r.occurred_at)
    messages: list[tw.Message] = []
    edges: list[Edge] = []
    for index, record in enumerate(ordered):
        candidates = ordered[max(0, index - window) : index]
        parent_choice = _best_parent(record, candidates, llm, weights, min_score)
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
    weights: dict[str, float],
    candidate_window: int = DEFAULT_CANDIDATE_WINDOW,
    min_fused_score: float = DEFAULT_MIN_FUSED_SCORE,
) -> list[Tree]:
    """Reconstruct one lineage :class:`Tree` per distinct ``group_key``.

    Args:
        records: every record across every group; grouping happens here.
        llm: adjudication channel client; defaults to
            :class:`~lineageweave.adjudication_client.NullAdjudicationClient`
            (the supplied vector must therefore omit the llm channel).
        weights: fusion weights calibrated for exactly the channels this call
            executes. Required, and always a psychometric estimate (ADR 0145,
            second amendment): the persisted
            fast-mlsirm corpus estimate on product paths, or
            :func:`~lineageweave.channel_weight_estimation.estimate_fixture_channel_weights`
            for the library demo. No hand-picked default exists.
        candidate_window: how many recent prior records to consider as
            candidate parents per record; see :data:`DEFAULT_CANDIDATE_WINDOW`.
        min_fused_score: candidates scoring below this become a new root
            instead of a forced weak match; see :data:`DEFAULT_MIN_FUSED_SCORE`.
    """
    llm = llm or NullAdjudicationClient()
    active = active_weights(llm, weights)
    trees: list[Tree] = []
    for group_key, group_records in _group_by(records).items():
        root_containers, edges = _reconstruct_group(
            group_records, llm, active, candidate_window, min_fused_score
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
