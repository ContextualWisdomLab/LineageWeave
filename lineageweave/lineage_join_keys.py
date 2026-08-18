"""Join keys between posts: same Keyman, same win-pool, same ontology object.

These labels sit on Event Lineage edges only. A missing ontology object
fail-closes that branch. This module does not add an explore screen and
does not invent a parent from an unverified candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .ontology import iri_for_lookup_code

JOIN_KEYMAN = "same_keyman"
JOIN_WIN_POOL = "same_win_pool"
JOIN_ONTOLOGY_OBJECT = "same_ontology_object"

JOIN_KEY_LABELS: dict[str, str] = {
    JOIN_KEYMAN: "같은 Keyman",
    JOIN_WIN_POOL: "같은 수주풀",
    JOIN_ONTOLOGY_OBJECT: "같은 온톨로지 객체",
}

ONTOLOGY_OBJECT_EMPTY_NEXT_ACTION = "그 객체는 온톨로지에 아직 없습니다"


@dataclass(frozen=True)
class PostJoinFacts:
    """Authorized join facts for one post. Empty sets stay empty."""

    post_id: str
    win_pool: str
    keyman_ids: frozenset[str]
    ontology_object_ids: frozenset[str]
    unbound_object_names: frozenset[str]


@dataclass(frozen=True)
class EdgeJoinKeys:
    """Buyer-facing labels for one reconstruct edge."""

    codes: tuple[str, ...]
    labels: tuple[str, ...]
    empty_next_action: str | None


def ontology_object_is_declared(lookup_code: str) -> bool:
    """True only when the published ontology already names this object."""
    return iri_for_lookup_code(lookup_code) is not None


def join_keys_for_pair(left: PostJoinFacts, right: PostJoinFacts) -> EdgeJoinKeys:
    """Label the reconstruct edge. Do not invent a new parent node."""
    codes: list[str] = []
    if left.keyman_ids & right.keyman_ids:
        codes.append(JOIN_KEYMAN)
    left_pool = left.win_pool.strip()
    right_pool = right.win_pool.strip()
    if left_pool and left_pool == right_pool:
        codes.append(JOIN_WIN_POOL)
    if left.ontology_object_ids & right.ontology_object_ids:
        codes.append(JOIN_ONTOLOGY_OBJECT)
    unbound = left.unbound_object_names & right.unbound_object_names
    empty = ONTOLOGY_OBJECT_EMPTY_NEXT_ACTION if unbound and JOIN_ONTOLOGY_OBJECT not in codes else None
    return EdgeJoinKeys(
        codes=tuple(codes),
        labels=tuple(JOIN_KEY_LABELS[code] for code in codes),
        empty_next_action=empty,
    )


def annotate_lineage_edges(
    edges: Sequence[dict[str, object]],
    facts_by_post: dict[str, PostJoinFacts],
) -> list[dict[str, object]]:
    """Copy reconstruct edges and attach join-key labels. No Searxng parents."""
    annotated: list[dict[str, object]] = []
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        left = facts_by_post.get(source)
        right = facts_by_post.get(target)
        payload = dict(edge)
        if left is None or right is None:
            payload["join_keys"] = []
            payload["empty_next_action"] = None
            annotated.append(payload)
            continue
        keys = join_keys_for_pair(left, right)
        payload["join_keys"] = [
            {"code": code, "label": label} for code, label in zip(keys.codes, keys.labels, strict=True)
        ]
        payload["empty_next_action"] = keys.empty_next_action
        annotated.append(payload)
    return annotated


__all__ = [
    "JOIN_KEYMAN",
    "JOIN_ONTOLOGY_OBJECT",
    "JOIN_WIN_POOL",
    "JOIN_KEY_LABELS",
    "ONTOLOGY_OBJECT_EMPTY_NEXT_ACTION",
    "EdgeJoinKeys",
    "PostJoinFacts",
    "annotate_lineage_edges",
    "join_keys_for_pair",
    "ontology_object_is_declared",
]
