"""Similar-topic scrape is scheduled and fail-closed. No invented posts."""

from lineageweave.camoufox_client import FetchedPage, NullCamoufoxClient, build_camoufox_client
from lineageweave.similar_topic_scrape import (
    MARKET_STATUS_TOPIC,
    SALES_LEAD_TOPIC,
    SIMILAR_TOPIC_EMPTY_NEXT_ACTION,
    assemble_similar_topic_batch,
    scrape_similar_topics,
    similar_topic_empty_for_board,
    topic_queries_from_board,
)


def test_topics_come_from_sales_lead_and_market_status() -> None:
    topics = topic_queries_from_board(
        voc_type_codes=("voc", "vom"),
        relationship_codes=("rel_vom",),
        has_sales_lead=True,
    )
    assert SALES_LEAD_TOPIC in topics
    assert MARKET_STATUS_TOPIC in topics


def test_empty_camoufox_url_does_not_plant_a_server() -> None:
    assert isinstance(build_camoufox_client(""), NullCamoufoxClient)
    assert isinstance(build_camoufox_client("   "), NullCamoufoxClient)


def test_missing_camoufox_fail_closes_without_invented_posts() -> None:
    batch = assemble_similar_topic_batch(
        searxng_available=True,
        camoufox=NullCamoufoxClient(),
        fetched_pages=(FetchedPage("https://example.test", "Invented", "body"),),
    )
    assert batch.posts == ()
    assert batch.empty_next_action == SIMILAR_TOPIC_EMPTY_NEXT_ACTION


def test_missing_searxng_fail_closes() -> None:
    class _Ready:
        available = True

        def fetch_page(self, url: str) -> FetchedPage:
            return FetchedPage(url, "Title", "Body")

    batch = assemble_similar_topic_batch(searxng_available=False, camoufox=_Ready())
    assert batch.empty_next_action == SIMILAR_TOPIC_EMPTY_NEXT_ACTION


def test_fetched_pages_become_regular_posts() -> None:
    class _Ready:
        available = True

        def fetch_page(self, url: str) -> FetchedPage:
            raise AssertionError("assemble uses already-fetched pages")

    batch = assemble_similar_topic_batch(
        searxng_available=True,
        camoufox=_Ready(),
        fetched_pages=(FetchedPage("https://example.test/lead", "Demo similar topic", "Body"),),
    )
    assert batch.empty_next_action is None
    assert batch.posts[0].title == "Demo similar topic"


def test_cloud_scrape_hook_does_not_fetch_the_public_web() -> None:
    class _Ready:
        available = True

        def fetch_page(self, url: str) -> FetchedPage:
            raise AssertionError(f"Cloud scrape must not fetch {url}")

    batch = scrape_similar_topics(
        topics=(SALES_LEAD_TOPIC,),
        searxng_base_url="https://searxng.example",
        camoufox=_Ready(),
    )
    assert batch.posts == ()
    assert batch.empty_next_action == SIMILAR_TOPIC_EMPTY_NEXT_ACTION


def test_board_empty_copy_when_no_similar_topic_posts() -> None:
    assert similar_topic_empty_for_board([{"thread_group_key": "A-100"}]) == SIMILAR_TOPIC_EMPTY_NEXT_ACTION
    assert similar_topic_empty_for_board([{"thread_group_key": "similar-topic"}]) is None
