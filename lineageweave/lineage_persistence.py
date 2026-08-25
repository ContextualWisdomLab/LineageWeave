"""Flatten ``reconstruct()`` trees into the rows Event Lineage persists.

The reconstruction algorithm stays in ``reconstruct.py``. This module is
the persistence contract shared by seed scripts and the live rebuild
writer so they cannot drift from what the Event Lineage panel reads.

Each parent→child edge is still one ``post_lineage_edge`` row. The
winning edge's active channel scores are persisted beside it as
``post_lineage_edge_signal`` rows (ADR 0172). A missing LLM channel is
dropped, never fabricated. Contribution is ``weight * score`` and must
reconcile with ``fused_score`` within the base tolerance plus the bounded
persistence quantization budget.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from .adjudication_client import AdjudicationClient
from .models import Edge, Record
from .reconstruct import (
    DEFAULT_CANDIDATE_WINDOW,
    DEFAULT_MIN_FUSED_SCORE,
    reconstruct,
)

RECONSTRUCTION_VERSION_PREFIX = "lineageweave.reconstruct"
CHANNEL_EVIDENCE_TOLERANCE = 1e-6
SIGNAL_QUANTUM = Decimal("0.000001")

LINEAGE_SIGNAL_ORDER = ("temporal", "secondary_key", "text", "llm")

LINEAGE_SIGNAL_LOOKUP_CODES = {
    "temporal": "lineage_signal_temporal",
    "secondary_key": "lineage_signal_secondary_key",
    "text": "lineage_signal_text",
    "llm": "lineage_signal_llm",
}

LINEAGE_SIGNAL_LABELS = {
    "temporal": "Temporal proximity",
    "secondary_key": "Secondary key match",
    "text": "Text similarity",
    "llm": "LLM adjudication",
}

LOOKUP_CODE_TO_SIGNAL = {code: name for name, code in LINEAGE_SIGNAL_LOOKUP_CODES.items()}


def lineage_edge_specs(
    records: Sequence[Record],
    *,
    llm: AdjudicationClient | None = None,
    weights: dict[str, float],
) -> list[Edge]:
    """Run reconstruct and return every resulting parent→child edge.

    Callers persist these as ``post_lineage_edge`` rows plus matching
    ``post_lineage_edge_signal`` rows. Record ids must already be the ids
    the database will store (UUIDs for product posts, fixture ids for the
    library-only demo) -- this function does not invent or rewrite
    identifiers.

    ``llm`` defaults to ``None``, which ``reconstruct()`` treats as the
    unavailable :class:`~lineageweave.adjudication_client.NullAdjudicationClient`
    (the supplied calibrated vector must omit the llm channel) -- callers that
    want the reasoning channel
    actually contributing to real reconstructions must pass a real one.

    ``weights`` is required and always a psychometric estimate (ADR
    0145, second amendment): the persisted fast-mlsirm corpus estimate
    on product paths, or the demo-design estimate from
    :func:`~lineageweave.channel_weight_estimation.estimate_fixture_channel_weights`.
    No hand-picked default exists anywhere.
    """
    trees = reconstruct(list(records), llm=llm, weights=weights)
    return [edge for tree in trees for edge in tree.edges]


def reconstruction_version(package_version: str | None = None) -> str:
    """Return the reconstruction identity stored on ``event_lineage_rebuild``.

    PostgreSQL remains the authority for live Event Lineage. This string
    names the reconstruct implementation that produced the current graph
    so a later rebuild cannot silently rewrite historic evidence.
    """
    if package_version is None:
        from lineageweave import __version__ as package_version
    return f"{RECONSTRUCTION_VERSION_PREFIX}/{package_version}"


def quantize_signal_value(value: float) -> float:
    """Quantize a score, weight, or contribution onto the persisted numeric scale."""
    quantized = Decimal(str(value)).quantize(SIGNAL_QUANTUM, rounding=ROUND_HALF_EVEN)
    return float(quantized)


@dataclass(frozen=True)
class LineageRebuildSpec:
    """Rows one atomic Event Lineage rebuild writes besides the edge list."""

    reconstruction_version: str
    min_fused_score: float
    candidate_window: int
    channel_weights: tuple[tuple[str, float], ...]
    signal_rows: tuple[dict[str, object], ...]


def channel_signal_rows(
    edge: Edge,
    weights: Mapping[str, float],
) -> list[dict[str, object]]:
    """Build persistable signal rows for one reconstructed edge.

    One row per active channel. The LLM channel is omitted when it did
    not participate. ``signal_weight`` is the normalized active weight
    actually used. ``signal_contribution`` is ``weight * score``.

    Raises:
        ValueError: if recorded contributions do not reconcile with
            ``edge.fused_score`` after accounting for one half quantum per
            persisted channel and a small floating-point guard.
    """
    active_weights = dict(weights)
    rows: list[dict[str, object]] = []
    contribution_sum = 0.0
    for channel in LINEAGE_SIGNAL_ORDER:
        if channel not in edge.channel_scores or channel not in active_weights:
            continue
        score = quantize_signal_value(float(edge.channel_scores[channel]))
        weight = quantize_signal_value(float(active_weights[channel]))
        contribution = quantize_signal_value(float(active_weights[channel]) * float(edge.channel_scores[channel]))
        contribution_sum += contribution
        rows.append(
            {
                "parent_post_id": edge.parent_id,
                "child_post_id": edge.child_id,
                "signal_code": LINEAGE_SIGNAL_LOOKUP_CODES[channel],
                "channel_name": channel,
                "signal_score": score,
                "signal_weight": weight,
                "signal_contribution": contribution,
            }
        )
    # Each numeric(8,6) contribution can differ from its exact product by
    # half a quantum. A fixed tolerance fails valid 3/4-channel edges when
    # those independent rounding errors accumulate.
    rounding_budget = len(rows) * float(SIGNAL_QUANTUM) / 2 + float(SIGNAL_QUANTUM)
    reconciliation_tolerance = max(CHANNEL_EVIDENCE_TOLERANCE, rounding_budget)
    residual = abs(contribution_sum - float(edge.fused_score))
    if rows and residual > reconciliation_tolerance:
        raise ValueError(
            f"channel contributions {contribution_sum} do not reconcile with "
            f"fused_score {edge.fused_score} (tolerance {reconciliation_tolerance})"
        )
    return rows


def rank_channel_evidence(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Project persisted signal rows onto the additive API collection.

    Ordering is contribution descending, then the controlled signal order
    ``temporal``, ``secondary_key``, ``text``, ``llm``. Rank is 1-based.
    The payload never includes prompts, responses, credentials, or source
    text.
    """

    def sort_key(row: Mapping[str, object]) -> tuple[float, int]:
        """Contribution descending, ties broken by the canonical channel order."""
        channel = _channel_name(row)
        order = LINEAGE_SIGNAL_ORDER.index(channel) if channel in LINEAGE_SIGNAL_ORDER else len(LINEAGE_SIGNAL_ORDER)
        return (-float(row["signal_contribution"]), order)

    evidence: list[dict[str, object]] = []
    for rank, row in enumerate(sorted(rows, key=sort_key), start=1):
        channel = _channel_name(row)
        label = str(row["signal_label"]) if row.get("signal_label") else LINEAGE_SIGNAL_LABELS.get(channel, channel)
        evidence.append(
            {
                "signal_code": channel,
                "signal_label": label,
                "score": float(row["signal_score"]),
                "weight": float(row["signal_weight"]),
                "contribution": float(row["signal_contribution"]),
                "rank": rank,
            }
        )
    return evidence


