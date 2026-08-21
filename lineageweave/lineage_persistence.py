"""Project reconstruction output into a versioned persistence contract.

The reconstruction algorithm stays in :mod:`lineageweave.reconstruct`. This
module carries both selected edges and the normalized active weight profile so
a database writer can persist the exact evidence used for one reconstruction
run without recomputing or guessing missing channels. Seed scripts, the
analysis-run worker, and the durable ``POST /api/lineage/rebuild`` job share
this contract so they cannot drift from what the Event Lineage panel reads.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .adjudication_client import AdjudicationClient, NullAdjudicationClient
from .models import Edge, Record
from .reconstruct import DEFAULT_CHANNEL_WEIGHTS, active_weights, reconstruct

RECONSTRUCTION_VERSION = "rankweave-weighted-convex-v1"


@dataclass(frozen=True)
class LineageReconstructionSpec:
    """Selected edges plus the exact active fusion profile for one run.

    Attributes:
        edges: Every selected parent→child edge produced by reconstruction.
        channel_weights: Normalized weights for channels that actually
            participated. Missing channels are absent rather than represented
            by zero.
        reconstruction_version: Stable algorithm contract identifier persisted
            with the run so later rebuilds cannot silently change its meaning.
    """

    edges: tuple[Edge, ...]
    channel_weights: dict[str, float]
    reconstruction_version: str


def lineage_reconstruction_spec(
    records: Sequence[Record],
    *,
    llm: AdjudicationClient | None = None,
    weights: dict[str, float] = DEFAULT_CHANNEL_WEIGHTS,
) -> LineageReconstructionSpec:
    """Run reconstruction and retain its active normalized weight profile.

    The same resolved LLM availability and configured pre-normalization weights
    are supplied to both :func:`active_weights` and :func:`reconstruct`. This
    prevents the persisted profile from drifting from the profile that selected
    the edges.
    """

    resolved_llm = llm if llm is not None else NullAdjudicationClient()
    normalized_weights = active_weights(resolved_llm, weights)
    trees = reconstruct(list(records), llm=resolved_llm, weights=weights)
    return LineageReconstructionSpec(
        edges=tuple(edge for tree in trees for edge in tree.edges),
        channel_weights=dict(normalized_weights),
        reconstruction_version=RECONSTRUCTION_VERSION,
    )


def lineage_edge_specs(
    records: Sequence[Record],
    *,
    llm: AdjudicationClient | None = None,
) -> list[Edge]:
    """Return the backward-compatible selected-edge projection.

    Callers that persist or expose audit evidence must use
    :func:`lineage_reconstruction_spec` instead so normalized weights and the
    reconstruction version are not discarded.
    """

    return list(lineage_reconstruction_spec(records, llm=llm).edges)
