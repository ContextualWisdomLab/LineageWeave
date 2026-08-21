from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from backend.app.entity_relationship_ingestion import ingest_post_entity_relationships
from lineageweave.entity_relationship_classification import OrganizationRelationship


class _Connection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    @asynccontextmanager
    async def transaction(self):
        yield self

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((" ".join(query.split()), args))
        return "OK"


class _Client:
    available = True

    def classify(self, _title: str, _body: str, names: list[str]) -> list[OrganizationRelationship]:
        return [OrganizationRelationship(names[0], "rel_voc")] if names else []


def test_relationship_ingestion_replaces_stale_rows_and_filters_unknown_names() -> None:
    conn = _Connection()
    relationships = asyncio.run(
        ingest_post_entity_relationships(
            conn,
            _Client(),
            "post-1",
            "Synthetic title",
            "Synthetic body",
            ["External organization"],
        )
    )

    assert relationships[0].organization_name == "External organization"
    assert conn.executed[0][0] == "delete from post_counterparty_entity where post_id = $1"
    assert conn.executed[1][0].startswith("insert into post_counterparty_entity")


def test_relationship_ingestion_clears_rows_when_no_counterparty_remains() -> None:
    conn = _Connection()
    assert asyncio.run(
        ingest_post_entity_relationships(
            conn, _Client(), "post-2", "Synthetic title", "Synthetic body", []
        )
    ) == []
    assert conn.executed == [
        ("delete from post_counterparty_entity where post_id = $1", ("post-2",))
    ]
