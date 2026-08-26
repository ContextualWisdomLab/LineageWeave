"""Tests for authorized voice-taxonomy aggregate queries."""

import asyncio

from backend.app.voice_taxonomy import load_voice_taxonomy_summary


class _Connection:
    def __init__(self) -> None:
        self.args: tuple[object, ...] = ()

    async def fetchrow(self, query: str, *args: object):
        assert "post_product_mention" in query
        assert "post_project_mention" in query
        self.args = args
        return {
            "total_eligible": 4,
            "classified_unique": 1,
            "multi_membership": 1,
            "source_count": 2,
            "derived_count": 1,
            "unavailable": 2,
            "disagreement": 1,
            "category_post_counts": {"voc": 2, "vom": 1},
        }


def test_voice_summary_binds_authorization_and_every_filter() -> None:
    connection = _Connection()
    summary = asyncio.run(
        load_voice_taxonomy_summary(
            connection,
            authorized_corporate_entity_ids=("corp-a",),
            authorized_process_unit_ids=("pu-a",),
            date_from="from",
            date_to="to",
            corporate_entity_id="corp-filter",
            process_unit_id="pu-filter",
            team_id="team-filter",
            person_id="person-filter",
            product_catalog_id="product-filter",
            project_key="project-filter",
        )
    )
    assert summary["total_eligible"] == 4
    assert connection.args == (
        ["corp-a"], ["pu-a"], "from", "to", "corp-filter", "pu-filter",
        "team-filter", "person-filter", "product-filter", "project-filter",
    )
