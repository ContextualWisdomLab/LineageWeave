"""Tests for authorized voice-taxonomy aggregate queries."""

import asyncio

from backend.app import main
from backend.app.auth import CurrentAccount
from backend.app.voice_taxonomy import (
    load_voice_taxonomy_summary,
    warm_voice_taxonomy_read_statements,
)


class _Connection:
    def __init__(self) -> None:
        self.args: tuple[object, ...] = ()

    async def fetchrow(self, query: str, *args: object):
        assert "post_product_mention" in query
        assert "post_project_mention" in query
        assert "post.visibility_code = 'public'" in query
        assert "cardinality($2::uuid[]) = 0" in query
        assert "not (post.corporate_entity_id = any($11::uuid[]))" in query
        assert "source_deleted_flag" in query
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
            excluded_corporate_entity_ids=("demo-corp",),
        )
    )
    assert summary["total_eligible"] == 4
    assert connection.args == (
        ["corp-a"], ["pu-a"], "from", "to", "corp-filter", "pu-filter",
        "team-filter", "person-filter", "product-filter", "project-filter",
        ["demo-corp"],
    )


def test_voice_summary_uses_exact_month_projection() -> None:
    """The common authorized read sums the maintained monthly partitions."""

    class ProjectionConnection:
        async def fetchrow(self, query: str, *args: object):
            assert "voice_taxonomy_month_read_projection" in query
            assert "source_post post" not in query
            assert args == (
                ["corp-a"], [], None, None, None, None, ["demo-corp"], True,
            )
            return {
                "total_eligible": 7,
                "classified_unique": 5,
                "multi_membership": 1,
                "source_count": 6,
                "derived_count": 2,
                "unavailable": 1,
                "disagreement": 1,
                "category_post_counts": {"voc": 4, "vop": 2},
                "projection_stale": False,
            }

    summary = asyncio.run(
        load_voice_taxonomy_summary(
            ProjectionConnection(),
            authorized_corporate_entity_ids=("corp-a",),
            authorized_process_unit_ids=(),
            excluded_corporate_entity_ids=("demo-corp",),
            source_context_required=True,
        )
    )
    assert summary == {
        "total_eligible": 7,
        "classified_unique": 5,
        "multi_membership": 1,
        "source_count": 6,
        "derived_count": 2,
        "unavailable": 1,
        "disagreement": 1,
        "category_post_counts": {"voc": 4, "vop": 2},
    }


def test_voice_summary_prepares_all_read_shapes() -> None:
    """Pool startup executes each statement shape before accepting reads."""

    class Connection:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def fetchrow(self, query: str, *_args: object):
            self.queries.append(query)
            return {
                "total_eligible": 0, "classified_unique": 0,
                "multi_membership": 0, "source_count": 0,
                "derived_count": 0, "unavailable": 0, "disagreement": 0,
                "category_post_counts": {}, "projection_stale": False,
            }

    connection = Connection()
    asyncio.run(warm_voice_taxonomy_read_statements(connection))
    assert "voice_taxonomy_month_read_projection" in connection.queries[0]
    assert "voice_taxonomy_day_read_projection" in connection.queries[1]
    assert "voice_taxonomy_post_read_projection" in connection.queries[2]


def test_voice_summary_excludes_demo_entities_when_real_context_exists(monkeypatch) -> None:
    """A real-data account never mixes synthetic seed rows into its denominator."""
    captured: dict[str, object] = {}

    class Acquire:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_args: object) -> None:
            return None

    class Pool:
        def acquire(self) -> Acquire:
            return Acquire()

    async def has_real(_conn: object, entity_ids: list[str]) -> bool:
        assert entity_ids == ["00000000-0000-0000-0000-000000000001"]
        return True

    async def demo_ids(_conn: object) -> set[str]:
        return {"00000000-0000-0000-0000-000000000099"}

    async def load(_conn: object, **kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "total_eligible": 0,
            "classified_unique": 0,
            "multi_membership": 0,
            "source_count": 0,
            "derived_count": 0,
            "unavailable": 0,
            "disagreement": 0,
            "category_post_counts": {},
        }

    monkeypatch.setattr(main, "has_real_source_context", has_real)
    monkeypatch.setattr(main, "fetch_demo_corporate_entity_ids", demo_ids)
    monkeypatch.setattr(main, "load_voice_taxonomy_summary", load)
    account = CurrentAccount(
        user_account_id="00000000-0000-0000-0000-000000000010",
        external_subject_id="synthetic-subject",
        display_name="Synthetic reader",
        preferred_locale="en",
        corporate_entity_ids=frozenset({"00000000-0000-0000-0000-000000000001"}),
        process_unit_ids=frozenset(),
        permission_codes=frozenset({"post_read"}),
    )

    result = asyncio.run(
        main.read_voice_taxonomy_summary(
            date_from=None,
            date_to=None,
            corporate_entity_id=None,
            process_unit_id=None,
            team_id=None,
            person_id=None,
            product_catalog_id=None,
            project_key=None,
            account=account,
            pool=Pool(),
        )
    )

    assert result["total_eligible"] == 0
    assert captured["excluded_corporate_entity_ids"] == (
        "00000000-0000-0000-0000-000000000099",
    )
