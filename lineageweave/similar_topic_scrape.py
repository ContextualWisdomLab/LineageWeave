"""Scheduled similar-topic scrape hook. Live Camoufox fetch is Remote-only.

This Cloud slice consumes topic labels already on the board and
fail-closes when Camoufox is not on the machine. It does not plant a
Camoufox or Searxng server and does not fetch the public web.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .camoufox_client import CamoufoxClient, FetchedPage, NullCamoufoxClient

SIMILAR_TOPIC_EMPTY_NEXT_ACTION = "유사 토픽 글을 아직 받을 수 없습니다"
SIMILAR_TOPIC_THREAD_KEY = "similar-topic"

SALES_LEAD_TOPIC = "sales-lead specificity"
MARKET_STATUS_TOPIC = "voice of market"


@dataclass(frozen=True)
class SimilarTopicPost:
    """One already-fetched page ready to publish as a regular board post."""

    title: str
    body: str
    source_url: str


@dataclass(frozen=True)
class SimilarTopicBatch:
    """Scheduler result. Empty when Camoufox is not on this machine."""

    posts: tuple[SimilarTopicPost, ...]
    empty_next_action: str | None


def topic_queries_from_board(
    *,
    voc_type_codes: Sequence[str],
    relationship_codes: Sequence[str],
    has_sales_lead: bool,
) -> tuple[str, ...]:
    """Ontology / semantic-layer topics already on the board. No invented names."""
    topics: list[str] = []
    if has_sales_lead or "sales_lead_specificity" in relationship_codes:
        topics.append(SALES_LEAD_TOPIC)
    if "vom" in voc_type_codes or "rel_vom" in relationship_codes:
        topics.append(MARKET_STATUS_TOPIC)
    return tuple(topics)


def assemble_similar_topic_batch(
    *,
    searxng_available: bool,
    camoufox: CamoufoxClient,
    fetched_pages: Sequence[FetchedPage] = (),
) -> SimilarTopicBatch:
    """Publish only pages already fetched on Remote. Do not invent titles."""
    if not searxng_available or not camoufox.available:
        return SimilarTopicBatch(posts=(), empty_next_action=SIMILAR_TOPIC_EMPTY_NEXT_ACTION)
    posts = tuple(
        SimilarTopicPost(title=page.title, body=page.body, source_url=page.url)
        for page in fetched_pages
        if page.title.strip() and page.body.strip()
    )
    if not posts:
        return SimilarTopicBatch(posts=(), empty_next_action=SIMILAR_TOPIC_EMPTY_NEXT_ACTION)
    return SimilarTopicBatch(posts=posts, empty_next_action=None)


def scrape_similar_topics(
    *,
    topics: Sequence[str],
    searxng_base_url: str,
    camoufox: CamoufoxClient,
) -> SimilarTopicBatch:
    """Cloud scheduler hook. Does not search or fetch the public web."""
    del topics, searxng_base_url
    client = camoufox if camoufox.available else NullCamoufoxClient()
    return assemble_similar_topic_batch(
        searxng_available=False,
        camoufox=client,
    )


def similar_topic_empty_for_board(posts: Sequence[Any]) -> str | None:
    """Board placeholder when no scheduled similar-topic posts exist."""
    for post in posts:
        thread = getattr(post, "thread_group_key", None)
        if thread is None and isinstance(post, dict):
            thread = post.get("thread_group_key")
        if str(thread or "") == SIMILAR_TOPIC_THREAD_KEY:
            return None
    return SIMILAR_TOPIC_EMPTY_NEXT_ACTION
