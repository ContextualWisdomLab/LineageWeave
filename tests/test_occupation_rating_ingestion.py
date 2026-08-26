"""Tests for the provenance-bearing occupation-rating read projection."""

import asyncio
from decimal import Decimal

from backend.app.main import (
    read_occupation_rating_sources,
    read_occupation_ratings,
    read_rating_source_occupations,
)
from backend.app.occupation_rating_ingestion import (
    fetch_occupation_rating_sources,
    fetch_occupation_ratings,
    fetch_rating_source_occupations,
)


class FakeConnection:
    """Minimal ordered asyncpg stand-in for one projection query."""

    def __init__(self, source, rows=()):
        self.source = source
        self.rows = list(rows)
        self.fetch_called = False
        self.last_fetch_query = ""

    async def fetchrow(self, _query: str, *_args: object):
        """Return configured source metadata."""
        return self.source

    async def fetch(self, query: str, *_args: object):
        """Return configured observation rows."""
        self.fetch_called = True
        self.last_fetch_query = query
        return self.rows


class FakeAcquire:
    """Async pool-acquire context for route wiring."""

    def __init__(self, conn: FakeConnection):
        self.conn = conn

    async def __aenter__(self) -> FakeConnection:
        """Return the configured connection."""
        return self.conn

    async def __aexit__(self, *_args: object) -> None:
        """Release without external state."""


class FakePool:
    """Minimal pool exposing one acquisition context."""

    def __init__(self, conn: FakeConnection):
        self.conn = conn

    def acquire(self) -> FakeAcquire:
        """Return one deterministic acquisition context."""
        return FakeAcquire(self.conn)


def test_unimported_source_is_not_an_empty_observed_profile() -> None:
    conn = FakeConnection(None)

    result = asyncio.run(
        fetch_occupation_ratings(
            conn,
            data_release_code="onet-31.0",
            source_table_code="abilities",
            onetsoc_code="15-1252.00",
            limit=100,
            offset=0,
        )
    )

    assert result["source_available"] is False
    assert result["items"] == []
    assert conn.fetch_called is False


def test_rating_projection_preserves_exact_decimal_and_warning_flags() -> None:
    source = {
        "source_table_name": "Abilities",
        "source_artifact_url": "https://example.test/abilities.csv",
        "source_artifact_sha256": "a" * 64,
        "source_row_count": 2,
        "scale_artifact_url": "https://example.test/scales.csv",
        "scale_artifact_sha256": "b" * 64,
        "scale_source_row_count": 33,
    }
    row = {
        "element_id": "1.A.1.a.1",
        "element_name": "Oral Comprehension",
        "scale_id": "IM",
        "scale_name": "Importance",
        "minimum_value": Decimal("1.00"),
        "maximum_value": Decimal("5.00"),
        "category_value": None,
        "data_value": Decimal("4.10"),
        "sample_size": 8,
        "standard_error": Decimal("0.1830"),
        "lower_ci_bound": Decimal("3.7414"),
        "upper_ci_bound": Decimal("4.4586"),
        "recommend_suppress": True,
        "not_relevant": None,
        "source_updated_month": "08/2026",
        "domain_source_code": "Analyst",
    }
    conn = FakeConnection(source, (row, row))

    result = asyncio.run(
        fetch_occupation_ratings(
            conn,
            data_release_code="onet-31.0",
            source_table_code="abilities",
            onetsoc_code="15-1252.00",
            limit=1,
            offset=0,
        )
    )

    item = result["items"][0]
    assert item["data_value"] == "4.10"
    assert item["standard_error"] == "0.1830"
    assert item["recommend_suppress"] is True
    assert item["not_relevant"] is None
    assert result["source"]["scale_artifact_sha256"] == "b" * 64
    assert result["next_offset"] == 1


def test_empty_profile_keeps_imported_scale_provenance() -> None:
    source = {
        "source_table_name": "Abilities",
        "source_artifact_url": "https://example.test/abilities.csv",
        "source_artifact_sha256": "a" * 64,
        "source_row_count": 2,
        "scale_artifact_url": "https://example.test/scales.csv",
        "scale_artifact_sha256": "b" * 64,
        "scale_source_row_count": 33,
    }

    result = asyncio.run(
        fetch_occupation_ratings(
            FakeConnection(source),
            data_release_code="onet-31.0",
            source_table_code="abilities",
            onetsoc_code="15-9999.99",
            limit=100,
            offset=0,
        )
    )

    assert result["source_available"] is True
    assert result["items"] == []
    assert result["source"]["scale_artifact_sha256"] == "b" * 64


def test_authenticated_route_delegates_to_bounded_projection() -> None:
    result = asyncio.run(
        read_occupation_ratings(
            onetsoc_code="15-1252.00",
            data_release_code="onet-31.0",
            source_table_code="abilities",
            limit=100,
            offset=0,
            _account=object(),
            pool=FakePool(FakeConnection(None)),
        )
    )

    assert result["source_available"] is False


def test_source_catalog_returns_only_query_selected_imports() -> None:
    source = {
        "data_release_code": "onet-31.0",
        "release_version": "31.0",
        "source_publisher_name": "National Center for O*NET Development",
        "source_license_url": "https://example.test/license",
        "source_table_code": "abilities",
        "source_table_name": "Abilities",
        "source_artifact_url": "https://example.test/abilities.csv",
        "source_artifact_sha256": "a" * 64,
        "source_row_count": 94640,
    }

    conn = FakeConnection(None, (source,))
    result = asyncio.run(fetch_occupation_rating_sources(conn))

    assert result == {"sources": [source]}
    assert "source_table_code <> 'scales_reference'" in conn.last_fetch_query
    assert "and exists" in conn.last_fetch_query


def test_authenticated_source_catalog_route_uses_shared_projection() -> None:
    result = asyncio.run(
        read_occupation_rating_sources(
            _account=object(),
            pool=FakePool(FakeConnection(None)),
        )
    )

    assert result == {"sources": []}


def test_source_occupation_catalog_distinguishes_unavailable_from_empty() -> None:
    unavailable = asyncio.run(
        fetch_rating_source_occupations(
            FakeConnection(None),
            data_release_code="onet-31.0",
            source_table_code="abilities",
        )
    )
    empty = asyncio.run(
        fetch_rating_source_occupations(
            FakeConnection({"exists": 1}),
            data_release_code="onet-31.0",
            source_table_code="abilities",
        )
    )

    assert unavailable["source_available"] is False
    assert empty["source_available"] is True
    assert empty["occupations"] == []


def test_source_occupation_catalog_returns_authoritative_codes_and_titles() -> None:
    rows = (
        {"onetsoc_code": "11-1011.00", "occupation_title": "Chief Executives"},
        {"onetsoc_code": "15-1252.00", "occupation_title": "Software Developers"},
    )
    conn = FakeConnection({"exists": 1}, rows)

    result = asyncio.run(
        fetch_rating_source_occupations(
            conn,
            data_release_code="onet-31.0",
            source_table_code="abilities",
        )
    )

    assert result["occupations"] == list(rows)
    assert "and exists" in conn.last_fetch_query


def test_authenticated_source_occupation_route_uses_shared_projection() -> None:
    result = asyncio.run(
        read_rating_source_occupations(
            data_release_code="onet-31.0",
            source_table_code="abilities",
            _account=object(),
            pool=FakePool(FakeConnection({"exists": 1})),
        )
    )

    assert result["source_available"] is True
