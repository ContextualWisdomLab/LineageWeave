"""Contracts for the official O*NET occupational construct catalog."""

from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager

import pytest

from lineageweave.occupational_construct_catalog import (
    ONET_ATTRIBUTION,
    catalog_content_sha256,
    parse_onet_construct_catalog,
    sync_onet_construct_catalog,
)


def _payload() -> dict[str, object]:
    return {
        "table_id": "content_model_reference",
        "row": [
            {
                "element_id": "1.A.1.a.1",
                "element_name": "Oral Comprehension",
                "description": "Understand spoken words.",
            },
            {
                "element_id": "1.D.1",
                "element_name": "Achievement Orientation",
                "description": "   ",
            },
            {
                "element_id": "4.A.1.a.1",
                "element_name": "Getting Information",
                "description": None,
            },
            {
                "element_id": "2.C.1",
                "element_name": "Education",
                "description": "Outside the governed roots.",
            },
        ],
    }


def test_parser_admits_only_the_three_published_hierarchy_roots() -> None:
    """Published element positions, not label guesses, determine each family."""
    constructs = parse_onet_construct_catalog(_payload())
    assert [construct.family_code for construct in constructs] == [
        "cognitive_ability",
        "work_style",
        "work_activity",
    ]
    assert constructs[0].construct_iri.endswith("/1.A.1.a.1")
    assert constructs[1].description is None


def test_parser_rejects_malformed_or_duplicate_source_rows() -> None:
    """A malformed official document cannot become a partial local catalog."""
    with pytest.raises(ValueError, match="Content Model Reference"):
        parse_onet_construct_catalog({"table_id": "other", "row": []})
    payload = _payload()
    rows = payload["row"]
    assert isinstance(rows, list)
    payload["row"] = [rows[0], rows[0]]
    with pytest.raises(ValueError, match="duplicate"):
        parse_onet_construct_catalog(payload)


def test_catalog_hash_is_key_order_independent() -> None:
    """Equivalent decoded JSON produces one reproducible release digest."""
    assert catalog_content_sha256({"a": 1, "b": 2}) == catalog_content_sha256(
        {"b": 2, "a": 1}
    )


class _Transaction(AbstractAsyncContextManager[None]):
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *_args: object) -> None:
        return None


class _RecordingConnection:
    def __init__(self) -> None:
        self.batch: list[tuple[object, ...]] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def fetchval(self, query: str, *args: object) -> str:
        assert "source_content_sha256" in query
        assert args[3] == ONET_ATTRIBUTION
        return "vocabulary-id"

    async def executemany(
        self, query: str, args: list[tuple[object, ...]]
    ) -> None:
        assert "construct_description" in query
        self.batch = args

    async def fetch(self, _query: str, *_args: object) -> list[dict[str, object]]:
        return [
            {
                "construct_iri": row[1],
                "construct_family_code": row[2],
                "preferred_label": row[3],
                "construct_description": row[4],
            }
            for row in self.batch
        ]


def test_sync_uses_one_transaction_and_verifies_exact_stored_metadata() -> None:
    """The operator sync persists and verifies the whole admitted catalog."""
    conn = _RecordingConnection()
    assert asyncio.run(sync_onet_construct_catalog(conn, _payload())) == 3
    assert len(conn.batch) == 3


def test_sync_rejects_conflicting_stored_construct_metadata() -> None:
    """A same-version label conflict aborts instead of rewriting history."""
    class ConflictingConnection(_RecordingConnection):
        async def fetch(
            self, query: str, *args: object
        ) -> list[dict[str, object]]:
            rows = await super().fetch(query, *args)
            rows[0]["preferred_label"] = "Conflicting label"
            return rows

    with pytest.raises(ValueError, match="differs from the official release"):
        asyncio.run(sync_onet_construct_catalog(ConflictingConnection(), _payload()))