def llm_participated(evidence: Sequence[Mapping[str, object]]) -> bool:
    """Return whether the optional LLM channel is present in ``evidence``."""
    return any(item.get("signal_code") == "llm" for item in evidence)


def lineage_rebuild_spec(
    edges: Sequence[Edge],
    *,
    weights: Mapping[str, float],
    min_fused_score: float = DEFAULT_MIN_FUSED_SCORE,
    candidate_window: int = DEFAULT_CANDIDATE_WINDOW,
    package_version: str | None = None,
) -> LineageRebuildSpec:
    """Assemble the rebuild metadata and signal rows for ``edges``.

    ``weights`` is the provenance-bearing psychometric estimate that fused
    the graph. Every signal row uses that same profile so a later audit can
    reproduce the active measurement contract.
    """
    active_weights = dict(weights)

    signal_rows: list[dict[str, object]] = []
    for edge in edges:
        signal_rows.extend(channel_signal_rows(edge, active_weights))

    ordered_weights = tuple(
        (LINEAGE_SIGNAL_LOOKUP_CODES[name], quantize_signal_value(active_weights[name]))
        for name in LINEAGE_SIGNAL_ORDER
        if name in active_weights
    )
    return LineageRebuildSpec(
        reconstruction_version=reconstruction_version(package_version),
        min_fused_score=min_fused_score,
        candidate_window=candidate_window,
        channel_weights=ordered_weights,
        signal_rows=tuple(signal_rows),
    )


def _channel_name(row: Mapping[str, object]) -> str:
    stored = row.get("channel_name")
    if isinstance(stored, str) and stored:
        return stored
    lookup = str(row.get("signal_code") or "")
    return LOOKUP_CODE_TO_SIGNAL.get(lookup, lookup)
