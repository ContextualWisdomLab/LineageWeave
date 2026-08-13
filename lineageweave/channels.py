"""Independent scoring channels fused by :mod:`lineageweave.reconstruct`.

Each channel scores one ``(candidate_parent, record)`` pair in ``[0, 1]``.
No single channel is trusted alone -- Topic Detection and Tracking research
(Allan, 2002) established that naive single-signal linking between short
text items produces unreliable threads; fusing several weak, independent
signals is the standard mitigation (see docs/lineage-bi-research-notes.md).
"""

from __future__ import annotations

import difflib

from .models import Record


def temporal_score(candidate: Record, record: Record) -> float:
    """Closer in time scores higher; never negative even if clocks tie."""
    gap_seconds = max((record.occurred_at - candidate.occurred_at).total_seconds(), 0.0)
    gap_days = gap_seconds / 86_400.0
    return 1.0 / (1.0 + gap_days)


def secondary_key_match_score(candidate: Record, record: Record) -> float:
    """1.0 when both records share a non-empty secondary_key (e.g. project code)."""
    if not candidate.secondary_key or not record.secondary_key:
        return 0.0
    return 1.0 if candidate.secondary_key == record.secondary_key else 0.0


def text_similarity_score(candidate: Record, record: Record) -> float:
    """Cheap, dependency-free stand-in for an embedding-cosine channel.

    :class:`~difflib.SequenceMatcher` ratio on the two labels. Swap in
    :class:`~lineageweave.embedding_client.EmbeddingClient` + cosine
    similarity for real semantic matching once an embedding provider is
    configured (see ``lineageweave.embedding_client``) -- the channel
    fusion in ``reconstruct.py`` does not care which one produced the score.
    """
    return difflib.SequenceMatcher(None, candidate.label, record.label).ratio()
