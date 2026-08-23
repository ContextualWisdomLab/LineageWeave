"""Fail-closed adapter for RankWeave's in-process weighted RRF fusion.

`RankWeave <https://github.com/ContextualWisdomLab/RankWeave>`_ is a
library, not an HTTP service. Reconstruction already calls
``weighted_convex_fuse`` inside ``reconstruct.py``; this module is the
only LineageWeave port that may call ``weighted_reciprocal_rank_fuse``
for the reader-facing Rankings surface. It never invents a fused score,
a theta, or a hidden post.

The default transport raises :class:`RankWeaveNotAvailable` so a
disabled or missing library is fail-closed, the same discipline as
:class:`lineageweave.threadweave_client.ThreadWeaveNotAvailable`.
Wiring the in-process library is additive
(``LibraryRankWeaveTransport``), not a redesign.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence

# Cormack et al. (2009) reciprocal-rank fusion constant.
DEFAULT_RANK_CONSTANT_ETA = 60
DEFAULT_RANKING_LIMIT = 20
DEFAULT_CHANNEL_WEIGHTS = {"temporal": 0.25, "lexical": 0.75}
# Seeded A-100 titles mention pricing, quote, and delivery. This is a
# synthetic demo query, not a customer string.
DEFAULT_RANKING_QUERY = "pricing quote delivery"


class RankWeaveNotAvailable(RuntimeError):
    """Raised when the RankWeave ranking port is down or disabled."""

    reason = "rankweave_not_available"


def _no_transport(
    _channels: dict[str, list[str]],
    _weights: dict[str, float],
) -> list[dict[str, Any]]:
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


@dataclass(frozen=True)
class RankedPost:
    """One visible fused hit. Rank is 1-based position, never a theta."""

    post_id: str
    post_title: str
    fused_rank: int

    def to_json(self) -> dict[str, Any]:
        """Serialize this ranked hit to its API-facing JSON shape."""
        return {
            "post_id": self.post_id,
            "post_title": self.post_title,
            "fused_rank": self.fused_rank,
        }


@dataclass(frozen=True)
class RankingList:
    """Accepted ranking projection. Empty when RankWeave returned no hits."""

    items: tuple[RankedPost, ...]

    def to_json(self) -> list[dict[str, Any]]:
        """Serialize the accepted ranking list to its API-facing JSON shape."""
        return [item.to_json() for item in self.items]


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
) -> RankingList:
    """Accept transport output. Unknown shapes fail closed. Hidden ids drop."""
    if not isinstance(raw, list):
        raise RankWeaveNotAvailable(
            "rankweave_not_available: ranking envelope is not a hit list"
        )
    items: list[RankedPost] = []
    seen: set[str] = set()
    for hit in raw:
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
            )
        )
    return RankingList(items=tuple(items))


class LibraryRankWeaveTransport:
    """Call RankWeave ``weighted_reciprocal_rank_fuse`` in-process."""

    def __call__(
        self,
        channels: dict[str, list[str]],
        weights: dict[str, float],
    ) -> list[dict[str, Any]]:
        try:
            rw = _import_rankweave()
        except ImportError as exc:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: rankweave package is not installed. "
                "Never invent a fused score."
            ) from exc
        usable = {
            name: [item_id for item_id in ranks if str(item_id).strip()]
            for name, ranks in channels.items()
            if ranks
        }
        if not usable:
            return []
        active_weights = {
            name: weights[name] for name in usable if name in weights and weights[name] > 0
        }
        if not active_weights:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: no positive channel weights remain"
            )
        try:
            hits = rw.weighted_reciprocal_rank_fuse(
                usable,
                active_weights,
                limit=DEFAULT_RANKING_LIMIT,
                rank_constant_eta=DEFAULT_RANK_CONSTANT_ETA,
            )
        except TypeError:
            try:
                hits = rw.weighted_reciprocal_rank_fuse(
                    usable,
                    active_weights,
                    limit=DEFAULT_RANKING_LIMIT,
                )
            except Exception as exc:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: weighted_reciprocal_rank_fuse failed"
                ) from exc
        except Exception as exc:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: weighted_reciprocal_rank_fuse failed"
            ) from exc
        projected: list[dict[str, Any]] = []
        for hit in hits:
            item_id = _item_id_from_hit(hit)
            if item_id:
                projected.append({"item_id": item_id})
        return projected


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
            [dict[str, list[str]], dict[str, float]], list[dict[str, Any]]
        ] = _no_transport,
    ) -> None:
        self._transport = transport

    def fuse_rankings(
        self,
        channels: dict[str, list[str]],
        titles_by_id: Mapping[str, str],
        weights: dict[str, float] | None = None,
    ) -> RankingList:
        """Fuse the supplied per-channel rankings through RankWeave."""
        try:
            raw = self._transport(channels, weights or DEFAULT_CHANNEL_WEIGHTS)
        except RankWeaveNotAvailable:
            raise
        except Exception as exc:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: ranking transport failed"
            ) from exc
        return project_ranking_list(raw, titles_by_id)

    def as_api_payload(
        self,
        posts: Sequence[Mapping[str, Any]],
        can_see_post: Callable[[Mapping[str, Any]], bool],
        query: str = DEFAULT_RANKING_QUERY,
    ) -> dict[str, Any]:
        """Reader-visible ranking status. Never invents a fused score."""
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
