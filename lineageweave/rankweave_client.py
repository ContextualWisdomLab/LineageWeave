"""Fail-closed adapter for RankWeave's in-process weighted RRF fusion.

`RankWeave <https://github.com/ContextualWisdomLab/RankWeave>`_ is a
library, not an HTTP service. Reconstruction already calls
``weighted_convex_fuse`` inside ``reconstruct.py``; this module is the
only LineageWeave port that may call ``weighted_reciprocal_rank_fuse``
for the buyer-facing Rankings surface. It never invents a fused score,
a theta, or a hidden post.

The default transport raises :class:`RankWeaveNotAvailable` so a
disabled or missing library is fail-closed, the same discipline as
:class:`lineageweave.threadweave_client.ThreadWeaveNotAvailable`.
Wiring the in-process library is additive
(``LibraryRankWeaveTransport``), not a redesign.

Rankings channel evidence is computed from LineageWeave-owned rank
lists (ADR 0167). The transport is trusted only for fused item order.
A missing channel is omitted, never fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence

# Cormack et al. (2009) reciprocal-rank fusion constant.
DEFAULT_RANK_CONSTANT_ETA = 60
DEFAULT_RANKING_LIMIT = 20
# Seeded A-100 titles mention pricing, quote, and delivery. This is a
# synthetic demo query, not a customer string.
DEFAULT_RANKING_QUERY = "pricing quote delivery"
RANKING_SIGNAL_LABELS = {
    "temporal": "Newest first",
    "lexical": "Title overlap",
}


class RankWeaveNotAvailable(RuntimeError):
    """Raised when the RankWeave ranking port is down or disabled."""

    reason = "rankweave_not_available"


class _ClassicWeights(dict[str, float]):
    """Mark caller-omitted weights selecting classic Cormack RRF."""


def _no_transport(
    _channels: dict[str, list[str]],
    _weights: dict[str, float],
) -> object:
    raise RankWeaveNotAvailable(
        "rankweave_not_available: RankWeave ranking port is not configured. "
        "Pass RANKWEAVE_DISABLED=0 (default) or a transport= callable. "
        "Never invent a fused score."
    )


def _import_rankweave() -> Any:
    """Import RankWeave at call time so a missing package fail-closes."""
    import rankweave as rw

    return rw


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return datetime.min
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.min


def _token_overlap(title: str, query: str) -> int:
    query_tokens = {token for token in query.casefold().split() if token}
    title_tokens = {token for token in title.casefold().split() if token}
    return len(query_tokens & title_tokens)


def ranking_channels_from_rows(
    posts: Sequence[Mapping[str, Any]],
    can_see_post: Callable[[Mapping[str, Any]], bool],
    query: str = DEFAULT_RANKING_QUERY,
) -> dict[str, list[str]]:
    """Project ABAC-visible posts into rank-only RankWeave channels.

    Hidden posts are omitted from every channel. Missing cells stay
    missing: a post never receives an invented score. Temporal ranks
    newest first; lexical ranks by token overlap with the demo query.
    """
    visible: list[Mapping[str, Any]] = []
    for row in posts:
        if not can_see_post(row):
            continue
        title = str(row.get("post_title") or "").strip()
        post_id = str(row.get("post_id") or "").strip()
        if not title or not post_id:
            continue
        visible.append(row)
    temporal = sorted(
        visible,
        key=lambda row: (
            _as_datetime(row.get("created_at")),
            str(row.get("post_id") or ""),
        ),
        reverse=True,
    )
    lexical = sorted(
        visible,
        key=lambda row: (
            -_token_overlap(str(row.get("post_title") or ""), query),
            str(row.get("post_title") or "").casefold(),
            str(row.get("post_id") or ""),
        ),
    )
    return {
        "temporal": [str(row["post_id"]) for row in temporal],
        "lexical": [str(row["post_id"]) for row in lexical],
    }


def ranking_channel_evidence(
    post_id: str,
    channels: Mapping[str, Sequence[str]],
    weights: Mapping[str, float],
    eta: int = DEFAULT_RANK_CONSTANT_ETA,
) -> tuple["RankingChannelEvidence", ...]:
    """Explain one fused hit from owned channel ranks.

    RankWeave owns the Cormack contribution arithmetic. A channel the post is
    missing from, or a non-positive weight, is omitted. Transport extra fields
    are ignored so a missing signal cannot be invented.
    """
    return _owner_channel_evidence(channels, weights, eta).get(post_id, ())


def _evidence_from_owner_hit(hit: object) -> tuple["RankingChannelEvidence", ...]:
    """Project one RankWeave result without recalculating a contribution."""
    collected = [
        (
            str(contribution.channel_name),
            int(contribution.rank),
            float(contribution.weight),
            float(contribution.contribution),
        )
        for contribution in getattr(hit, "channel_contributions", ())
        if contribution.rank is not None and contribution.weight > 0
    ]
    collected.sort(key=lambda item: (-item[3], item[0]))
    return tuple(
        RankingChannelEvidence(
            signal_code=signal_code,
            signal_label=RANKING_SIGNAL_LABELS.get(signal_code, signal_code),
            channel_rank=channel_rank,
            weight=weight,
            contribution=contribution,
            rank=index,
        )
        for index, (signal_code, channel_rank, weight, contribution) in enumerate(
            collected, start=1
        )
    )


def _owner_channel_evidence(
    channels: Mapping[str, Sequence[str]],
    weights: Mapping[str, float],
    eta: int,
) -> dict[str, tuple["RankingChannelEvidence", ...]]:
    """Index one RankWeave owner calculation by item identifier."""
    return {
        item_id: _evidence_from_owner_hit(hit)
        for hit in _owner_rrf_hits(
            channels,
            weights,
            eta,
            classic=isinstance(weights, _ClassicWeights),
        )
        if (item_id := _item_id_from_hit(hit))
    }


@dataclass(frozen=True)
class RankingChannelEvidence:
    """One owned-channel contribution to a fused ranking hit."""

    signal_code: str
    signal_label: str
    channel_rank: int
    weight: float
    contribution: float
    rank: int

    def to_json(self) -> dict[str, Any]:
        """Return the reader-safe owned-channel evidence payload."""

        return {
            "signal_code": self.signal_code,
            "signal_label": self.signal_label,
            "channel_rank": self.channel_rank,
            "weight": self.weight,
            "contribution": self.contribution,
            "rank": self.rank,
        }


@dataclass(frozen=True)
class RankedPost:
    """One visible fused hit. Rank is 1-based position, never a theta."""

    post_id: str
    post_title: str
    fused_rank: int
    channel_evidence: tuple[RankingChannelEvidence, ...] = ()

    def to_json(self) -> dict[str, Any]:
        """Serialize this ranked hit to its API-facing JSON shape."""
        return {
            "post_id": self.post_id,
            "post_title": self.post_title,
            "fused_rank": self.fused_rank,
            "channel_evidence": [item.to_json() for item in self.channel_evidence],
        }


@dataclass(frozen=True)
class RankingList:
    """Accepted ranking projection. Empty when RankWeave returned no hits."""

    items: tuple[RankedPost, ...]

    def to_json(self) -> list[dict[str, Any]]:
        """Serialize the accepted ranking list to its API-facing JSON shape."""
        return [item.to_json() for item in self.items]


@dataclass(frozen=True)
class _OwnerRankingEnvelope:
    """RankWeave hits produced by the trusted in-process adapter."""

    hits: tuple[object, ...]


def _owner_rrf_hits(
    channels: Mapping[str, Sequence[str]],
    weights: Mapping[str, float],
    eta: int,
    *,
    limit: int | None = None,
    classic: bool = False,
) -> list[object]:
    """Return RankWeave-owned classic or convex-weighted RRF results."""
    try:
        rw = _import_rankweave()
        if classic:
            return list(
                rw.reciprocal_rank_fuse(
                    channels,
                    limit=limit,
                    rank_constant_eta=eta,
                )
            )
        return list(
            rw.weighted_reciprocal_rank_fuse(
                channels,
                weights,
                limit=limit,
                rank_constant_eta=eta,
            )
        )
    except Exception as exc:
        raise RankWeaveNotAvailable(
            "rankweave_not_available: reciprocal-rank fusion failed"
        ) from exc


def _item_id_from_hit(hit: object) -> str:
    if isinstance(hit, Mapping):
        return str(hit.get("item_id") or hit.get("post_id") or "").strip()
    item_id = getattr(hit, "item_id", None)
    if item_id is not None:
        return str(item_id).strip()
    if isinstance(hit, (tuple, list)) and hit:
        return str(hit[0]).strip()
    return ""


def project_ranking_list(
    raw: object,
    titles_by_id: Mapping[str, str],
    channels: Mapping[str, Sequence[str]] | None = None,
    weights: Mapping[str, float] | None = None,
) -> RankingList:
    """Accept transport output. Unknown shapes fail closed. Hidden ids drop.

    Channel evidence is accepted only from the trusted in-process owner
    envelope. Legacy list transports retain their ordering but expose an
    empty breakdown; re-fusing their inputs could diverge from that ordering.
    Transport extra fields are ignored so a transport cannot invent a signal.
    """
    if isinstance(raw, _OwnerRankingEnvelope):
        raw_hits = list(raw.hits)
        evidence_by_post_id = {
            item_id: _evidence_from_owner_hit(hit)
            for hit in raw_hits
            if (item_id := _item_id_from_hit(hit))
        }
    elif isinstance(raw, list):
        raw_hits = raw
        if not raw_hits:
            return RankingList(items=())
        evidence_by_post_id = {}
    else:
        raise RankWeaveNotAvailable(
            "rankweave_not_available: ranking envelope is not a hit list"
        )
    items: list[RankedPost] = []
    seen: set[str] = set()
    for hit in raw_hits:
        post_id = _item_id_from_hit(hit)
        title = str(titles_by_id.get(post_id) or "").strip()
        if not post_id or not title or post_id in seen:
            continue
        seen.add(post_id)
        items.append(
            RankedPost(
                post_id=post_id,
                post_title=title,
                fused_rank=len(items) + 1,
                channel_evidence=evidence_by_post_id.get(post_id, ()),
            )
        )
    return RankingList(items=tuple(items))


class LibraryRankWeaveTransport:
    """Call RankWeave reciprocal-rank fusion in-process."""

    def __call__(
        self,
        channels: dict[str, list[str]],
        weights: dict[str, float],
    ) -> object:
        classic = isinstance(weights, _ClassicWeights)
        usable = {
            name: [item_id for item_id in ranks if str(item_id).strip()]
            for name, ranks in channels.items()
            if ranks
        }
        if not usable:
            return _OwnerRankingEnvelope(hits=())
        active_weights = {
            name: weights[name] for name in usable if name in weights and weights[name] > 0
        }
        if not active_weights:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: no positive channel weights remain"
            )
        usable = {name: ranks for name, ranks in usable.items() if name in active_weights}
        hits = _owner_rrf_hits(
            usable,
            active_weights,
            DEFAULT_RANK_CONSTANT_ETA,
            limit=DEFAULT_RANKING_LIMIT,
            classic=classic,
        )
        return _OwnerRankingEnvelope(hits=tuple(hits))


def build_rankweave_client(disabled: bool = False) -> "RankWeaveClient":
    """``disabled=True`` keeps the default fail-closed transport."""
    if disabled:
        return RankWeaveClient()
    return RankWeaveClient(transport=LibraryRankWeaveTransport())


class RankWeaveClient:
    """Fuses visible-post channels through a pluggable RankWeave transport."""

    def __init__(
        self,
        transport: Callable[
            [dict[str, list[str]], dict[str, float]], object
        ] = _no_transport,
    ) -> None:
        self._transport = transport

    def fuse_rankings(
        self,
        channels: dict[str, list[str]],
        titles_by_id: Mapping[str, str],
        weights: dict[str, float] | None = None,
    ) -> RankingList:
        """Fuse the channels; parameter-free classic RRF by default.

        No hand-picked weight exists (ADR 0200 point 1): without an explicit
        ``weights`` argument the adapter calls Cormack et al.'s (2009)
        parameter-free reciprocal rank fusion. The paper's own finding is
        that the unweighted form outperforms trained alternatives, so there
        is no arbitrary number to justify.
        Callers holding a psychometrically estimated set may still pass
        it explicitly; the disclosed per-channel evidence carries
        whichever weights actually fused.
        """
        if weights is not None and not weights:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: explicit channel weights are empty"
            )
        active_weights = (
            weights
            if weights is not None
            else _ClassicWeights({name: 1.0 for name in channels})
        )
        try:
            raw = self._transport(channels, active_weights)
        except RankWeaveNotAvailable:
            raise
        except Exception as exc:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: ranking transport failed"
            ) from exc
        try:
            return project_ranking_list(
                raw, titles_by_id, channels=channels, weights=active_weights
            )
        except RankWeaveNotAvailable:
            raise
        except Exception as exc:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: ranking projection failed"
            ) from exc

    def as_api_payload(
        self,
        posts: Sequence[Mapping[str, Any]],
        can_see_post: Callable[[Mapping[str, Any]], bool],
        query: str = DEFAULT_RANKING_QUERY,
    ) -> dict[str, Any]:
        """Buyer-visible ranking status. Never invents a fused score."""
        channels = ranking_channels_from_rows(posts, can_see_post, query=query)
        titles_by_id = {
            post_id: str(row.get("post_title") or "").strip()
            for row in posts
            if can_see_post(row)
            for post_id in [str(row.get("post_id") or "").strip()]
            if post_id and str(row.get("post_title") or "").strip()
        }
        try:
            ranking = self.fuse_rankings(channels, titles_by_id)
        except RankWeaveNotAvailable:
            return {
                "port": "rankweave",
                "status": "unavailable",
                "status_reason": RankWeaveNotAvailable.reason,
                "rankings": [],
            }
        return {
            "port": "rankweave",
            "status": "accepted",
            "status_reason": None,
            "rankings": ranking.to_json(),
        }
