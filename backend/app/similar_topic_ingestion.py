"""Publish scheduled similar-topic posts. Not an HTTP buyer route."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from lineageweave.camoufox_client import CamoufoxClient
from lineageweave.similar_topic_scrape import (
    SIMILAR_TOPIC_THREAD_KEY,
    SimilarTopicBatch,
    scrape_similar_topics,
    topic_queries_from_board,
)


def collect_board_topic_queries(cur: Any) -> tuple[str, ...]:
    """Sales-lead and market-status topics already on the board."""
    cur.execute("select voc_type_code from source_post")
    voc_types = [row[0] for row in cur.fetchall()]
    cur.execute("select relationship_type_code from post_counterparty_entity")
    relationships = [row[0] for row in cur.fetchall()]
    cur.execute(
        "select 1 from post_evaluation_response where criterion_code = %s limit 1",
        ("sales_lead_specificity",),
    )
    has_sales_lead = cur.fetchone() is not None
    return topic_queries_from_board(
        voc_type_codes=voc_types,
        relationship_codes=relationships,
        has_sales_lead=has_sales_lead,
    )


def publish_similar_topic_batch(
    cur: Any,
    batch: SimilarTopicBatch,
    *,
    author_account_id: str,
    corporate_entity_id: str,
    process_unit_id: str,
    created_at: datetime,
) -> tuple[str, ...]:
    """Insert fetched pages as regular source_post rows. No invented titles."""
    if batch.empty_next_action or not batch.posts:
        return ()
    clock = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    published: list[str] = []
    for post in batch.posts:
        cur.execute(
            "select post_id from source_post where thread_group_key = %s and post_title = %s",
            (SIMILAR_TOPIC_THREAD_KEY, post.title),
        )
        existing = cur.fetchone()
        if existing is not None:
            published.append(str(existing[0]))
            continue
        cur.execute(
            """
            insert into source_post (
                author_account_id, corporate_entity_id, process_unit_id,
                post_title, post_body, voc_type_code, visibility_code,
                thread_group_key, secondary_grouping_key, created_at, updated_at
            ) values (%s, %s, %s, %s, %s, 'vom', 'public', %s, %s, %s, %s)
            returning post_id
            """,
            (
                author_account_id,
                corporate_entity_id,
                process_unit_id,
                post.title,
                post.body,
                SIMILAR_TOPIC_THREAD_KEY,
                post.source_url,
                clock,
                clock,
            ),
        )
        published.append(str(cur.fetchone()[0]))
    return tuple(published)


def publish_similar_topic_scrape(
    cur: Any,
    *,
    searxng_base_url: str,
    camoufox: CamoufoxClient,
    author_account_id: str,
    corporate_entity_id: str,
    process_unit_id: str,
    created_at: datetime,
) -> SimilarTopicBatch:
    """Scheduler entry. Unavailable channels write no posts."""
    topics = collect_board_topic_queries(cur)
    batch = scrape_similar_topics(
        topics=topics,
        searxng_base_url=searxng_base_url,
        camoufox=camoufox,
    )
    publish_similar_topic_batch(
        cur,
        batch,
        author_account_id=author_account_id,
        corporate_entity_id=corporate_entity_id,
        process_unit_id=process_unit_id,
        created_at=created_at,
    )
    return batch
